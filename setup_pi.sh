#!/usr/bin/env bash
# ==============================================================================
# FreshScan AI - Raspberry Pi 4B + Camera Rev 1.3 Setup Script
# ==============================================================================
set -e

echo "🍓 ============================================================"
echo "   FreshScan AI: Raspberry Pi 4B (4GB) Setup Script"
echo "   Sensor: Raspberry Pi Camera Module Rev 1.3 (OV5647)"
echo "🍓 ============================================================"

ARCH=$(uname -m)
echo "🔍 Detected CPU Architecture: $ARCH"

if [ "$ARCH" != "aarch64" ]; then
  echo "⚠️ WARNING: You are running a 32-bit OS ($ARCH)."
  echo "   It is strongly recommended to use Raspberry Pi OS 64-bit (aarch64) for"
  echo "   optimal TensorFlow Lite performance and pre-built Python wheels."
fi

# 1. Update and install essential apt packages
echo ""
echo "📦 [1/5] Installing Raspberry Pi OS system dependencies..."
sudo apt update
sudo apt install -y \
  python3-pip \
  python3-venv \
  python3-picamera2 \
  libcamera-tools \
  v4l-utils \
  libgl1 \
  libglib2.0-0 \
  libatlas-base-dev \
  mosquitto \
  mosquitto-clients

# Enable and start Mosquitto MQTT broker
sudo systemctl enable --now mosquitto || true

# 2. Check Camera Configuration in config.txt
echo ""
echo "📷 [2/5] Checking Raspberry Pi Camera Rev 1.3 hardware configuration..."
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
  CONFIG_FILE="/boot/config.txt"
fi

if [ -f "$CONFIG_FILE" ]; then
  if grep -q "camera_auto_detect=1" "$CONFIG_FILE" || grep -q "dtoverlay=ov5647" "$CONFIG_FILE"; then
    echo "  ✓ Camera overlay found in $CONFIG_FILE."
  else
    echo "  ℹ Adding camera overlay to $CONFIG_FILE..."
    echo "dtoverlay=ov5647" | sudo tee -a "$CONFIG_FILE" >/dev/null
    echo "  ✓ Added 'dtoverlay=ov5647' to $CONFIG_FILE (reboot may be required if not already loaded)."
  fi
fi

# 3. Increase swapfile space to ensure smooth package installations
echo ""
echo "🧠 [3/5] Checking swap configuration..."
if [ -f /etc/dphys-swapfile ]; then
  CURRENT_SWAP=$(grep -oP '^CONF_SWAPSIZE=\K[0-9]+' /etc/dphys-swapfile || echo "100")
  if [ "$CURRENT_SWAP" -lt 1024 ]; then
    echo "  ℹ Increasing swap size to 1024MB to prevent out-of-memory during pip installs..."
    sudo dphys-swapfile swapoff || true
    sudo sed -i 's/^CONF_SWAPSIZE=[0-9]*/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
    sudo dphys-swapfile setup || true
    sudo dphys-swapfile swapon || true
    echo "  ✓ Swap increased to 1024MB."
  fi
fi

# 4. Setup Python Virtual Environment with system-site-packages for Picamera2 access
echo ""
echo "🐍 [4/5] Setting up Python virtual environment (with --system-site-packages for picamera2)..."
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  python3 -m venv --system-site-packages venv
fi

. venv/bin/activate
pip install --upgrade pip

echo "📦 Installing Python requirements..."
if [ -f "requirements-pi.txt" ]; then
  pip install -r requirements-pi.txt
else
  pip install -r requirements.txt
fi

# 5. Run Camera Test Diagnostic
echo ""
echo "🎯 [5/5] Running camera hardware diagnostic..."
python test_camera.py

echo ""
echo "============================================================"
echo "🎉 Setup complete! You are ready to run FreshScan AI."
echo ""
echo "To start the web server:"
echo "   ./run.sh"
echo ""
echo "To run a single capture directly from terminal:"
echo "   python capture_and_classify.py"
echo "============================================================"
