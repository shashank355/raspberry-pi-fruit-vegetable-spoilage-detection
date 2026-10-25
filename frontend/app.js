// ==============================================================================
// FreshScan AI 2.0 • Raspberry Pi 5 + USB Camera + Gemini AI Pro Dashboard Controller
// ==============================================================================

// State management
let currentStream = null;
let autoScanInterval = null;
let usbcamAutoScanInterval = null;
let aiProAutoScanInterval = null;
let isAnalyzing = false;
let isAiProAnalyzing = false;
let uploadedBlob = null;
let currentResult = null;
const HISTORY_STORAGE_KEY = 'freshscan_scan_history';

// DOM Elements: Webcam (Browser HTML5 MediaDevices)
const videoFeed = document.getElementById('webcam-feed');
const snapshotCanvas = document.getElementById('snapshot-canvas');
const scanLaser = document.getElementById('scan-laser');
const cameraPlaceholder = document.getElementById('camera-placeholder');
const btnToggleCamera = document.getElementById('btn-toggle-camera');
const cameraBtnText = document.getElementById('camera-btn-text');
const btnCapture = document.getElementById('btn-capture');
const toggleAutoscan = document.getElementById('toggle-autoscan');

// DOM Elements: External USB Camera (Raspberry Pi 5)
const btnUsbcamCapture = document.getElementById('btn-usbcam-capture');
const btnRefreshStream = document.getElementById('btn-refresh-stream');
const toggleUsbcamAutoscan = document.getElementById('toggle-usbcam-autoscan');
const usbcamStreamFeed = document.getElementById('usbcam-stream-feed');
const usbcamScanLaser = document.getElementById('usbcam-scan-laser');
const usbcamSensorName = document.getElementById('usbcam-sensor-name');
const usbcamBackendBadge = document.getElementById('usbcam-backend-badge');
const selectUsbDevice = document.getElementById('select-usb-device');

// DOM Elements: AI Pro Studio & Controls
const toggleAiPro = document.getElementById('toggle-ai-pro');
const aiProToggleStatusText = document.getElementById('ai-pro-toggle-status-text');
const aiProIntervalSelect = document.getElementById('ai-pro-interval-select');
const btnAiProInspectNow = document.getElementById('btn-ai-pro-inspect-now');
const btnOpenKeyModal = document.getElementById('btn-open-key-modal');
const cooldownPill = document.getElementById('cooldown-pill');
const telemetryCalls = document.getElementById('telemetry-calls');
const telemetryTokensSaved = document.getElementById('telemetry-tokens-saved');
const telemetrySkipped = document.getElementById('telemetry-skipped');
const telemetryTokensUsed = document.getElementById('telemetry-tokens-used');
const aiProHeaderBadge = document.getElementById('ai-pro-header-badge');

// DOM Elements: AI Pro Results Display Card
const aiProResultCard = document.getElementById('ai-pro-result-card');
const aiProGradeBadge = document.getElementById('ai-pro-grade-badge');
const aiProScorePill = document.getElementById('ai-pro-score-pill');
const aiProShelfLife = document.getElementById('ai-pro-shelf-life');
const aiProRipeness = document.getElementById('ai-pro-ripeness');
const aiProWarningBox = document.getElementById('ai-pro-warning-box');
const aiProSpoilageList = document.getElementById('ai-pro-spoilage-list');
const aiProDefectsChips = document.getElementById('ai-pro-defects-chips');
const aiProSummaryText = document.getElementById('ai-pro-summary-text');
const aiProStorageText = document.getElementById('ai-pro-storage-text');
const aiProTokenInfo = document.getElementById('ai-pro-token-info');
const aiProSaverTag = document.getElementById('ai-pro-saver-tag');

// DOM Elements: Gemini API Key Modal
const keyModal = document.getElementById('key-modal');
const keyModalBackdrop = document.getElementById('key-modal-backdrop');
const keyModalCloseBtn = document.getElementById('key-modal-close-btn');
const geminiKeyInput = document.getElementById('gemini-key-input');
const geminiModelSelect = document.getElementById('gemini-model-select');
const btnSaveKey = document.getElementById('btn-save-key');
const btnCancelKey = document.getElementById('btn-cancel-key');

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

// Results Dashboard (Local Inference)
const emptyState = document.getElementById('empty-state');
const loadingState = document.getElementById('loading-state');
const loadingTitle = document.getElementById('loading-title');
const loadingDesc = document.getElementById('loading-desc');
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

// Hardware alerts elements
const activeAlertsList = document.getElementById('active-alerts-list');
const emptyAlertsPlaceholder = document.getElementById('empty-alerts-placeholder');
const activeAlertsCountBadge = document.getElementById('active-alerts-count-badge');
const esp32Badge = document.getElementById('esp32-badge');
const btnTriggerTestAlert = document.getElementById('btn-trigger-test-alert');
const simProduceSelect = document.getElementById('sim-produce-select');
const btnTestTelegram = document.getElementById('btn-test-telegram');
const btnRefreshAlerts = document.getElementById('btn-refresh-alerts');


// ==========================================
// Subtle Web Audio Feedback
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
    // Autoplay restrictions
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
    const targetEl = document.getElementById(`tab-${targetTab}`);
    if (targetEl) targetEl.classList.add('active');
  });
});


// ==========================================
// External USB Camera Handlers (Raspberry Pi 5)
// ==========================================
async function loadCameraDevices() {
  try {
    const res = await fetch('/api/camera/devices');
    if (!res.ok) return;
    const data = await res.json();

    if (selectUsbDevice && data.devices) {
      selectUsbDevice.innerHTML = '<option value="auto">Auto-detect USB</option>';
      data.devices.forEach(dev => {
        const opt = document.createElement('option');
        opt.value = dev.index;
        opt.textContent = `${dev.node}: ${dev.name} ${dev.is_usb ? '(USB)' : ''}`;
        if (dev.index === data.current_index) {
          opt.selected = true;
        }
        selectUsbDevice.appendChild(opt);
      });
    }
  } catch (e) {
    console.warn('Could not load camera devices:', e);
  }
}

if (selectUsbDevice) {
  selectUsbDevice.addEventListener('change', async () => {
    const chosen = selectUsbDevice.value;
    try {
      const res = await fetch('/api/camera/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: chosen === 'auto' ? 'auto' : parseInt(chosen) })
      });
      if (res.ok) {
        checkUsbCameraStatus();
        if (usbcamStreamFeed) {
          usbcamStreamFeed.src = `/api/camera/stream?t=${Date.now()}`;
        }
      }
    } catch (e) {
      console.error('Failed to switch camera:', e);
    }
  });
}

async function checkUsbCameraStatus() {
  try {
    const res = await fetch('/api/camera/status');
    if (!res.ok) return;
    const status = await res.json();
    if (usbcamSensorName && status.sensor) {
      usbcamSensorName.textContent = status.sensor;
    }
    if (usbcamBackendBadge && status.backend) {
      usbcamBackendBadge.textContent = status.backend.toUpperCase();
      usbcamBackendBadge.style.color = status.available ? '#34d399' : '#fbbf24';
    }
    const hwBadge = document.getElementById('hardware-badge');
    if (hwBadge) {
      hwBadge.textContent = `🍓 RPi 5 • ${status.available ? 'USB Cam Ready' : 'Virtual Cam'}`;
    }
  } catch (e) {
    console.warn('Could not query USB camera status:', e);
  }
}

async function captureUsbCameraFrame() {
  if (isAnalyzing) return;
  isAnalyzing = true;

  if (usbcamScanLaser) usbcamScanLaser.classList.add('scanning');
  emptyState.style.display = 'none';
  resultsDashboard.style.display = 'none';
  loadingState.style.display = 'flex';
  if (loadingTitle) loadingTitle.textContent = 'Snapping USB Camera...';
  if (loadingDesc) loadingDesc.textContent = 'Executing inference on Raspberry Pi 5';
  resultsStateBadge.textContent = 'Inference Running...';
  resultsStateBadge.style.color = '#38bdf8';

  try {
    const res = await fetch('/api/camera/capture', { method: 'POST' });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: 'USB Camera capture failed' }));
      throw new Error(errData.detail || 'USB Camera capture error');
    }
    const data = await res.json();
    currentResult = data;
    renderResults(data);
    saveToHistory(data);
  } catch (err) {
    console.error('USB Camera Capture error:', err);
    alert(`Raspberry Pi 5 USB Camera Capture Failed: ${err.message}`);
    loadingState.style.display = 'none';
    if (!currentResult) emptyState.style.display = 'flex';
  } finally {
    isAnalyzing = false;
    if (usbcamScanLaser) usbcamScanLaser.classList.remove('scanning');
  }
}

if (btnUsbcamCapture) {
  btnUsbcamCapture.addEventListener('click', captureUsbCameraFrame);
}

if (btnRefreshStream && usbcamStreamFeed) {
  btnRefreshStream.addEventListener('click', () => {
    usbcamStreamFeed.src = `/api/camera/stream?t=${Date.now()}`;
  });
}

if (toggleUsbcamAutoscan) {
  toggleUsbcamAutoscan.addEventListener('change', () => {
    if (toggleUsbcamAutoscan.checked) {
      usbcamAutoScanInterval = setInterval(() => {
        if (!isAnalyzing && !isAiProAnalyzing) {
          captureUsbCameraFrame();
        }
      }, 3000);
    } else {
      clearInterval(usbcamAutoScanInterval);
      usbcamAutoScanInterval = null;
    }
  });
}


// ==============================================================================
// GEMINI AI PRO QUALITY INSPECTION & TOKEN PROTECTOR
// ==============================================================================

async function fetchAiProStatus() {
  try {
    const res = await fetch('/api/ai-pro/status');
    if (!res.ok) return;
    const telemetry = await res.json();
    updateTelemetryUI(telemetry);
  } catch (e) {
    console.warn('Could not fetch AI Pro status:', e);
  }
}

function updateTelemetryUI(telemetry) {
  if (!telemetry) return;

  if (telemetryCalls) telemetryCalls.textContent = telemetry.total_calls ?? 0;
  if (telemetryTokensSaved) telemetryTokensSaved.textContent = `~${telemetry.estimated_tokens_saved ?? 0}`;
  if (telemetrySkipped) telemetrySkipped.textContent = telemetry.saved_calls ?? 0;
  if (telemetryTokensUsed) telemetryTokensUsed.textContent = telemetry.estimated_tokens_used ?? 0;

  if (cooldownPill) {
    if (telemetry.cooldown_remaining > 0) {
      cooldownPill.textContent = `Cooldown: ${telemetry.cooldown_remaining}s`;
      cooldownPill.style.color = '#fbbf24';
    } else {
      cooldownPill.textContent = `Cooldown: Ready`;
      cooldownPill.style.color = '#34d399';
    }
  }

  if (aiProHeaderBadge) {
    if (!telemetry.is_configured) {
      aiProHeaderBadge.textContent = '✨ AI Pro: No Key';
      aiProHeaderBadge.style.color = '#f87171';
    } else if (telemetry.is_active) {
      aiProHeaderBadge.textContent = '✨ AI Pro: Live Auto';
      aiProHeaderBadge.style.color = '#e879f9';
    } else {
      aiProHeaderBadge.textContent = '✨ AI Pro: Ready';
      aiProHeaderBadge.style.color = '#c084fc';
    }
  }

  // Update toggle state if desynced
  if (toggleAiPro && toggleAiPro.checked !== Boolean(telemetry.is_active)) {
    toggleAiPro.checked = Boolean(telemetry.is_active);
    updateAiProToggleLabel(telemetry.is_active);
  }
}

function updateAiProToggleLabel(isActive) {
  if (aiProToggleStatusText) {
    aiProToggleStatusText.textContent = isActive ? 'AI Pro: ACTIVE' : 'AI Pro: OFF';
    aiProToggleStatusText.style.color = isActive ? '#c084fc' : 'var(--text-muted)';
  }
}

// Toggle AI Pro Switch Handler
if (toggleAiPro) {
  toggleAiPro.addEventListener('change', async () => {
    const shouldActivate = toggleAiPro.checked;
    updateAiProToggleLabel(shouldActivate);

    try {
      const res = await fetch('/api/ai-pro/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: shouldActivate })
      });
      const data = await res.json();

      if (data.telemetry) {
        updateTelemetryUI(data.telemetry);

        if (shouldActivate && !data.telemetry.is_configured) {
          alert('Notice: Gemini API key is not yet configured. Please click "Key" to enter your API key.');
          openKeyModal();
          toggleAiPro.checked = false;
          updateAiProToggleLabel(false);
          return;
        }
      }

      if (shouldActivate) {
        startAiProLoop();
      } else {
        stopAiProLoop();
      }
    } catch (e) {
      console.error('Failed to toggle AI Pro:', e);
      toggleAiPro.checked = !shouldActivate;
      updateAiProToggleLabel(!shouldActivate);
    }
  });
}

function startAiProLoop() {
  stopAiProLoop();
  const intervalSeconds = parseFloat(aiProIntervalSelect?.value || '15');
  console.log(`[AI Pro] Starting frequent auto-inspection loop every ${intervalSeconds}s (Token-Saver active).`);

  // Run first inspection immediately
  runAiProInspection(false);

  aiProAutoScanInterval = setInterval(() => {
    if (toggleAiPro.checked && !isAiProAnalyzing && !isAnalyzing) {
      runAiProInspection(false);
    }
  }, intervalSeconds * 1000);
}

function stopAiProLoop() {
  if (aiProAutoScanInterval) {
    clearInterval(aiProAutoScanInterval);
    aiProAutoScanInterval = null;
    console.log('[AI Pro] Stopped frequent auto-inspection loop.');
  }
}

// When interval dropdown changes
if (aiProIntervalSelect) {
  aiProIntervalSelect.addEventListener('change', () => {
    if (toggleAiPro.checked) {
      startAiProLoop();
    }
  });
}

// Run single AI Pro Inspection
async function runAiProInspection(force = false) {
  if (isAiProAnalyzing) return;
  isAiProAnalyzing = true;

  if (usbcamScanLaser) usbcamScanLaser.classList.add('scanning');

  try {
    const url = `/api/ai-pro/inspect?source=camera&force=${force ? 'true' : 'false'}`;
    const res = await fetch(url, { method: 'POST' });
    const result = await res.json();

    if (!res.ok || !result.success) {
      if (result.code === 'MISSING_API_KEY') {
        alert('Please configure your Gemini API Key first by clicking the Key button.');
        openKeyModal();
        if (toggleAiPro) {
          toggleAiPro.checked = false;
          updateAiProToggleLabel(false);
          stopAiProLoop();
        }
      } else if (result.error) {
        console.warn('[AI Pro] Inspection note:', result.error);
      }
      return;
    }

    // Handle token-saving skipped frames
    if (result.skipped) {
      console.log(`[AI Pro Token-Saver] ${result.message}`);
      if (cooldownPill) {
        cooldownPill.textContent = result.reason === 'static_scene'
          ? `🛡️ Scene Unchanged (${result.diff_pct}%) • Tokens Saved`
          : `🛡️ Cooldown Active (${result.cooldown_remaining}s)`;
        cooldownPill.style.color = '#34d399';
      }
      updateTelemetryUI(result.stats);
      return;
    }

    // New verification verdict from Gemini!
    if (result.data) {
      renderAiProResults(result.data, result.diff_pct);
      updateTelemetryUI(result.stats);
      playSuccessChime(result.data.freshness?.toLowerCase() === 'fresh');
      fetchActiveAlerts();
    }

  } catch (err) {
    console.error('[AI Pro] Inspection request error:', err);
  } finally {
    isAiProAnalyzing = false;
    if (usbcamScanLaser) usbcamScanLaser.classList.remove('scanning');
  }
}

function renderAiProResults(data, diffPct = 0) {
  if (!aiProResultCard) return;

  aiProResultCard.style.display = 'block';

  // Make sure main results dashboard is also visible
  emptyState.style.display = 'none';
  resultsDashboard.style.display = 'flex';

  const isFresh = (data.freshness || '').toLowerCase() === 'fresh';
  const isSpoiled = !isFresh || (data.quality_grade || '').toLowerCase().includes('spoiled');

  // Quality Grade Badge
  if (aiProGradeBadge) {
    aiProGradeBadge.textContent = data.quality_grade || (isFresh ? 'Grade A (Premium)' : 'Spoiled');
    aiProGradeBadge.className = `quality-grade-badge ${isSpoiled ? 'spoiled' : ''}`;
  }

  // Quality Score Pill
  if (aiProScorePill) {
    aiProScorePill.textContent = `Score: ${data.quality_score ?? 90}/100`;
  }

  // Shelf Life & Ripeness
  if (aiProShelfLife) {
    const days = data.estimated_shelf_life_days ?? (isFresh ? 4 : 0);
    aiProShelfLife.textContent = days > 0 ? `⏳ ~${days} Days Remaining` : '❌ Immediate Discard';
  }
  if (aiProRipeness) {
    aiProRipeness.textContent = data.ripeness || 'Optimal Ripe';
  }

  // Observed Visual Defects Chips
  if (aiProDefectsChips) {
    aiProDefectsChips.innerHTML = '';
    const defects = data.defects || [];
    if (defects.length === 0) {
      aiProDefectsChips.innerHTML = '<span class="defect-chip none">✓ No visible defects observed</span>';
    } else {
      defects.forEach(d => {
        const chip = document.createElement('span');
        chip.className = 'defect-chip';
        chip.textContent = `• ${d}`;
        aiProDefectsChips.appendChild(chip);
      });
    }
  }

  // Spoilage warning list
  if (aiProWarningBox && aiProSpoilageList) {
    const indicators = data.spoilage_indicators || [];
    if (indicators.length > 0 || isSpoiled) {
      aiProWarningBox.style.display = 'block';
      aiProSpoilageList.innerHTML = '';
      (indicators.length > 0 ? indicators : ['Cellular decay or spoilage risk detected']).forEach(ind => {
        const li = document.createElement('li');
        li.textContent = ind;
        aiProSpoilageList.appendChild(li);
      });
    } else {
      aiProWarningBox.style.display = 'none';
    }
  }

  // Agronomic Narrative Text
  if (aiProSummaryText) {
    aiProSummaryText.textContent = data.detailed_summary || 'Produce demonstrates good cellular integrity and wholesome commercial condition.';
  }

  // Storage Advice
  if (aiProStorageText) {
    aiProStorageText.textContent = data.storage_recommendation || 'Store produce in a cool, ventilated container.';
  }

  // Token & Latency Footer
  if (aiProTokenInfo) {
    aiProTokenInfo.textContent = `⚡ ${data.engine || 'Gemini 2.5 Flash'} • ${data.tokens_used || 258} tokens • ${data.latency_ms || 750}ms`;
  }

  // Also update standard verdict banner with high-accuracy Gemini result
  if (verdictTag) {
    verdictTag.textContent = isFresh ? '🌿 GEMINI PRO: FRESH' : '⚠️ GEMINI PRO: SPOILED';
  }
  if (verdictTitle) {
    verdictTitle.textContent = `${data.produce} — ${data.quality_grade}`;
  }
  if (verdictDesc) {
    verdictDesc.textContent = data.detailed_summary;
  }
  if (verdictScore) {
    verdictScore.textContent = `${data.quality_score}% Quality`;
  }
  if (verdictMeter) {
    verdictMeter.style.width = `${data.quality_score}%`;
  }
  if (categoryName) {
    categoryName.textContent = data.produce;
  }
  if (categoryTypePill) {
    categoryTypePill.textContent = data.category_type || 'Produce';
  }
}

// "Inspect Now (AI Pro)" button handler
if (btnAiProInspectNow) {
  btnAiProInspectNow.addEventListener('click', () => {
    runAiProInspection(true); // force=true bypasses diff & cooldown
  });
}

// Gemini Key Modal Handlers
function openKeyModal() {
  if (keyModal) keyModal.style.display = 'flex';
}
function closeKeyModal() {
  if (keyModal) keyModal.style.display = 'none';
}

if (btnOpenKeyModal) btnOpenKeyModal.addEventListener('click', openKeyModal);
if (keyModalCloseBtn) keyModalCloseBtn.addEventListener('click', closeKeyModal);
if (keyModalBackdrop) keyModalBackdrop.addEventListener('click', closeKeyModal);
if (btnCancelKey) btnCancelKey.addEventListener('click', closeKeyModal);

if (btnSaveKey) {
  btnSaveKey.addEventListener('click', async () => {
    const keyVal = geminiKeyInput?.value.trim();
    const modelVal = geminiModelSelect?.value || 'gemini-2.5-flash';

    if (!keyVal) {
      alert('Please enter a valid Gemini API key.');
      return;
    }

    try {
      const res = await fetch('/api/ai-pro/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: keyVal, model: modelVal })
      });
      const data = await res.json();

      if (data.success && data.configured) {
        alert('🎉 Gemini API Key successfully saved and activated!');
        closeKeyModal();
        fetchAiProStatus();
      } else {
        alert('Failed to configure key.');
      }
    } catch (e) {
      alert(`Configuration error: ${e.message}`);
    }
  });
}


// ==========================================
// Webcam Controls (HTML5 MediaDevices API)
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

if (btnToggleCamera) {
  btnToggleCamera.addEventListener('click', () => {
    if (currentStream) {
      stopCamera();
    } else {
      startCamera();
    }
  });
}

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

if (btnCapture) btnCapture.addEventListener('click', captureWebcamFrame);

if (toggleAutoscan) {
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
}


// ==========================================
// Dropzone & File Upload
// ==========================================
if (browseLink) {
  browseLink.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });
}
if (dropzone) dropzone.addEventListener('click', () => fileInput.click());

['dragenter', 'dragover'].forEach(eventName => {
  if (dropzone) {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  }
});

['dragleave', 'drop'].forEach(eventName => {
  if (dropzone) {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  }
});

if (dropzone) {
  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    if (dt.files && dt.files[0]) {
      handleFile(dt.files[0]);
    }
  });
}

if (fileInput) {
  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      handleFile(fileInput.files[0]);
    }
  });
}

// Clipboard Paste Support
document.addEventListener('paste', (e) => {
  const items = (e.clipboardData || e.originalEvent.clipboardData).items;
  for (let item of items) {
    if (item.type.indexOf('image') !== -1) {
      const blob = item.getAsFile();
      if (tabButtons[2]) tabButtons[2].click();
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

if (btnRemovePreview) {
  btnRemovePreview.addEventListener('click', (e) => {
    e.stopPropagation();
    uploadedBlob = null;
    fileInput.value = '';
    uploadPreviewOverlay.style.display = 'none';
    btnAnalyzeUpload.disabled = true;
  });
}

if (btnAnalyzeUpload) {
  btnAnalyzeUpload.addEventListener('click', () => {
    if (uploadedBlob) {
      sendImageToApi(uploadedBlob, uploadedBlob.name || 'uploaded_image.jpg');
    }
  });
}

if (btnLoadSample) {
  btnLoadSample.addEventListener('click', async () => {
    try {
      const res = await fetch('test_sample.jpg');
      if (!res.ok) throw new Error('Sample not found');
      const blob = await res.blob();
      handleFile(blob);
      sendImageToApi(blob, 'test_sample.jpg');
    } catch (err) {
      console.error('Error loading sample:', err);
      alert('Could not load test_sample.jpg.');
    }
  });
}


// ==========================================
// API Communication & Render Results
// ==========================================
async function sendImageToApi(imageBlob, filename = 'produce.jpg') {
  if (isAnalyzing) return;
  isAnalyzing = true;

  emptyState.style.display = 'none';
  resultsDashboard.style.display = 'none';
  loadingState.style.display = 'flex';
  if (loadingTitle) loadingTitle.textContent = 'Analyzing Image...';
  if (loadingDesc) loadingDesc.textContent = 'Running edge classifiers on Raspberry Pi 5';
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
    ? 'Produce meets safety and quality standards for consumption or culinary use.'
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
if (btnCopyJson) {
  btnCopyJson.addEventListener('click', () => {
    if (currentResult) {
      navigator.clipboard.writeText(JSON.stringify(currentResult, null, 2)).then(() => {
        btnCopyJson.textContent = '✓ Copied!';
        setTimeout(() => btnCopyJson.textContent = '📋 Copy JSON', 2000);
      });
    }
  });
}

// Fullscreen Modal for image
if (btnFullscreenAnnotated) {
  btnFullscreenAnnotated.addEventListener('click', () => {
    if (annotatedImageDisplay.src) {
      modalImage.src = annotatedImageDisplay.src;
      imageModal.classList.add('open');
    }
  });
}
[modalBackdrop, modalCloseBtn].forEach(el => {
  if (el) el.addEventListener('click', () => imageModal.classList.remove('open'));
});


// ==========================================
// Scan History Storage (localStorage)
// ==========================================
function saveToHistory(data) {
  try {
    let history = JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) || '[]');
    const item = {
      id: Date.now(),
      category: data.category?.label || 'Unknown',
      emoji: data.metadata?.emoji || '🥬',
      freshness: data.freshness?.label || 'Fresh',
      score: ((data.freshness?.score || 0.9) * 100).toFixed(0),
      image: data.annotated_image_base64 || '',
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
      if (historySection) historySection.style.display = 'none';
      return;
    }
    if (historySection) historySection.style.display = 'block';
    if (!historyStrip) return;

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

if (btnClearHistory) {
  btnClearHistory.addEventListener('click', () => {
    localStorage.removeItem(HISTORY_STORAGE_KEY);
    renderHistory();
  });
}


// ==========================================
// FreshScan AI 2.0 Alerts & System Status
// ==========================================
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
      if (emptyAlertsPlaceholder) {
        activeAlertsList.appendChild(emptyAlertsPlaceholder);
        emptyAlertsPlaceholder.style.display = 'block';
      }
      return;
    }

    if (emptyAlertsPlaceholder) emptyAlertsPlaceholder.style.display = 'none';
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
        esp32Badge.textContent = `📡 MQTT Standby`;
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
    fetchAiProStatus();
  });
}

// Global exposes for inline button actions
window.acknowledgeAlert = acknowledgeAlert;
window.clearAlert = clearAlert;

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
  renderHistory();
  loadCameraDevices();
  checkUsbCameraStatus();
  fetchAiProStatus();
  fetchActiveAlerts();
  checkSystemStatus();

  // Background telemetry & alerts sync interval every 4s
  setInterval(() => {
    fetchActiveAlerts();
    checkSystemStatus();
    fetchAiProStatus();
  }, 4000);
});
