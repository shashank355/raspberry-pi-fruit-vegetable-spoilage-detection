#!/usr/bin/env python3
"""
Camera diagnostic tool for Raspberry Pi Camera Module Rev 1.3 (OV5647).
Run this to test camera connectivity, sensor detection, and frame grabbing.
"""
import sys
import os
import subprocess
from pathlib import Path

# Add project root
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.camera import PiCameraManager


def check_system_diagnostics():
    print("=" * 60)
    print(" Raspberry Pi Camera Rev 1.3 (OV5647) Hardware Diagnostics")
    print("=" * 60)

    # 1. Check vcgencmd / libcamera-hello / rpicam-hello if on Pi
    print("\n[1/4] Probing system camera detection utilities...")
    rpicam_cmd = None
    for cmd in ["rpicam-hello", "libcamera-hello"]:
        try:
            res = subprocess.run([cmd, "--list-cameras"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                rpicam_cmd = cmd
                print(f"  ✓ {cmd} detected available cameras:")
                for line in res.stdout.strip().split("\n"):
                    print(f"    {line}")
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    if not rpicam_cmd:
        print("  ℹ libcamera/rpicam utility not found directly (normal on non-Pi or container environments).")

    # 2. Check Video4Linux devices (/dev/video*)
    print("\n[2/4] Checking Video4Linux device nodes (/dev/video*)...")
    v4l_devices = list(Path("/dev").glob("video*"))
    if v4l_devices:
        print(f"  ✓ Found V4L2 device nodes: {[str(d) for d in sorted(v4l_devices)]}")
    else:
        print("  ⚠️ No /dev/video* devices found.")

    # 3. Check Python Picamera2 availability
    print("\n[3/4] Checking Python camera libraries...")
    try:
        from picamera2 import Picamera2
        print("  ✓ 'picamera2' library is installed and available.")
    except Exception as e:
        print(f"  ℹ 'picamera2' not imported: {e}")

    try:
        import cv2
        print(f"  ✓ OpenCV is available (v{cv2.__version__}).")
    except Exception as e:
        print(f"  ⚠️ OpenCV not available: {e}")

    # 4. Initialize PiCameraManager and snap test photo
    print("\n[4/4] Testing snapshot capture via PiCameraManager...")
    try:
        cam = PiCameraManager()
        status = cam.get_status()
        print(f"  • Active Backend: {status['backend']}")
        print(f"  • Hardware Sensor: {status['sensor']}")
        print(f"  • Status Message: {status['message']}")

        rgb_arr, pil_img = cam.capture_frame()
        out_file = "camera_test.jpg"
        pil_img.save(out_file)
        print(f"  ✓ Successfully captured and saved test snapshot to: {out_file} ({pil_img.width}x{pil_img.height})")
    except Exception as e:
        print(f"  ❌ Camera capture failed: {e}")
        print("\nTroubleshooting tips for Raspberry Pi Camera Rev 1.3:")
        print("  1. Ensure 15-pin ribbon cable is seated firmly:")
        print("     - On Pi 4B: Blue tape faces the Ethernet/USB ports.")
        print("     - On Camera Rev 1.3 board: Blue tape faces away from the lens (towards the PCB back).")
        print("  2. In Raspberry Pi OS Bookworm/Bullseye:")
        print("     - Run 'sudo raspi-config' -> Interface Options -> Legacy Camera / Camera -> Enable.")
        print("     - Verify '/boot/firmware/config.txt' contains 'dtoverlay=ov5647' or 'camera_auto_detect=1'.")
        print("  3. Run 'sudo apt install -y python3-picamera2 libcamera-tools'.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    check_system_diagnostics()
