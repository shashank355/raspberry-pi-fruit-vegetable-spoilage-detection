#!/usr/bin/env python3
"""
Camera diagnostic tool for External USB Cameras on Raspberry Pi 5.
Probes connected V4L2 USB cameras, tests frame capture, and verifies streaming capabilities.
"""
import sys
import os
import subprocess
from pathlib import Path

# Add project root
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.camera import USBCameraManager


def check_system_diagnostics():
    print("=" * 65)
    print(" 🍓 Raspberry Pi 5 • External USB Camera Hardware Diagnostics")
    print("=" * 65)

    # 1. Check Video4Linux devices (/dev/video*) and names
    print("\n[1/4] Probing Video4Linux device nodes (/dev/video*)...")
    v4l_devices = list(Path("/dev").glob("video*"))
    if v4l_devices:
        print(f"  ✓ Found V4L2 device nodes: {[str(d) for d in sorted(v4l_devices)]}")
    else:
        print("  ⚠️ No /dev/video* devices found.")

    # List identified camera names
    discovered = USBCameraManager.list_available_cameras()
    print("\n[2/4] Discovered Camera Sensors:")
    for cam in discovered:
        usb_tag = " [External USB Camera]" if cam["is_usb"] else " [Integrated / Virtual]"
        print(f"  • {cam['node']}: {cam['name']}{usb_tag}")

    # 2. Check OpenCV availability and build info
    print("\n[3/4] Checking OpenCV & Video4Linux backend...")
    try:
        import cv2
        print(f"  ✓ OpenCV is available (v{cv2.__version__}).")
    except Exception as e:
        print(f"  ❌ OpenCV not available: {e}")

    # 3. Test frame capture via USBCameraManager
    print("\n[4/4] Testing snapshot capture via USBCameraManager...")
    try:
        cam = USBCameraManager()
        status = cam.get_status()
        print(f"  • Active Device : {status['sensor']}")
        print(f"  • Node Path     : {status['device_path']}")
        print(f"  • Backend       : {status['backend']}")
        print(f"  • Resolution    : {status['resolution']}")
        print(f"  • Platform      : {status['platform']}")
        print(f"  • Ready         : {status['ready']}")

        rgb_arr, pil_img = cam.capture_frame()
        out_file = "camera_test.jpg"
        pil_img.save(out_file)
        print(f"  ✓ Successfully captured and saved test snapshot to: {out_file} ({pil_img.width}x{pil_img.height})")
    except Exception as e:
        print(f"  ❌ Camera capture failed: {e}")
        print("\nTroubleshooting tips for External USB Camera on Raspberry Pi 5:")
        print("  1. Ensure the USB camera is plugged into one of the blue USB 3.0 ports on the Pi 5.")
        print("  2. Run 'lsusb' to verify the Linux kernel detects your camera chipset.")
        print("  3. Run 'v4l2-ctl --list-devices' to check the mapped device node.")
        print("  4. Set 'CAMERA_INDEX=auto' (or the specific index like 'CAMERA_INDEX=2') in .env.")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    check_system_diagnostics()
