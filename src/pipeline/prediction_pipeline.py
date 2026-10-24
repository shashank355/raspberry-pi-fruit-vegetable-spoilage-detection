import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import json

from src.config import Config

# TFLite Runtime resolution: prefers lightweight tflite-runtime / litert, falls back to tf.lite
Interpreter = None
TFLITE_AVAILABLE = False
try:
    from tflite_runtime.interpreter import Interpreter
    TFLITE_AVAILABLE = True
except ImportError:
    try:
        from ai_edge_litert.interpreter import Interpreter
        TFLITE_AVAILABLE = True
    except ImportError:
        try:
            import tensorflow as tf
            Interpreter = tf.lite.Interpreter
            TFLITE_AVAILABLE = True
        except ImportError:
            TFLITE_AVAILABLE = False

CATEGORY_LABELS_PATH = Path(Config.MODEL_DIR) / "category_labels.json"
with open(CATEGORY_LABELS_PATH, "r") as f:
    CATEGORY_LABELS = json.load(f)

FRESHNESS_LABELS = ["Fresh", "Rotten"]

CATEGORY_IMG_SIZE = (224, 224)
FRESHNESS_IMG_SIZE = (224, 224)


class PredictionPipeline:
    def __init__(self, force_engine: str = None):
        """
        Initializes the inference pipeline.
        force_engine: 'tflite' or 'keras'. If None, auto-selects TFLite if available, else Keras.
        """
        self.category_labels = CATEGORY_LABELS
        self.freshness_labels = FRESHNESS_LABELS

        cat_tflite_path = Path(Config.TFLITE_CATEGORY_MODEL)
        fresh_tflite_path = Path(Config.TFLITE_FRESHNESS_MODEL)
        cat_keras_path = Path(Config.KERAS_CATEGORY_MODEL)
        fresh_keras_path = Path(Config.KERAS_FRESHNESS_MODEL)

        use_tflite = (
            force_engine == "tflite"
            or (
                force_engine is None
                and TFLITE_AVAILABLE
                and cat_tflite_path.exists()
                and fresh_tflite_path.exists()
            )
        )

        if use_tflite and TFLITE_AVAILABLE and cat_tflite_path.exists() and fresh_tflite_path.exists():
            print(f"[PredictionPipeline] Initializing TensorFlow Lite engine (optimized for Raspberry Pi)...")
            self.engine = "tflite"
            self.category_interpreter = Interpreter(model_path=str(cat_tflite_path))
            self.category_interpreter.allocate_tensors()
            self.cat_in_idx = self.category_interpreter.get_input_details()[0]["index"]
            self.cat_out_idx = self.category_interpreter.get_output_details()[0]["index"]

            self.freshness_interpreter = Interpreter(model_path=str(fresh_tflite_path))
            self.freshness_interpreter.allocate_tensors()
            self.fresh_in_idx = self.freshness_interpreter.get_input_details()[0]["index"]
            self.fresh_out_idx = self.freshness_interpreter.get_output_details()[0]["index"]
        else:
            print("[PredictionPipeline] Initializing Full Keras engine...")
            self.engine = "keras"
            import tensorflow as tf
            self.category_model = tf.keras.models.load_model(cat_keras_path)
            self.freshness_model = tf.keras.models.load_model(fresh_keras_path)

        print(f"[PredictionPipeline] Ready using {self.engine.upper()} backend.")

    def _preprocess_image(self, img, target_size, normalize=True):
        if isinstance(img, (str, Path)):
            img_path = Path(img)
            if not img_path.exists():
                raise FileNotFoundError(f"Image not found: {img_path.resolve()}")
            img = Image.open(str(img_path)).convert("RGB")
        elif isinstance(img, np.ndarray):
            if img.ndim == 3 and img.shape[2] in (3, 4):
                img = Image.fromarray(img).convert("RGB")
            else:
                raise ValueError("NumPy input must be shape (H, W, 3) or (H, W, 4)")
        elif isinstance(img, Image.Image):
            img = img.convert("RGB")
        img_resized = img.resize(target_size)
        img_array = np.array(img_resized).astype("float32")
        if normalize:
            img_array = img_array / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        return img_array, img

    def _infer_category(self, img_array):
        if self.engine == "tflite":
            self.category_interpreter.set_tensor(self.cat_in_idx, img_array)
            self.category_interpreter.invoke()
            return self.category_interpreter.get_tensor(self.cat_out_idx)
        else:
            return self.category_model.predict(img_array, verbose=0)

    def _infer_freshness(self, img_array):
        if self.engine == "tflite":
            self.freshness_interpreter.set_tensor(self.fresh_in_idx, img_array)
            self.freshness_interpreter.invoke()
            return self.freshness_interpreter.get_tensor(self.fresh_out_idx)
        else:
            return self.freshness_model.predict(img_array, verbose=0)

    def predict(self, img):
        cat_img_array, pil_img = self._preprocess_image(img, CATEGORY_IMG_SIZE, normalize=True)
        cat_pred = self._infer_category(cat_img_array)
        cat_idx = int(np.argmax(cat_pred))
        cat_label = self.category_labels[cat_idx]
        cat_score = float(np.max(cat_pred))

        fresh_img_array, _ = self._preprocess_image(img, FRESHNESS_IMG_SIZE, normalize=True)
        fresh_pred = self._infer_freshness(fresh_img_array)
        fresh_idx = int(np.argmax(fresh_pred))
        fresh_label = self.freshness_labels[fresh_idx]
        fresh_score = float(np.max(fresh_pred))

        return {
            "category": {"label": cat_label, "idx": cat_idx, "score": cat_score},
            "freshness": {"label": fresh_label, "idx": fresh_idx, "score": fresh_score},
            "pil_img": pil_img,
            "engine": self.engine
        }

    def annotate(self, img, result, font_size=None):
        pil_img = result["pil_img"].copy()
        draw = ImageDraw.Draw(pil_img)

        cat_pct = result["category"]["score"] * 100
        fresh_pct = result["freshness"]["score"] * 100
        text = f"{result['category']['label']} ({cat_pct:.1f}%)  •  {result['freshness']['label']} ({fresh_pct:.1f}%)"

        if font_size is None:
            font_size = max(22, min(48, int(pil_img.width / 24)))

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

        banner_h = font_size + 18
        is_fresh = result["freshness"]["label"].lower() == "fresh"
        bar_color = (16, 185, 129) if is_fresh else (239, 68, 68)

        # Draw translucent dark background banner
        draw.rectangle([0, 0, pil_img.width, banner_h], fill=(15, 23, 42, 220))
        # Draw colored accent bar at top
        draw.rectangle([0, 0, pil_img.width, 4], fill=bar_color)
        # Draw text
        draw.text((16, 8), text, fill=(255, 255, 255), font=font)
        return pil_img


if __name__ == "__main__":
    pipeline = PredictionPipeline()
    sample_path = Path(Config.PROJECT_ROOT) / "test_sample.jpg"
    if sample_path.exists():
        res = pipeline.predict(sample_path)
        print("Prediction result:", res["category"], "|", res["freshness"], f"(Backend: {res['engine']})")
