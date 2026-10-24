// State management
let currentStream = null;
let autoScanInterval = null;
let isAnalyzing = false;
let uploadedBlob = null;
let currentResult = null;
const HISTORY_STORAGE_KEY = 'freshscan_scan_history';

// DOM Elements
const videoFeed = document.getElementById('webcam-feed');
const snapshotCanvas = document.getElementById('snapshot-canvas');
const scanLaser = document.getElementById('scan-laser');
const cameraPlaceholder = document.getElementById('camera-placeholder');
const btnToggleCamera = document.getElementById('btn-toggle-camera');
const cameraBtnText = document.getElementById('camera-btn-text');
const btnCapture = document.getElementById('btn-capture');
const toggleAutoscan = document.getElementById('toggle-autoscan');

// Raspberry Pi Camera Rev 1.3 DOM Elements
const btnPicamCapture = document.getElementById('btn-picam-capture');
const btnRefreshStream = document.getElementById('btn-refresh-stream');
const togglePicamAutoscan = document.getElementById('toggle-picam-autoscan');
const picamStreamFeed = document.getElementById('picam-stream-feed');
const picamScanLaser = document.getElementById('picam-scan-laser');
const picamSensorName = document.getElementById('picam-sensor-name');
const picamBackendBadge = document.getElementById('picam-backend-badge');
let picamAutoScanInterval = null;

// Tabs
const tabButtons = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

// Upload & Dropzone
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const browseLink = document.getElementById('browse-link');
const uploadPreviewOverlay = document.getElementById('upload-preview-overlay');
const uploadPreviewImg = document.getElementById('upload-preview-img');
const btnRemovePreview = document.getElementById('btn-remove-preview');
const btnLoadSample = document.getElementById('btn-load-sample');
const btnAnalyzeUpload = document.getElementById('btn-analyze-upload');

// Results Dashboard
const emptyState = document.getElementById('empty-state');
const loadingState = document.getElementById('loading-state');
const resultsDashboard = document.getElementById('results-dashboard');
const resultsStateBadge = document.getElementById('results-state-badge');

const verdictBanner = document.getElementById('verdict-banner');
const verdictTag = document.getElementById('verdict-tag');
const verdictScore = document.getElementById('verdict-score');
const verdictTitle = document.getElementById('verdict-title');
const verdictMeter = document.getElementById('verdict-meter');
const verdictDesc = document.getElementById('verdict-desc');

const categoryTypePill = document.getElementById('category-type-pill');
const categoryEmoji = document.getElementById('category-emoji');
const categoryName = document.getElementById('category-name');
const categoryScore = document.getElementById('category-score');
const categoryMeter = document.getElementById('category-meter');
const storageTipText = document.getElementById('storage-tip-text');

const annotatedImageDisplay = document.getElementById('annotated-image-display');
const btnFullscreenAnnotated = document.getElementById('btn-fullscreen-annotated');
const jsonCodeBlock = document.getElementById('json-code-block');
const btnCopyJson = document.getElementById('btn-copy-json');

// History & Modal
const historySection = document.getElementById('history-section');
const historyStrip = document.getElementById('history-strip');
const btnClearHistory = document.getElementById('btn-clear-history');
const imageModal = document.getElementById('image-modal');
const modalBackdrop = document.getElementById('modal-backdrop');
const modalCloseBtn = document.getElementById('modal-close-btn');
const modalImage = document.getElementById('modal-image');

// ==========================================
// Subtle Web Audio Feedback (Success Chime)
// ==========================================
function playSuccessChime(isFresh) {
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.type = 'sine';
    const freq = isFresh ? 587.33 : 329.63; // D5 for Fresh, E4 for Rotten
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(freq * 1.5, audioCtx.currentTime + 0.15);

    gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);

    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.35);
  } catch (e) {
    // Ignore audio context autoplay restrictions
  }
}

// ==========================================
// Tabs Switching
// ==========================================
tabButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    const targetTab = btn.getAttribute('data-tab');

    tabButtons.forEach(b => b.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));

    btn.classList.add('active');
    document.getElementById(`tab-${targetTab}`).classList.add('active');
  });
});

// ==========================================
// Camera Controls (HTML5 MediaDevices API)
// ==========================================
async function startCamera() {
  try {
    const constraints = {
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: 'user'
      }
    };
    currentStream = await navigator.mediaDevices.getUserMedia(constraints);
    videoFeed.srcObject = currentStream;

    cameraPlaceholder.style.display = 'none';
    btnToggleCamera.classList.remove('btn-secondary');
    btnToggleCamera.classList.add('btn-primary');
    cameraBtnText.textContent = 'Stop Camera';
    btnCapture.disabled = false;
    toggleAutoscan.disabled = false;
    scanLaser.classList.add('scanning');

    document.getElementById('status-text').textContent = 'Camera Streaming';
  } catch (err) {
    console.error('Camera access error:', err);
    alert('Unable to access webcam. Please ensure your browser has camera permissions enabled.');
  }
}

function stopCamera() {
  if (currentStream) {
    currentStream.getTracks().forEach(track => track.stop());
    currentStream = null;
  }
  videoFeed.srcObject = null;
  cameraPlaceholder.style.display = 'flex';
  btnToggleCamera.classList.add('btn-secondary');
  btnToggleCamera.classList.remove('btn-primary');
  cameraBtnText.textContent = 'Start Camera';
  btnCapture.disabled = true;
  toggleAutoscan.disabled = true;
  toggleAutoscan.checked = false;
  clearInterval(autoScanInterval);
  autoScanInterval = null;
  scanLaser.classList.remove('scanning');

  document.getElementById('status-text').textContent = 'System Ready';
}

btnToggleCamera.addEventListener('click', () => {
  if (currentStream) {
    stopCamera();
  } else {
    startCamera();
  }
});

// Capture frame from webcam
function captureWebcamFrame() {
  if (!currentStream || isAnalyzing) return;

  const width = videoFeed.videoWidth || 640;
  const height = videoFeed.videoHeight || 480;

  snapshotCanvas.width = width;
  snapshotCanvas.height = height;

  const ctx = snapshotCanvas.getContext('2d');
  ctx.drawImage(videoFeed, 0, 0, width, height);

  snapshotCanvas.toBlob(blob => {
    if (blob) {
      sendImageToApi(blob, 'webcam_capture.jpg');
    }
  }, 'image/jpeg', 0.92);
}

btnCapture.addEventListener('click', captureWebcamFrame);

// Auto-scan feature (every 3 seconds)
toggleAutoscan.addEventListener('change', () => {
  if (toggleAutoscan.checked) {
    autoScanInterval = setInterval(() => {
      if (currentStream && !isAnalyzing) {
        captureWebcamFrame();
      }
    }, 3000);
  } else {
    clearInterval(autoScanInterval);
    autoScanInterval = null;
  }
});

// ==========================================
// Dropzone & File Upload
// ==========================================
browseLink.addEventListener('click', (e) => {
  e.stopPropagation();
  fileInput.click();
});
dropzone.addEventListener('click', () => fileInput.click());

['dragenter', 'dragover'].forEach(eventName => {
  dropzone.addEventListener(eventName, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(eventName => {
  dropzone.addEventListener(eventName, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove('dragover');
  });
});

dropzone.addEventListener('drop', (e) => {
  const dt = e.dataTransfer;
  if (dt.files && dt.files[0]) {
    handleFile(dt.files[0]);
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files && fileInput.files[0]) {
    handleFile(fileInput.files[0]);
  }
});

// Clipboard Paste Support
document.addEventListener('paste', (e) => {
  const items = (e.clipboardData || e.originalEvent.clipboardData).items;
  for (let item of items) {
    if (item.type.indexOf('image') !== -1) {
      const blob = item.getAsFile();
      // Switch to upload tab
      tabButtons[1].click();
      handleFile(blob);
      break;
    }
  }
});

function handleFile(file) {
  uploadedBlob = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    uploadPreviewImg.src = e.target.result;
    uploadPreviewOverlay.style.display = 'block';
    btnAnalyzeUpload.disabled = false;
  };
  reader.readAsDataURL(file);
}

btnRemovePreview.addEventListener('click', (e) => {
  e.stopPropagation();
  uploadedBlob = null;
  fileInput.value = '';
  uploadPreviewOverlay.style.display = 'none';
  btnAnalyzeUpload.disabled = true;
});

btnAnalyzeUpload.addEventListener('click', () => {
  if (uploadedBlob) {
    sendImageToApi(uploadedBlob, uploadedBlob.name || 'uploaded_image.jpg');
  }
});

// Quick Sample Load
btnLoadSample.addEventListener('click', async () => {
  try {
    const res = await fetch('test_sample.jpg');
    if (!res.ok) throw new Error('Sample not found');
    const blob = await res.blob();
    handleFile(blob);
    // Immediately analyze sample
    sendImageToApi(blob, 'test_sample.jpg');
  } catch (err) {
    console.error('Error loading sample:', err);
    alert('Could not load test_sample.jpg.');
  }
});

// ==========================================
// API Communication & Render Results
// ==========================================
async function sendImageToApi(imageBlob, filename = 'produce.jpg') {
  if (isAnalyzing) return;
  isAnalyzing = true;

  // Update UI to Loading State
  emptyState.style.display = 'none';
  resultsDashboard.style.display = 'none';
  loadingState.style.display = 'flex';
  resultsStateBadge.textContent = 'Inference Running...';
  resultsStateBadge.style.color = '#38bdf8';

  const formData = new FormData();
  formData.append('image', imageBlob, filename);

  try {
    const response = await fetch('/predict/image', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Analysis failed' }));
      throw new Error(errorData.detail || 'Server error');
    }

    const data = await response.json();
    currentResult = data;
    renderResults(data);
    saveToHistory(data);
  } catch (error) {
    console.error('Inference error:', error);
    alert(`Prediction failed: ${error.message}`);
    loadingState.style.display = 'none';
    if (!currentResult) emptyState.style.display = 'flex';
  } finally {
    isAnalyzing = false;
  }
}

function renderResults(data) {
  loadingState.style.display = 'none';
  resultsDashboard.style.display = 'flex';

  const cat = data.category;
  const fresh = data.freshness;
  const meta = data.metadata || {};

  const isFresh = fresh.label.toLowerCase() === 'fresh';
  playSuccessChime(isFresh);

  // Verdict Banner
  verdictBanner.className = `verdict-banner ${isFresh ? 'verdict-fresh' : 'verdict-rotten'}`;
  verdictTag.textContent = isFresh ? '🌿 FRESH PRODUCE' : '⚠️ SPOILED / ROTTEN';
  const freshPct = (fresh.score * 100).toFixed(1);
  verdictScore.textContent = `${freshPct}% Match`;
  verdictTitle.textContent = isFresh ? 'Optimal & Wholesome' : 'Decay / Spoilage Detected';
  verdictMeter.style.width = `${freshPct}%`;
  verdictDesc.textContent = isFresh
    ? 'Produce meets safety and quality standards for consumption or cooking.'
    : 'Signs of mold, softening, or oxidation observed. Discarding is advised.';

  // State Badge in Card Header
  resultsStateBadge.textContent = isFresh ? 'Fresh Verdict' : 'Spoiled Verdict';
  resultsStateBadge.style.color = isFresh ? '#34d399' : '#f87171';

  // Category Details
  categoryTypePill.textContent = meta.type || 'Produce';
  categoryEmoji.textContent = meta.emoji || '🥬';
  categoryName.textContent = cat.label;
  const catPct = (cat.score * 100).toFixed(1);
  categoryScore.textContent = `${catPct}%`;
  categoryMeter.style.width = `${catPct}%`;

  // Storage & Culinary Tip
  storageTipText.textContent = meta.tip || 'Store in a clean, temperature-controlled environment.';

  // Annotated Image
  if (data.annotated_image_base64) {
    annotatedImageDisplay.src = data.annotated_image_base64;
  }

  // Raw JSON
  jsonCodeBlock.textContent = JSON.stringify(data, null, 2);
}

// Copy JSON
btnCopyJson.addEventListener('click', () => {
  if (currentResult) {
    navigator.clipboard.writeText(JSON.stringify(currentResult, null, 2)).then(() => {
      btnCopyJson.textContent = '✓ Copied!';
      setTimeout(() => btnCopyJson.textContent = '📋 Copy JSON', 2000);
    });
  }
});

// Fullscreen Modal for image
btnFullscreenAnnotated.addEventListener('click', () => {
  if (annotatedImageDisplay.src) {
    modalImage.src = annotatedImageDisplay.src;
    imageModal.classList.add('open');
  }
});
[modalBackdrop, modalCloseBtn].forEach(el => {
  el.addEventListener('click', () => imageModal.classList.remove('open'));
});

// ==========================================
// Scan History Storage (localStorage)
// ==========================================
function saveToHistory(data) {
  try {
    let history = JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) || '[]');
    const item = {
      id: Date.now(),
      category: data.category.label,
      emoji: data.metadata?.emoji || '🥬',
      freshness: data.freshness.label,
      score: (data.freshness.score * 100).toFixed(0),
      image: data.annotated_image_base64,
      data: data
    };
    history.unshift(item);
    if (history.length > 8) history = history.slice(0, 8);
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
    renderHistory();
  } catch (e) {
    console.warn('History save failed:', e);
  }
}

function renderHistory() {
  try {
    const history = JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) || '[]');
    if (!history.length) {
      historySection.style.display = 'none';
      return;
    }
    historySection.style.display = 'block';
    historyStrip.innerHTML = '';

    history.forEach(item => {
      const el = document.createElement('div');
      el.className = 'history-item';
      const isFresh = item.freshness.toLowerCase() === 'fresh';
      el.innerHTML = `
        <img class="history-thumb" src="${item.image}" alt="${item.category}">
        <span class="history-tag" style="color: ${isFresh ? '#34d399' : '#f87171'}">
          ${item.emoji} ${item.category}
        </span>
        <span class="history-sub">${item.freshness} • ${item.score}%</span>
      `;
      el.addEventListener('click', () => {
        currentResult = item.data;
        renderResults(item.data);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
      historyStrip.appendChild(el);
    });
  } catch (e) {
    console.warn('History render error:', e);
  }
}

btnClearHistory.addEventListener('click', () => {
  localStorage.removeItem(HISTORY_STORAGE_KEY);
  renderHistory();
});

// ==========================================
// Raspberry Pi Camera Rev 1.3 Handlers
// ==========================================
async function capturePiCameraFrame() {
  if (isAnalyzing) return;
  isAnalyzing = true;

  if (picamScanLaser) picamScanLaser.classList.add('scanning');
  emptyState.style.display = 'none';
  resultsDashboard.style.display = 'none';
  loadingState.style.display = 'flex';
  resultsStateBadge.textContent = 'Snapping Pi Camera & Analyzing...';
  resultsStateBadge.style.color = '#38bdf8';

  try {
    const res = await fetch('/api/camera/capture', { method: 'POST' });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: 'Pi Camera capture failed' }));
      throw new Error(errData.detail || 'Pi Camera capture error');
    }
    const data = await res.json();
    currentResult = data;
    renderResults(data);
    saveToHistory(data);
  } catch (err) {
    console.error('Pi Camera Capture error:', err);
    alert(`Raspberry Pi Camera Capture Failed: ${err.message}`);
    loadingState.style.display = 'none';
    if (!currentResult) emptyState.style.display = 'flex';
  } finally {
    isAnalyzing = false;
    if (picamScanLaser) picamScanLaser.classList.remove('scanning');
  }
}

if (btnPicamCapture) {
  btnPicamCapture.addEventListener('click', capturePiCameraFrame);
}

if (btnRefreshStream && picamStreamFeed) {
  btnRefreshStream.addEventListener('click', () => {
    picamStreamFeed.src = `/api/camera/stream?t=${Date.now()}`;
  });
}

if (togglePicamAutoscan) {
  togglePicamAutoscan.addEventListener('change', () => {
    if (togglePicamAutoscan.checked) {
      picamAutoScanInterval = setInterval(() => {
        if (!isAnalyzing) {
          capturePiCameraFrame();
        }
      }, 3000);
    } else {
      clearInterval(picamAutoScanInterval);
      picamAutoScanInterval = null;
    }
  });
}

async function checkPiCameraStatus() {
  try {
    const res = await fetch('/api/camera/status');
    if (!res.ok) return;
    const status = await res.json();
    if (picamSensorName && status.sensor) {
      picamSensorName.textContent = status.sensor;
    }
    if (picamBackendBadge && status.backend) {
      picamBackendBadge.textContent = status.backend.toUpperCase();
      picamBackendBadge.style.color = status.available ? '#34d399' : '#fbbf24';
    }
  } catch (e) {
    console.warn('Could not query Pi camera status:', e);
  }
}

async function checkSystemEngine() {
  try {
    const res = await fetch('/api/metadata');
    if (!res.ok) return;
    const meta = await res.json();
    const engineBadge = document.getElementById('engine-badge');
    if (engineBadge && meta.engine) {
      engineBadge.textContent = `${meta.engine.toUpperCase()} SIMD • 10 Classes`;
    }
  } catch (e) {
    console.warn('Could not query metadata engine:', e);
  }
}

// Initial loads
window.addEventListener('DOMContentLoaded', () => {
  renderHistory();
  checkPiCameraStatus();
  checkSystemEngine();
  fetchActiveAlerts();
  checkSystemStatus();
  // Poll active alerts and system status every 4s
  setInterval(() => {
    fetchActiveAlerts();
    checkSystemStatus();
  }, 4000);
});

// ==========================================
// FreshScan AI 2.0 Active Alerts & Simulator
// ==========================================
const activeAlertsList = document.getElementById('active-alerts-list');
const emptyAlertsPlaceholder = document.getElementById('empty-alerts-placeholder');
const activeAlertsCountBadge = document.getElementById('active-alerts-count-badge');
const esp32Badge = document.getElementById('esp32-badge');
const btnTriggerTestAlert = document.getElementById('btn-trigger-test-alert');
const simProduceSelect = document.getElementById('sim-produce-select');
const btnTestTelegram = document.getElementById('btn-test-telegram');
const btnRefreshAlerts = document.getElementById('btn-refresh-alerts');

async function fetchActiveAlerts() {
  try {
    const res = await fetch('/api/alerts/active');
    if (!res.ok) return;
    const alerts = await res.json();

    if (activeAlertsCountBadge) {
      activeAlertsCountBadge.textContent = `${alerts.length} Active`;
      activeAlertsCountBadge.style.color = alerts.length > 0 ? '#f87171' : 'var(--accent-emerald)';
    }

    if (!alerts || alerts.length === 0) {
      activeAlertsList.innerHTML = '';
      activeAlertsList.appendChild(emptyAlertsPlaceholder);
      emptyAlertsPlaceholder.style.display = 'block';
      return;
    }

    emptyAlertsPlaceholder.style.display = 'none';
    activeAlertsList.innerHTML = '';

    const emojiMap = {
      Apple: '🍎', Banana: '🍌', Bellpepper: '🫑', Carrot: '🥕',
      Cucumber: '🥒', Mango: '🥭', Orange: '🍊', Potato: '🥔',
      Strawberry: '🍓', Tomato: '🍅'
    };

    alerts.forEach(alert => {
      const isNew = alert.status === 'NEW';
      const card = document.createElement('div');
      card.className = `alert-item-card ${isNew ? 'state-new' : 'state-ack'}`;

      const emoji = emojiMap[alert.produce] || '🥬';
      const timeStr = alert.created_at ? new Date(alert.created_at).toLocaleTimeString() : '';

      card.innerHTML = `
        <div class="alert-item-info">
          <span class="alert-item-emoji">${emoji}</span>
          <div>
            <div class="alert-item-title">
              ${alert.produce}
              <span class="alert-status-pill ${isNew ? 'status-pill-new' : 'status-pill-ack'}">
                ${isNew ? `LED #${alert.led_index} BLINKING` : `LED #${alert.led_index} STEADY ON`}
              </span>
            </div>
            <div class="alert-item-sub">
              <strong>${alert.event_id}</strong> • Detected at ${timeStr} • ${(alert.freshness_score * 100).toFixed(1)}% Spoiled
            </div>
          </div>
        </div>
        <div class="alert-item-actions">
          ${isNew ? `<button class="btn-sm btn-ack" onclick="acknowledgeAlert('${alert.event_id}')">Acknowledge</button>` : ''}
          <button class="btn-sm btn-clr" onclick="clearAlert('${alert.event_id}')">Clear</button>
        </div>
      `;
      activeAlertsList.appendChild(card);
    });
  } catch (e) {
    console.warn('Error fetching active alerts:', e);
  }
}

async function acknowledgeAlert(id) {
  try {
    const res = await fetch(`/api/alerts/${id}/acknowledge`, { method: 'POST' });
    if (res.ok) fetchActiveAlerts();
  } catch (e) {
    console.error('Error acknowledging alert:', e);
  }
}

async function clearAlert(id) {
  try {
    const res = await fetch(`/api/alerts/${id}/clear`, { method: 'POST' });
    if (res.ok) fetchActiveAlerts();
  } catch (e) {
    console.error('Error clearing alert:', e);
  }
}

async function checkSystemStatus() {
  try {
    const res = await fetch('/api/system/status');
    if (!res.ok) return;
    const status = await res.json();
    if (esp32Badge) {
      if (status.mqtt?.esp32_online) {
        esp32Badge.textContent = `📡 ESP32: Online (${status.mqtt.esp32_ip || 'Active'})`;
        esp32Badge.style.color = '#34d399';
      } else if (status.mqtt?.mqtt_broker_connected) {
        esp32Badge.textContent = `📡 MQTT Ready • ESP32 Standby`;
        esp32Badge.style.color = '#38bdf8';
      } else {
        esp32Badge.textContent = `📡 MQTT Broker Standby`;
        esp32Badge.style.color = 'var(--text-muted)';
      }
    }
  } catch (e) {
    console.warn('Error checking system status:', e);
  }
}

if (btnTriggerTestAlert && simProduceSelect) {
  btnTriggerTestAlert.addEventListener('click', async () => {
    const vegetable = simProduceSelect.value;
    btnTriggerTestAlert.disabled = true;
    btnTriggerTestAlert.textContent = 'Transmitting to ESP32...';
    try {
      const res = await fetch('/api/test/spoilage-alert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vegetable: vegetable })
      });
      const data = await res.json();
      fetchActiveAlerts();
      alert(`✅ Spoilage alert sent to ESP32 (LED #${data.decision?.led_index || ''}) and queued for Telegram!`);
    } catch (err) {
      alert(`Simulation failed: ${err.message}`);
    } finally {
      btnTriggerTestAlert.disabled = false;
      btnTriggerTestAlert.textContent = '⚡ Send Alert to ESP32 & Telegram';
    }
  });
}

if (btnTestTelegram) {
  btnTestTelegram.addEventListener('click', async () => {
    btnTestTelegram.disabled = true;
    btnTestTelegram.textContent = 'Pinging Telegram...';
    try {
      const res = await fetch('/api/test/telegram', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        alert('🎉 Telegram link verified! Check your Telegram chat for the ping message.');
      } else {
        alert(`Telegram test message failed:\n${data.error || 'Check bot token and chat ID.'}`);
      }
    } catch (err) {
      alert(`Network error: ${err.message}`);
    } finally {
      btnTestTelegram.disabled = false;
      btnTestTelegram.textContent = '✈️ Test Telegram Link';
    }
  });
}

if (btnRefreshAlerts) {
  btnRefreshAlerts.addEventListener('click', () => {
    fetchActiveAlerts();
    checkSystemStatus();
  });
}

// Make ack/clear accessible to inline onclick
window.acknowledgeAlert = acknowledgeAlert;
window.clearAlert = clearAlert;
});
