#!/usr/bin/env bash
# ==============================================================================
# FreshScan AI 2.0 - Raspberry Pi 5 + External USB Camera Setup Script
# ==============================================================================
set -e

echo "🍓 ============================================================"
echo "   FreshScan AI 2.0: Raspberry Pi 5 Setup Script"
echo "   Hardware: Raspberry Pi 5 (ARM Cortex-A76 Quad-Core)"
echo "   Sensor  : External USB Camera (V4L2 / UVC)"
echo "   Cloud AI: Gemini AI Pro (Multimodal Quality Inspection)"
echo "🍓 ============================================================"

ARCH=$(uname -m)
echo "🔍 Detected CPU Architecture: $ARCH"

if [ "$ARCH" != "aarch64" ]; then
  echo "⚠️ WARNING: You are running a 32-bit OS ($ARCH)."
  echo "   It is strongly recommended to use Raspberry Pi OS 64-bit (aarch64) for"
  echo "   optimal ARMv8.2-A SIMD acceleration and pre-built Python wheels."
fi

# 1. Update and install essential apt packages for Raspberry Pi 5
echo ""
echo "📦 [1/4] Installing Raspberry Pi OS system dependencies for USB camera & MQTT..."
sudo apt update
sudo apt install -y \
  python3-pip \
  python3-venv \
  python3-dev \
  v4l-utils \
  libv4l-dev \
  libgl1 \
  libglib2.0-0 \
  mosquitto \
  mosquitto-clients

# Enable and start Mosquitto MQTT broker
sudo systemctl enable --now mosquitto || true

# 2. Check Video4Linux USB camera detection
echo ""
echo "📷 [2/4] Checking connected USB video devices..."
if [ -d "/sys/class/video4linux" ]; then
  echo "  Discovered Video4Linux nodes:"
  for dev in /sys/class/video4linux/video*; do
    if [ -f "$dev/name" ]; then
      NODE_NAME=$(basename "$dev")
      NAME=$(cat "$dev/name")
      echo "    • /dev/$NODE_NAME: $NAME"
    fi
  done
else
  echo "  ℹ No /sys/class/video4linux found. Plug in an external USB camera."
fi

# 3. Setup Python Virtual Environment
echo ""
echo "🐍 [3/4] Setting up Python virtual environment..."
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

. venv/bin/activate
pip install --upgrade pip

echo "📦 Installing Python requirements (including OpenCV & Google GenAI SDK)..."
if [ -f "requirements-pi.txt" ]; then
  pip install -r requirements-pi.txt
else
  pip install -r requirements.txt
fi

# 4. Run USB Camera Diagnostic
echo ""
echo "🎯 [4/4] Running USB camera hardware diagnostics..."
python test_camera.py

echo ""
echo "============================================================"
echo "🎉 Setup complete on Raspberry Pi 5!"
echo "   To start the web dashboard:"
echo "     ./run.sh"
echo "   Or start API directly:"
echo "     python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
echo "============================================================"
echo ""
