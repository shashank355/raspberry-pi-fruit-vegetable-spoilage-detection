import io
import os
import base64
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image
import numpy as np

from src.pipeline.prediction_pipeline import PredictionPipeline
from src.pipeline.gemini_service import GeminiQualityInspector
from src.camera import USBCameraManager
from src.events.event_manager import EventManager
from src.config import Config

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="FreshScan AI 2.0 — Edge AI Spoilage Detection & Gemini AI Pro (RPi 5)",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = PredictionPipeline()
camera_manager = USBCameraManager()
event_manager = EventManager()
gemini_inspector = GeminiQualityInspector()

PRODUCE_METADATA = {
    "Apple": {"emoji": "🍎", "type": "Fruit", "tip": "Store in refrigerator crisper drawer for 4–6 weeks."},
    "Banana": {"emoji": "🍌", "type": "Fruit", "tip": "Keep at room temperature away from direct sunlight; wrap stems in foil."},
    "Bellpepper": {"emoji": "🫑", "type": "Vegetable", "tip": "Keep completely dry in the crisper drawer; use within 1–2 weeks."},
    "Carrot": {"emoji": "🥕", "type": "Vegetable", "tip": "Trim leafy tops and keep sealed in a perforated bag in the fridge."},
    "Cucumber": {"emoji": "🥒", "type": "Vegetable", "tip": "Store on upper refrigerator shelves to protect from chill damage."},
    "Mango": {"emoji": "🥭", "type": "Fruit", "tip": "Ripen at room temperature, then refrigerate up to 5 days once soft."},
    "Orange": {"emoji": "🍊", "type": "Fruit", "tip": "Keeps at room temp for 1 week, or in fridge for 3–4 weeks."},
    "Potato": {"emoji": "🥔", "type": "Vegetable", "tip": "Store in a cool, dark, dry area; keep separated from onions and apples."},
    "Strawberry": {"emoji": "🍓", "type": "Fruit", "tip": "Keep unwashed in a paper-towel lined container in the fridge."},
    "Tomato": {"emoji": "🍅", "type": "Vegetable", "tip": "Store stem-side down at room temp; refrigeration diminishes sweetness."},
}


def read_imagefile(file) -> Tuple[np.ndarray, Image.Image]:
    img = Image.open(file).convert("RGB")
    return np.array(img), img


def _format_prediction_response(img_array: np.ndarray, result: dict):
    annotated_img = pipeline.annotate(img_array, result)

    # Process through FreshScan AI Decision Engine (SQLite + MQTT to ESP32 + Telegram)
    decision = event_manager.process_inspection(result, annotated_img=annotated_img)

    out_path = "annotated_result.jpg"
    annotated_img.save(out_path)

    buffered = io.BytesIO()
    annotated_img.save(buffered, format="JPEG", quality=92)
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    cat_label = result["category"]["label"]
    meta = PRODUCE_METADATA.get(cat_label, {"emoji": "🥬", "type": "Produce", "tip": "Store in a cool, dry place."})

    return {
        "category": result["category"],
        "freshness": result["freshness"],
        "metadata": meta,
        "engine": result.get("engine", "tflite"),
        "decision": decision,
        "annotated_filepath": out_path,
        "annotated_image_base64": f"data:image/jpeg;base64,{img_b64}"
    }


# ==========================================
# Local Edge Inference Endpoints
# ==========================================
@app.post("/predict/image")
async def predict_image(image: UploadFile = File(...)):
    try:
        img_array, pil_img = read_imagefile(image.file)
        result = pipeline.predict(img_array)
        return _format_prediction_response(img_array, result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/camera/capture")
async def capture_from_usb_camera():
    """Snaps an image from the external USB camera and analyzes freshness with edge models."""
    try:
        rgb_arr, pil_img = camera_manager.capture_frame()
        result = pipeline.predict(rgb_arr)
        return _format_prediction_response(rgb_arr, result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"USB Camera capture error: {str(e)}")


@app.get("/api/camera/status")
async def get_camera_status():
    """Returns status of the external USB camera on Raspberry Pi 5."""
    return camera_manager.get_status()


@app.get("/api/camera/devices")
async def get_camera_devices():
    """Discovers and returns all video devices attached to the Raspberry Pi 5."""
    devices = camera_manager.list_available_cameras()
    return {
        "devices": devices,
        "current_index": camera_manager.device_index,
        "current_device": camera_manager.device_name
    }


@app.post("/api/camera/select")
async def select_camera_device(index: Any = Body(..., embed=True)):
    """Selects and switches to a specific camera index (e.g. 2 for USB camera or 'auto')."""
    success = camera_manager.switch_camera(index)
    return {
        "success": success,
        "camera_status": camera_manager.get_status()
    }


@app.get("/api/camera/stream")
def stream_usb_camera():
    """Live MJPEG video stream from the external USB camera on Raspberry Pi 5."""
    return StreamingResponse(
        camera_manager.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ==========================================
# Gemini AI Pro Endpoints (Token-Optimized)
# ==========================================
@app.get("/api/ai-pro/status")
async def get_ai_pro_status():
    """Returns AI Pro toggle state, token usage statistics, and cooldown status."""
    return gemini_inspector.get_telemetry()


@app.post("/api/ai-pro/toggle")
async def toggle_ai_pro(active: bool = Body(..., embed=True)):
    """Enables or disables continuous AI Pro auto-inspection mode."""
    new_state = gemini_inspector.set_active(active)
    return {
        "is_active": new_state,
        "message": "AI Pro auto-inspection enabled" if new_state else "AI Pro auto-inspection paused",
        "telemetry": gemini_inspector.get_telemetry()
    }


@app.post("/api/ai-pro/configure")
async def configure_ai_pro(
    api_key: Optional[str] = Body(None),
    model: Optional[str] = Body(None),
    interval: Optional[float] = Body(None),
    cooldown: Optional[float] = Body(None),
    diff_threshold: Optional[float] = Body(None)
):
    """Dynamically updates Gemini AI Pro configuration and API credentials."""
    gemini_inspector.update_config(
        api_key=api_key,
        model=model,
        interval=interval,
        cooldown=cooldown,
        diff_threshold=diff_threshold
    )
    return {
        "success": True,
        "configured": gemini_inspector.is_configured(),
        "telemetry": gemini_inspector.get_telemetry()
    }


@app.post("/api/ai-pro/inspect")
async def inspect_with_ai_pro(
    source: str = Query("camera", description="'camera' to snap USB camera or 'upload' for uploaded file"),
    force: bool = Query(False, description="Bypass motion/diff token saver and force Gemini call"),
    image: Optional[UploadFile] = File(None)
):
    """
    Performs deep multimodal quality inspection via Gemini API with token protection.
    If source='camera', grabs live frame from external USB camera.
    """
    try:
        if source == "upload" and image is not None:
            rgb_arr, pil_img = read_imagefile(image.file)
        else:
            rgb_arr, pil_img = camera_manager.capture_frame()

        # Run local pre-check for hint and alert integration
        try:
            local_res = pipeline.predict(rgb_arr)
        except Exception:
            local_res = None

        inspection = gemini_inspector.inspect_produce(pil_img, force=force, local_prediction=local_res)

        # If Gemini identified spoilage and an actual call was made, trigger alert pipeline
        if inspection.get("success") and not inspection.get("skipped") and inspection.get("data"):
            data = inspection["data"]
            fresh_label = data.get("freshness", "Fresh")
            is_spoiled = fresh_label.lower() in ("rotten", "spoiled") or data.get("quality_grade") == "Spoiled"

            if is_spoiled:
                produce_name = data.get("produce", "Unknown")
                alert_res = {
                    "category": {"label": produce_name, "idx": 0, "score": float(data.get("confidence", 0.9))},
                    "freshness": {"label": "Rotten", "idx": 1, "score": float(data.get("confidence", 0.9))},
                    "pil_img": pil_img,
                    "engine": data.get("engine", "Gemini AI Pro")
                }
                event_manager.process_inspection(alert_res, annotated_img=pil_img)

        return inspection

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Pro Inspection error: {str(e)}")


# ==========================================
# FreshScan AI Alert Management Endpoints
# ==========================================
@app.get("/api/alerts/active")
async def get_active_alerts():
    """Returns all current unresolved spoilage alerts syncing with ESP32."""
    return event_manager.get_active_alerts()


@app.post("/api/alerts/{item_or_id}/acknowledge")
async def acknowledge_alert(item_or_id: str):
    """Acknowledges an alert from Web UI, updating LCD and setting ESP32 LED to steady ON."""
    success = event_manager.acknowledge_alert(item_or_id)
    return {"success": success, "target": item_or_id, "action": "ACKNOWLEDGED"}


@app.post("/api/alerts/{item_or_id}/clear")
async def clear_alert(item_or_id: str):
    """Clears an alert from Web UI, turning off the ESP32 LED and removing from LCD rotation."""
    success = event_manager.clear_alert(item_or_id)
    return {"success": success, "target": item_or_id, "action": "CLEARED"}


@app.get("/api/events/history")
async def get_event_history(limit: int = 50):
    """Returns persistent event history from SQLite."""
    return event_manager.get_history(limit=limit)


@app.get("/api/system/status")
async def get_system_status():
    """Comprehensive health check of Raspberry Pi 5, USB Camera, AI Pro, MQTT, and ESP32 panel."""
    mqtt_status = event_manager.mqtt.get_status()
    cam_status = camera_manager.get_status()
    ai_pro_status = gemini_inspector.get_telemetry()
    return {
        "system": "FreshScan AI 2.0",
        "platform": Config.PLATFORM_NAME,
        "engine": pipeline.engine,
        "camera": cam_status,
        "ai_pro": ai_pro_status,
        "mqtt": mqtt_status,
        "telegram_enabled": Config.TELEGRAM_ENABLED and bool(Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID),
        "active_alerts_count": len(event_manager.get_active_alerts())
    }


@app.post("/api/test/spoilage-alert")
async def test_spoilage_alert(vegetable: str = Body(..., embed=True)):
    """Simulates a spoilage event to test ESP32 LCD/LED panel and Telegram without camera inspection."""
    if vegetable not in Config.PRODUCE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid vegetable. Must be one of: {Config.PRODUCE_CATEGORIES}")

    mock_result = {
        "category": {"label": vegetable, "idx": Config.PRODUCE_CATEGORIES.index(vegetable), "score": 0.98},
        "freshness": {"label": "Rotten", "idx": 1, "score": 0.95},
        "pil_img": Image.new("RGB", (224, 224), color=(180, 50, 50)),
        "engine": pipeline.engine
    }
    decision = event_manager.process_inspection(mock_result)
    return {"message": f"Test spoilage alert triggered for {vegetable}", "decision": decision}


@app.post("/api/test/telegram")
async def test_telegram():
    """Sends a test ping to Telegram to verify credentials."""
    return event_manager.telegram.test_connection()


@app.get("/api/metadata")
async def get_metadata():
    return {
        "platform": Config.PLATFORM_NAME,
        "categories": pipeline.category_labels,
        "freshness_states": pipeline.freshness_labels,
        "produce_info": PRODUCE_METADATA,
        "produce_led_map": Config.PRODUCE_LED_MAP,
        "engine": pipeline.engine,
        "ai_pro": gemini_inspector.get_telemetry()
    }


# Mount static files for the HTML/CSS/JS frontend
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
