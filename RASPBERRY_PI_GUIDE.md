# FreshScan AI 2.0 — Raspberry Pi 5 + External USB Camera & Gemini AI Pro Guide

This guide details how to set up and deploy **FreshScan AI 2.0** on a **Raspberry Pi 5** using any **standard External USB Camera (UVC/V4L2)** combined with **Gemini AI Pro** multimodal quality inspection and **Token-Saving Guardrails**.

---

## 1. Hardware Overview & Specifications

- **Single Board Computer**: Raspberry Pi 5 (4GB / 8GB / 16GB RAM)
- **Processor**: Broadcom BCM2712, Quad-core ARM Cortex-A76 @ 2.4 GHz (3x faster inference than Pi 4B)
- **Camera Interface**: External USB Camera (UVC / Video4Linux2 via USB 3.0 ports)
- **Local Edge Inference**: TensorFlow Lite with ARMv8.2-A / Neon SIMD acceleration (~15–25ms latency)
- **Cloud Multimodal AI**: Google Gemini AI Pro (`gemini-2.5-flash` or `gemini-1.5-flash`)
- **Token Efficiency Guard**: Motion/structural frame difference gating + 512px downscaling + adaptive cooldown (protects token limits)
- **Alert Panel**: ESP32 wireless LCD & 10-LED bank over MQTT + Telegram Bot alerts

---

## 2. External USB Camera Connection

1. Plug your USB camera into one of the **blue USB 3.0 ports** on the Raspberry Pi 5 for high bandwidth and stable MJPEG streaming.
2. Confirm the Linux kernel detected the USB camera:
   ```bash
   lsusb
   ```
   You should see your camera chipset (e.g. `USB2.0 PC CAMERA`, `Logitech C920`, `eMeet`, etc.).
3. Check the created Video4Linux device nodes:
   ```bash
   ls -la /dev/video*
   ```
   Or query device names:
   ```bash
   cat /sys/class/video4linux/video*/name
   ```
4. **Auto-Selection**: FreshScan AI automatically discovers connected USB cameras and selects the active USB video node. You can also pick a specific device from the dashboard dropdown or set `CAMERA_INDEX=auto` (or `CAMERA_INDEX=2`) in `.env`.

---

## 3. Gemini AI Pro & Token Saver Configuration

To use the **AI Pro** toggle button without exhausting your Gemini token limits, the system implements 4 levels of token conservation:

1. **Scene-Change / Motion Gating**:
   A lightweight 64x64 frame difference is computed on each frame. If the produce hasn't moved or the scene is unchanged, the Gemini API call is **skipped**, preserving your tokens.
2. **Pre-Optimized Image Downscaling**:
   Images are automatically resized to 512x512 JPEG at 80% compression before dispatch. In Gemini multimodal pricing, a 512px image costs only **1 tile (~258 tokens)** compared to 1000+ tokens for 1080p.
3. **Adaptive Cooldown Protection**:
   Enforces a configurable minimum delay (e.g. 10s cooldown) between calls to prevent rapid firing.
4. **Local Edge Pre-Check**:
   The local edge model runs for free (0 tokens) to pre-classify produce and filter out blank backgrounds.

### Setting your Gemini API Key:

#### Option A: In the `.env` file
Open `.env` and set:
```bash
GEMINI_API_KEY=AIzaSyYourActualKeyHere
GEMINI_MODEL=gemini-2.5-flash
GEMINI_AUTO_INTERVAL=15.0
GEMINI_COOLDOWN=10.0
GEMINI_FRAME_DIFF_THRESHOLD=10.0
```

#### Option B: In the Web Dashboard
Click the **🔑 Key** button on the AI Pro studio card, paste your API key, and click **Save & Activate**.

---

## 4. Software Installation & Setup

Run the automated Raspberry Pi 5 setup script:
```bash
cd Image-Based-Food-Freshness-Prediction-System
chmod +x setup_pi.sh test_camera.py run.sh
./setup_pi.sh
```

### Manual Installation:
```bash
# 1. System packages
sudo apt update
sudo apt install -y python3-pip python3-venv v4l-utils libv4l-dev libgl1 mosquitto mosquitto-clients

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-pi.txt
```

---

## 5. Camera Diagnostic Verification

Run the USB camera diagnostic tool:
```bash
python test_camera.py
```
Output:
```text
=================================================================
 🍓 Raspberry Pi 5 • External USB Camera Hardware Diagnostics
=================================================================
  • Active Device : USB2.0 PC CAMERA: USB2.0 PC CAM
  • Node Path     : /dev/video2
  • Backend       : opencv_usb_v4l2
  • Resolution    : 640x480 (or 1280x720)
  • Platform      : Raspberry Pi 5
  • Ready         : True
  ✓ Successfully captured and saved test snapshot to: camera_test.jpg
```

---

## 6. Running the System

Start the server:
```bash
./run.sh
```
Or with Uvicorn:
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Open your browser to:
`http://<RASPBERRY_PI_IP>:8000`

### Using the Features in the Dashboard:
1. **USB Camera Feed**: Live streaming from your external USB webcam.
2. **Camera Selector**: Switch between video devices in the USB banner.
3. **✨ AI Pro Toggle Switch**:
   - Turn **ON**: Automatically captures live frames at your chosen interval (e.g. every 15s) and sends them to Gemini API for deep quality inspection.
   - When the frame has not changed, the **Token Saver** automatically protects your token quota by skipping the call and reusing the verified verdict.
   - Turn **OFF**: Pauses Gemini calls immediately and reverts to edge inference only.
4. **⚡ Inspect Now (AI Pro)**: Force an immediate Gemini inspection on demand.

---

## 7. CLI Single-Shot & Continuous Loop

You can also run headless scanning from the terminal:
```bash
# Single capture with local model:
python capture_and_classify.py

# Single capture with Gemini AI Pro inspection:
python capture_and_classify.py --ai-pro

# Continuous monitoring loop every 10 seconds:
python capture_and_classify.py --loop --interval 10 --ai-pro
```
