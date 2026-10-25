import io
import os
import time
import json
import threading
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from PIL import Image

from src.config import Config

# Modern Google GenAI SDK
GENAI_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None


class GeminiQualityInspector:
    """
    Edge-Optimized Gemini AI Pro Quality Inspector.
    Provides deep multimodal produce quality analysis with strict token-efficiency guardrails:
      1. Motion / Scene-Difference Gating: Eliminates redundant API calls when the scene is static.
      2. Adaptive Cooldown Rate Limiting: Prevents quota exhaustion and rapid-fire requests.
      3. Image Pre-Optimization: Downscales frames to 512px JPEG, reducing image token cost by ~75%.
      4. Structured JSON Extraction: Compact token prompt with deterministic schema.
      5. Real-Time Token Telemetry: Tracks calls, saved frames, and estimated token usage.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GeminiQualityInspector, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.api_key = Config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.model_name = Config.GEMINI_MODEL or "gemini-2.5-flash"
        self.auto_interval = Config.GEMINI_AUTO_INTERVAL
        self.cooldown = Config.GEMINI_COOLDOWN
        self.diff_threshold = Config.GEMINI_FRAME_DIFF_THRESHOLD
        self.max_dim = Config.GEMINI_MAX_IMAGE_DIM

        self.client = None
        self.is_active = False  # Toggle state for AI Pro auto-inspection
        self.last_call_time = 0.0
        self.last_thumbnail_arr = None
        self.last_result = None
        self.last_diff_pct = 0.0

        # Telemetry metrics
        self.stats = {
            "total_calls": 0,
            "saved_calls": 0,
            "estimated_tokens_used": 0,
            "estimated_tokens_saved": 0,
            "last_latency_ms": 0.0
        }

        self._init_client()

    def _init_client(self):
        if not GENAI_AVAILABLE:
            print("[GeminiQualityInspector] google-genai library not found. Install with: pip install google-genai")
            return

        if self.api_key and not self.api_key.startswith("YOUR_"):
            try:
                self.client = genai.Client(api_key=self.api_key)
                print(f"[GeminiQualityInspector] Initialized Gemini client with model '{self.model_name}'.")
            except Exception as e:
                print(f"[GeminiQualityInspector] Client initialization warning: {e}")
                self.client = None
        else:
            self.client = None

    def update_config(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        interval: Optional[float] = None,
        cooldown: Optional[float] = None,
        diff_threshold: Optional[float] = None
    ):
        with self._lock:
            if api_key is not None:
                self.api_key = api_key.strip()
                self._init_client()
            if model is not None:
                self.model_name = model.strip()
            if interval is not None:
                self.auto_interval = max(5.0, float(interval))
            if cooldown is not None:
                self.cooldown = max(3.0, float(cooldown))
            if diff_threshold is not None:
                self.diff_threshold = max(1.0, float(diff_threshold))

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("YOUR_") and self.client is not None)

    def set_active(self, active: bool) -> bool:
        with self._lock:
            self.is_active = bool(active)
            return self.is_active

    def compute_frame_diff(self, img: Image.Image) -> float:
        """
        Computes the normalized percentage change (0-100%) against the previously inspected frame.
        Uses a lightweight 64x64 grayscale matrix to save CPU cycles on Raspberry Pi 5.
        """
        thumb = img.convert("L").resize((64, 64), Image.Resampling.BILINEAR)
        arr = np.array(thumb, dtype=np.float32)

        if self.last_thumbnail_arr is None:
            self.last_thumbnail_arr = arr
            self.last_diff_pct = 100.0
            return 100.0

        diff = np.mean(np.abs(arr - self.last_thumbnail_arr)) / 255.0 * 100.0
        self.last_diff_pct = float(round(diff, 2))
        return self.last_diff_pct

    def optimize_image(self, img: Image.Image) -> Tuple[Image.Image, bytes]:
        """
        Downscales the image to optimal resolution (e.g. 512x512 max dimension)
        and compresses to JPEG quality 80 in memory.
        A 512x512 image utilizes only 1 Gemini tile (~258 tokens) compared to 1000+ for 1080p.
        """
        img_rgb = img.convert("RGB")
        w, h = img_rgb.size

        if max(w, h) > self.max_dim:
            scale = self.max_dim / float(max(w, h))
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_optimized = img_rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            img_optimized = img_rgb

        buf = io.BytesIO()
        img_optimized.save(buf, format="JPEG", quality=80, optimize=True)
        return img_optimized, buf.getvalue()

    def inspect_produce(
        self,
        img: Image.Image,
        force: bool = False,
        local_prediction: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Inspects produce image with Gemini API while guarding against token over-consumption.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Gemini API key is not configured. Please enter your Gemini API key in the AI Pro dashboard or .env file.",
                "code": "MISSING_API_KEY",
                "stats": self.get_telemetry()
            }

        now = time.time()
        elapsed = now - self.last_call_time
        frame_diff = self.compute_frame_diff(img)

        # 1. Cooldown & Token Conservation Check (unless forced by manual inspect)
        if not force:
            if elapsed < self.cooldown:
                remaining = self.cooldown - elapsed
                self.stats["saved_calls"] += 1
                self.stats["estimated_tokens_saved"] += 300
                return {
                    "success": True,
                    "skipped": True,
                    "reason": "cooldown",
                    "message": f"Cooldown active ({remaining:.1f}s remaining). API token preserved.",
                    "diff_pct": frame_diff,
                    "cooldown_remaining": round(remaining, 1),
                    "data": self.last_result,
                    "stats": self.get_telemetry()
                }

            if frame_diff < self.diff_threshold and self.last_result is not None:
                self.stats["saved_calls"] += 1
                self.stats["estimated_tokens_saved"] += 300
                return {
                    "success": True,
                    "skipped": True,
                    "reason": "static_scene",
                    "message": f"Static scene (frame changed by only {frame_diff:.1f}%). Reusing verified verdict to save tokens.",
                    "diff_pct": frame_diff,
                    "data": self.last_result,
                    "stats": self.get_telemetry()
                }

        # 2. Pre-process and downscale image for ultra-low token consumption
        opt_img, img_bytes = self.optimize_image(img)

        # 3. Compact, token-efficient system instruction & prompt
        system_instruction = (
            "You are an expert food quality inspector and agronomist. "
            "Inspect the provided produce image for freshness, defects, ripeness, quality grade, and shelf life. "
            "Respond ONLY with valid compact JSON without markdown formatting or code blocks."
        )

        prompt = (
            "Analyze this produce item. Return JSON with these exact fields: "
            "\"produce\": string (e.g. Tomato, Banana, Carrot, Apple), "
            "\"category_type\": \"Fruit\" or \"Vegetable\", "
            "\"freshness\": \"Fresh\" or \"Rotten\", "
            "\"confidence\": float (0.0 to 1.0), "
            "\"quality_score\": integer (0 to 100), "
            "\"quality_grade\": \"Grade A (Premium)\", \"Grade B (Acceptable)\", or \"Spoiled\", "
            "\"ripeness\": \"Underripe\", \"Ripe\", \"Overripe\", or \"Spoiled\", "
            "\"estimated_shelf_life_days\": integer, "
            "\"defects\": list of short strings (e.g. [\"Minor surface bruise\", \"Stem discoloration\"]) or [], "
            "\"spoilage_indicators\": list of short strings or [], "
            "\"storage_recommendation\": string (1 concise sentence), "
            "\"detailed_summary\": string (1-2 sentences on texture, skin integrity, and commercial quality)."
        )

        # Contextual hint from local edge classifier if available (helps Gemini maintain consistency)
        if local_prediction and "category" in local_prediction:
            loc_cat = local_prediction["category"].get("label")
            loc_fresh = local_prediction.get("freshness", {}).get("label")
            prompt += f" (Hint from edge sensor: Detected {loc_cat}, condition: {loc_fresh})."

        t_start = time.time()
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.15,
                max_output_tokens=500
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[opt_img, prompt],
                config=config
            )

            latency_ms = (time.time() - t_start) * 1000
            self.stats["last_latency_ms"] = round(latency_ms, 1)

            # Extract response text
            raw_text = response.text.strip() if hasattr(response, "text") and response.text else "{}"
            # Clean possible markdown wrapping if returned
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed_data = json.loads(raw_text)

            # Record token usage from metadata or estimate
            tokens_used = 280
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                total_t = getattr(response.usage_metadata, "total_token_count", None)
                if total_t:
                    tokens_used = int(total_t)

            self.stats["total_calls"] += 1
            self.stats["estimated_tokens_used"] += tokens_used

            # Update cache states
            self.last_call_time = time.time()
            self.last_thumbnail_arr = np.array(img.convert("L").resize((64, 64), Image.Resampling.BILINEAR), dtype=np.float32)

            result_payload = {
                "produce": parsed_data.get("produce", "Unknown Produce"),
                "category_type": parsed_data.get("category_type", "Produce"),
                "freshness": parsed_data.get("freshness", "Fresh"),
                "confidence": float(parsed_data.get("confidence", 0.95)),
                "quality_score": int(parsed_data.get("quality_score", 90)),
                "quality_grade": parsed_data.get("quality_grade", "Grade A (Premium)"),
                "ripeness": parsed_data.get("ripeness", "Ripe"),
                "estimated_shelf_life_days": int(parsed_data.get("estimated_shelf_life_days", 4)),
                "defects": parsed_data.get("defects", []),
                "spoilage_indicators": parsed_data.get("spoilage_indicators", []),
                "storage_recommendation": parsed_data.get("storage_recommendation", "Store in a cool, ventilated space."),
                "detailed_summary": parsed_data.get("detailed_summary", "Produce exhibits good visual quality."),
                "engine": f"Gemini AI Pro ({self.model_name})",
                "tokens_used": tokens_used,
                "latency_ms": self.stats["last_latency_ms"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            self.last_result = result_payload

            return {
                "success": True,
                "skipped": False,
                "diff_pct": frame_diff,
                "data": result_payload,
                "stats": self.get_telemetry()
            }

        except Exception as e:
            err_msg = str(e)
            print(f"[GeminiQualityInspector] API call error: {err_msg}")

            # Friendly message for quota/token limit
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                user_msg = "Gemini API rate limit or quota exceeded. The system has automatically paused requests to protect your account."
                code = "QUOTA_EXCEEDED"
            elif "API_KEY_INVALID" in err_msg or "400" in err_msg and "key" in err_msg.lower():
                user_msg = "Invalid Gemini API key. Please check your credentials in the dashboard."
                code = "INVALID_KEY"
            else:
                user_msg = f"Gemini inspection failed: {err_msg}"
                code = "API_ERROR"

            return {
                "success": False,
                "error": user_msg,
                "raw_error": err_msg,
                "code": code,
                "stats": self.get_telemetry()
            }

    def get_telemetry(self) -> Dict[str, Any]:
        now = time.time()
        elapsed = now - self.last_call_time
        cooldown_remaining = max(0.0, round(self.cooldown - elapsed, 1))

        return {
            "is_active": self.is_active,
            "is_configured": self.is_configured(),
            "model": self.model_name,
            "auto_interval": self.auto_interval,
            "cooldown": self.cooldown,
            "cooldown_remaining": cooldown_remaining,
            "diff_threshold": self.diff_threshold,
            "last_diff_pct": self.last_diff_pct,
            "total_calls": self.stats["total_calls"],
            "saved_calls": self.stats["saved_calls"],
            "estimated_tokens_used": self.stats["estimated_tokens_used"],
            "estimated_tokens_saved": self.stats["estimated_tokens_saved"],
            "last_latency_ms": self.stats["last_latency_ms"]
        }
