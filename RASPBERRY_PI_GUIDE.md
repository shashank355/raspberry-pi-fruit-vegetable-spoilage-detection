# FreshScan AI — Raspberry Pi 4B + Camera Module Rev 1.3 Guide

This guide explains how to set up, optimize, and run the **FreshScan AI Produce Freshness Classifier** on a **Raspberry Pi 4 Model B (4GB RAM)** equipped with the **Raspberry Pi Camera Module Rev 1.3 (OmniVision OV5647)**.

---

## 1. Hardware Overview & Specifications

- **Single Board Computer**: Raspberry Pi 4 Model B (4GB LPDDR4 RAM)
- **Processor**: Broadcom BCM2711, Quad-core Cortex-A72 (ARMv8 64-bit) @ 1.5 GHz
- **Camera Module**: Raspberry Pi Camera Rev 1.3 (5MP OmniVision OV5647 sensor, 15-pin CSI ribbon)
- **AI Inference Engine**: TensorFlow Lite (optimized with XNNPACK ARM NEON SIMD)
- **RAM Footprint**: ~120–250 MB during active inference (leaving >3.5 GB free)
- **Inference Latency**: ~60–100 ms per image

---

## 2. Hardware Wiring (Rev 1.3 Camera Connection)

The Rev 1.3 Camera connects to the Raspberry Pi 4B using a **15-pin flat flexible ribbon cable (FFC)** into the dedicated **CSI Camera port** (located between the Micro-HDMI ports and the 3.5mm audio jack):

```
+-------------------------------------------------------------+
|  [Ethernet] [USB 3.0] [USB 2.0]                             |
|                                  [CSI Port] <-- Connect here|
|                                    ||                       |
|                             [Blue tape faces                |
|                              Ethernet/USB ports]            |
|                                                             |
|  [Micro-HDMI 0]  [Micro-HDMI 1]  [Power USB-C]              |
+-------------------------------------------------------------+
```

### Cable Orientation Rules:
1. **On the Raspberry Pi 4B board**:
   - Gently pull the black plastic collar of the **CAMERA** port upward.
   - Insert the ribbon cable with the **blue tape side facing the USB and Ethernet ports** (the exposed silver contacts must face the micro-HDMI ports).
   - Push the black plastic collar back down to secure the ribbon firmly.
2. **On the Camera Rev 1.3 PCB**:
   - The **blue tape side faces away from the camera lens** (towards the back of the camera circuit board).
   - The exposed silver contacts face the front (lens side).

---

## 3. Raspberry Pi OS Configuration

> [!IMPORTANT]
> **Use Raspberry Pi OS 64-bit (Debian Bookworm or Bullseye, `aarch64`)**. 64-bit OS is required for pre-built modern TensorFlow wheels and full ARM NEON acceleration.

### Step 3.1: Enable Camera Overlay in `config.txt`
In Raspberry Pi OS Bookworm, edit `/boot/firmware/config.txt` (or `/boot/config.txt` on Bullseye):
```bash
sudo nano /boot/firmware/config.txt
```
Ensure the following line is present under `[all]`:
```ini
dtoverlay=ov5647
```
*(If you see `camera_auto_detect=1`, the Pi may auto-detect OV5647; adding `dtoverlay=ov5647` explicitly guarantees sensor initialization).*

After editing, reboot the Pi:
```bash
sudo reboot
```

### Step 3.2: Verify Camera Detection
Once rebooted, test sensor detection:
```bash
rpicam-hello --list-cameras
# or on Bullseye:
libcamera-hello --list-cameras
```
You should see:
```text
Available cameras:
0 : ov5647 [2592x1944 10-bit RGGB] (/base/soc/i2c0mux/i2c@1/ov5647@36)
```

---

## 4. One-Click Setup

Inside the project directory on your Raspberry Pi:

```bash
cd Image-Based-Food-Freshness-Prediction-System
chmod +x setup_pi.sh run.sh capture_and_classify.py
./setup_pi.sh
```

The `setup_pi.sh` script will:
1. Install system packages (`libcamera-tools`, `python3-picamera2`, `libgl1`, `v4l-utils`).
2. Verify camera drivers and configuration.
3. Configure swap space (prevents pip out-of-memory).
4. Create a virtual environment with `--system-site-packages` so Python can access native `picamera2` hardware acceleration.
5. Install optimized requirements.
6. Run camera diagnostic tests.

---

## 5. Running the Application

### Option A: Web Interface (Live Stream + Remote Access)
Start the web server:
```bash
./run.sh
```
Open your browser on the Pi or on any device on your local Wi-Fi:
```text
http://<your-raspberry-pi-ip>:8000
```

- Navigate to the **"Pi Camera Rev 1.3"** tab.
- View the live camera stream directly from the hardware.
- Click **"Snap Pi Camera & Analyze"** to classify produce.
- Or toggle **"Auto-Scan"** for hands-free scanning every 3 seconds.

---

### Option B: Standalone Command-Line Tool (Headless Mode)
If you are running the Pi headless (without a monitor) or want to trigger scans from a script or physical button:

```bash
# Activate virtual environment
source venv/bin/activate

# Snap a photo and classify immediately:
python capture_and_classify.py

# Continuous scanning every 3 seconds:
python capture_and_classify.py --loop --interval 3.0
```

**Example Terminal Output:**
```text
📸 [Pi Camera Rev 1.3] Capturing frame...
⚡ Frame captured in 81.3ms (1280x720)
🧠 Running AI Freshness inference...

==================================================
✨ FreshScan AI Analysis Result (Engine: TFLITE):
   • Category   : Apple (99.4%)
   • Condition  : [FRESH] Fresh (98.9%)
   • Inference  : 66.3ms
   • Saved to   : annotated_result.jpg
==================================================
```

---

## 6. Testing & Diagnostics

To quickly check your camera hardware anytime:
```bash
python test_camera.py
```
This tests:
1. `rpicam-hello` / `libcamera-hello` system camera detection.
2. Video4Linux device nodes (`/dev/video*`).
3. Python `picamera2` and OpenCV bindings.
4. Takes a test snapshot and saves it to `camera_test.jpg`.

---

## 7. Troubleshooting

| Issue | Cause | Fix |
| :--- | :--- | :--- |
| **"No camera detected"** | Ribbon cable loose or inverted | Check cable seating. Blue tape on Pi board must face Ethernet/USB ports. Blue tape on Camera PCB faces away from lens. |
| **"picamera2: camera not found"** | Missing device tree overlay | Add `dtoverlay=ov5647` to `/boot/firmware/config.txt` and reboot. |
| **Permission denied on `/dev/video0`** | User not in video group | Run `sudo usermod -a -G video $USER` and log back in. |
| **Out of memory during `pip install`** | Small default swap file (100MB) | Run `./setup_pi.sh` or increase swap with `sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile && sudo dphys-swapfile setup && sudo dphys-swapfile swapon`. |
