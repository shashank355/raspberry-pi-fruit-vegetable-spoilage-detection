import io
import os
import time
import threading
from pathlib import Path
from typing import Tuple, Optional, Generator, List, Dict, Any
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import cv2
except ImportError:
    cv2 = None


class USBCameraManager:
    """
    Hardware Camera Driver for External USB Cameras on Raspberry Pi 5.
    Uses Video4Linux2 (V4L2) via OpenCV with automatic USB device discovery,
    thread-safe frame grabbing, MJPEG live streaming, and graceful simulation fallback.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(USBCameraManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 20, camera_index=None):
        if self._initialized:
            return
        self._initialized = True
        self.width = width
        self.height = height
        self.fps = fps
        self.backend = None
        self.camera_device = None
        self.device_index = None
        self.device_name = "Unknown Camera"
        self.device_path = ""
        self.is_streaming = False
        self.latest_frame_bytes = None
        self._cam_lock = threading.Lock()

        # Determine target index from config or argument
        from src.config import Config
        target_idx = camera_index if camera_index is not None else Config.CAMERA_INDEX
        self._init_camera(target_idx)

    @staticmethod
    def list_available_cameras() -> List[Dict[str, Any]]:
        """
        Scans Video4Linux devices on the system to discover all connected cameras.
        Returns list of device metadata dicts.
        """
        cameras = []
        v4l_dir = Path("/sys/class/video4linux")

        if v4l_dir.exists():
            for p in sorted(v4l_dir.glob("video*")):
                idx_str = p.name.replace("video", "")
                if not idx_str.isdigit():
                    continue
                idx = int(idx_str)
                name_file = p / "name"
                name = name_file.read_text().strip() if name_file.exists() else f"Camera /dev/video{idx}"

                # Classify whether this is an external USB camera
                lower_name = name.lower()
                is_usb = any(term in lower_name for term in ["usb", "uvc", "webcam", "external"])

                cameras.append({
                    "index": idx,
                    "node": f"/dev/video{idx}",
                    "name": name,
                    "is_usb": is_usb
                })
        else:
            # Fallback probe for indices 0 to 4 if sysfs not accessible
            if cv2 is not None:
                for idx in range(5):
                    cap = cv2.VideoCapture(idx)
                    if cap.isOpened():
                        cameras.append({
                            "index": idx,
                            "node": f"/dev/video{idx}",
                            "name": f"V4L2 Camera {idx}",
                            "is_usb": True
                        })
                        cap.release()

        return cameras

    def _resolve_camera_index(self, target_idx) -> Optional[int]:
        """Resolves target camera index: handles 'auto', string numbers, or device paths."""
        discovered = self.list_available_cameras()

        # If 'auto' or unspecified, search for an external USB camera first
        if target_idx in ("auto", None, "", -1):
            for cam in discovered:
                if cam["is_usb"]:
                    print(f"[USBCameraManager] Auto-selected USB camera: {cam['name']} ({cam['node']})")
                    return cam["index"]
            # If no camera has 'usb' in name, try first available
            if discovered:
                print(f"[USBCameraManager] No specific USB keyword match, selecting first camera: {discovered[0]['name']}")
                return discovered[0]["index"]
            return 0

        # If target_idx is a path like '/dev/video2'
        if isinstance(target_idx, str) and target_idx.startswith("/dev/video"):
            try:
                return int(target_idx.replace("/dev/video", ""))
            except ValueError:
                pass

        try:
            return int(target_idx)
        except (ValueError, TypeError):
            return 0

    def _init_camera(self, target_idx=None):
        if cv2 is None:
            print("[USBCameraManager] OpenCV (cv2) is not available. Operating in simulation mode.")
            self._enter_mock_mode()
            return

        resolved_idx = self._resolve_camera_index(target_idx)
        discovered = {c["index"]: c for c in self.list_available_cameras()}

        # Candidate indices to try: resolved index first, then all discovered USB cameras, then 0..4
        candidates = [resolved_idx]
        for c in discovered.values():
            if c["index"] not in candidates:
                candidates.append(c["index"])

        opened_cap = None
        chosen_idx = None

        for idx in candidates:
            try:
                print(f"[USBCameraManager] Probing USB Camera on /dev/video{idx}...")
                cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(idx)

                if cap.isOpened():
                    # Set optimal resolution & FPS
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    cap.set(cv2.CAP_PROP_FPS, self.fps)
                    # Attempt to set MJPG fourcc for optimal USB bus bandwidth on Pi 5
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        opened_cap = cap
                        chosen_idx = idx
                        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        print(f"[USBCameraManager] Successfully connected to USB Camera at /dev/video{idx} ({actual_w}x{actual_h})")
                        break
                    else:
                        cap.release()
            except Exception as e:
                print(f"[USBCameraManager] Probe index {idx} failed: {e}")

        if opened_cap is not None:
            self.camera_device = opened_cap
            self.device_index = chosen_idx
            self.device_path = f"/dev/video{chosen_idx}"
            self.device_name = discovered.get(chosen_idx, {}).get("name", f"USB Camera ({self.device_path})")
            self.backend = "opencv_usb_v4l2"
        else:
            print("[USBCameraManager] No physical USB camera could be opened. Operating in simulation mode.")
            self._enter_mock_mode()

    def _enter_mock_mode(self):
        self.camera_device = None
        self.device_index = -1
        self.device_path = "/dev/video_virtual"
        self.device_name = "Virtual USB Camera (Simulation)"
        self.backend = "mock"

    def switch_camera(self, target_idx) -> bool:
        """Dynamically switch to a different camera device index."""
        with self._cam_lock:
            if self.camera_device is not None:
                try:
                    self.camera_device.release()
                except Exception:
                    pass
                self.camera_device = None

            self._init_camera(target_idx)
            return self.backend == "opencv_usb_v4l2"

    def get_status(self) -> Dict[str, Any]:
        is_hardware = self.backend == "opencv_usb_v4l2" and self.camera_device is not None
        actual_w = int(self.camera_device.get(cv2.CAP_PROP_FRAME_WIDTH)) if is_hardware else self.width
        actual_h = int(self.camera_device.get(cv2.CAP_PROP_FRAME_HEIGHT)) if is_hardware else self.height

        return {
            "available": is_hardware,
            "backend": self.backend,
            "sensor": self.device_name,
            "device_index": self.device_index,
            "device_path": self.device_path,
            "resolution": f"{actual_w}x{actual_h}",
            "fps": self.fps,
            "platform": "Raspberry Pi 5",
            "ready": True,
            "message": f"External USB Camera '{self.device_name}' ready on Raspberry Pi 5" if is_hardware else "Virtual USB Camera simulation mode (No physical USB camera connected)"
        }

    def capture_frame(self) -> Tuple[np.ndarray, Image.Image]:
        """
        Captures a high-resolution frame from the external USB camera.
        Returns:
            (numpy_rgb_array, pil_image)
        """
        with self._cam_lock:
            if self.backend == "opencv_usb_v4l2" and self.camera_device:
                ret, bgr_arr = self.camera_device.read()
                if ret and bgr_arr is not None:
                    rgb_arr = cv2.cvtColor(bgr_arr, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb_arr)
                    return rgb_arr, pil_img
                else:
                    print("[USBCameraManager] Frame read failed from USB camera. Attempting recovery...")
                    # Try one re-read
                    ret, bgr_arr = self.camera_device.read()
                    if ret and bgr_arr is not None:
                        rgb_arr = cv2.cvtColor(bgr_arr, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(rgb_arr)
                        return rgb_arr, pil_img

            # Fallback to simulation mode if hardware read fails or in mock
            from src.config import Config
            sample_path = Path(Config.PROJECT_ROOT) / "test_sample.jpg"
            if sample_path.exists():
                pil_img = Image.open(sample_path).convert("RGB")
            else:
                pil_img = Image.new("RGB", (self.width, self.height), color=(34, 139, 34))
                draw = ImageDraw.Draw(pil_img)
                draw.text((20, 20), "USB Camera Simulation (RPi 5)", fill=(255, 255, 255))

            rgb_arr = np.array(pil_img)
            return rgb_arr, pil_img

    def generate_mjpeg_stream(self) -> Generator[bytes, None, None]:
        """
        Generates a continuous MJPEG multipart stream for live web preview.
        """
        while True:
            try:
                rgb_arr, pil_img = self.capture_frame()
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=80)
                frame_bytes = buf.getvalue()

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
                time.sleep(1.0 / max(1, self.fps))
            except Exception:
                time.sleep(0.5)

    def close(self):
        with self._cam_lock:
            if self.camera_device is not None:
                try:
                    self.camera_device.release()
                except Exception:
                    pass
            self.camera_device = None


# Backward-compatibility aliases for legacy code and imports
PiCameraManager = USBCameraManager
CameraManager = USBCameraManager
