import io
import time
import threading
from pathlib import Path
from typing import Tuple, Optional, Generator
import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None

# Try importing Picamera2 (Official Raspberry Pi OS camera interface)
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except (ImportError, Exception):
    Picamera2 = None
    PICAMERA2_AVAILABLE = False


class PiCameraManager:
    """
    Hardware Camera Driver for Raspberry Pi Camera Module v1.3 (OmniVision OV5647).
    Supports:
      1. Picamera2 (Modern standard on Raspberry Pi OS Bookworm/Bullseye 64-bit)
      2. OpenCV / V4L2 fallback (e.g. /dev/video0 or libcamerify)
      3. Mock fallback for local testing without physical camera hardware
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PiCameraManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, width: int = 1280, height: int = 720, fps: int = 20):
        if self._initialized:
            return
        self._initialized = True
        self.width = width
        self.height = height
        self.fps = fps
        self.backend = None
        self.camera_device = None
        self.is_streaming = False
        self.latest_frame_bytes = None
        self._cam_lock = threading.Lock()
        self._init_camera()

    def _init_camera(self):
        # 1. Attempt Picamera2 initialization
        if PICAMERA2_AVAILABLE:
            try:
                print("[PiCameraManager] Probing Picamera2 for Raspberry Pi Camera Rev 1.3 (OV5647)...")
                cam = Picamera2()
                camera_info = cam.camera_properties
                print(f"[PiCameraManager] Picamera2 properties: {camera_info}")
                config = cam.create_preview_configuration(
                    main={"size": (self.width, self.height), "format": "RGB888"}
                )
                cam.configure(config)
                cam.start()
                time.sleep(1.0)  # Allow sensor exposure and white balance to settle
                self.camera_device = cam
                self.backend = "picamera2"
                print("[PiCameraManager] Successfully initialized via Picamera2.")
                return
            except Exception as e:
                print(f"[PiCameraManager] Picamera2 probe failed ({e}). Trying V4L2/OpenCV...")

        # 2. Attempt OpenCV / V4L2 fallback
        if cv2 is not None:
            try:
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        self.camera_device = cap
                        self.backend = "opencv_v4l2"
                        print("[PiCameraManager] Successfully initialized via OpenCV V4L2 (/dev/video0).")
                        return
                    cap.release()
            except Exception as e:
                print(f"[PiCameraManager] OpenCV probe failed ({e}).")

        # 3. Fallback to mock simulation
        self.backend = "mock"
        print("[PiCameraManager] No physical camera found or drivers unavailable. Operating in simulation mode.")

    def get_status(self) -> dict:
        is_hardware = self.backend in ("picamera2", "opencv_v4l2")
        return {
            "available": is_hardware,
            "backend": self.backend,
            "sensor": "Raspberry Pi Camera Rev 1.3 (OV5647)" if is_hardware else "Virtual Simulation Camera",
            "resolution": f"{self.width}x{self.height}",
            "ready": True,
            "message": "Physical Pi Camera Rev 1.3 ready" if is_hardware else "Running in simulation mode (No physical CSI camera detected)"
        }

    def capture_frame(self) -> Tuple[np.ndarray, Image.Image]:
        """
        Captures a high-resolution frame from the camera.
        Returns:
            (numpy_rgb_array, pil_image)
        """
        with self._cam_lock:
            if self.backend == "picamera2" and self.camera_device:
                # Picamera2 returns RGB numpy array directly
                rgb_arr = self.camera_device.capture_array()
                pil_img = Image.fromarray(rgb_arr)
                return rgb_arr, pil_img

            elif self.backend == "opencv_v4l2" and self.camera_device:
                ret, bgr_arr = self.camera_device.read()
                if not ret or bgr_arr is None:
                    raise RuntimeError("Failed to read frame from OpenCV camera device.")
                rgb_arr = cv2.cvtColor(bgr_arr, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_arr)
                return rgb_arr, pil_img

            else:
                # Simulation mode: Load test_sample.jpg if exists or generate synthesized image
                from src.config import Config
                sample_path = Path(Config.PROJECT_ROOT) / "test_sample.jpg"
                if sample_path.exists():
                    pil_img = Image.open(sample_path).convert("RGB")
                else:
                    pil_img = Image.new("RGB", (self.width, self.height), color=(34, 139, 34))
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
                time.sleep(1.0 / self.fps)
            except Exception as e:
                time.sleep(0.5)

    def close(self):
        with self._cam_lock:
            if self.backend == "picamera2" and self.camera_device:
                try:
                    self.camera_device.stop()
                    self.camera_device.close()
                except Exception:
                    pass
            elif self.backend == "opencv_v4l2" and self.camera_device:
                try:
                    self.camera_device.release()
                except Exception:
                    pass
            self.camera_device = None
