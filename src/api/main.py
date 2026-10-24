import io
import os
import base64
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image
import numpy as np

from src.pipeline.prediction_pipeline import PredictionPipeline
from src.camera import PiCameraManager
from src.events.event_manager import EventManager
from src.config import Config

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="FreshScan AI 2.0 — Edge AI Spoilage Detection & ESP32 Alert System",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = PredictionPipeline()
camera_manager = PiCameraManager()
event_manager = EventManager()

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


def read_imagefile(file) -> np.ndarray:
    img = Image.open(file).convert("RGB")
    return np.array(img)


def _format_prediction_response(img_array: np.ndarray, result: dict):
    annotated_img = pipeline.annotate(img_array, result)

    # Process through FreshScan AI 2.0 Decision Engine (SQLite + MQTT to ESP32 + Telegram)
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


@app.post("/predict/image")
async def predict_image(image: UploadFile = File(...)):
    try:
        img_array = read_imagefile(image.file)
        result = pipeline.predict(img_array)
        return _format_prediction_response(img_array, result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/camera/capture")
async def capture_from_pi_camera():
    """Snaps an image from the physical Raspberry Pi Camera Rev 1.3 and analyzes freshness."""
    try:
        rgb_arr, pil_img = camera_manager.capture_frame()
        result = pipeline.predict(rgb_arr)
        return _format_prediction_response(rgb_arr, result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pi Camera capture error: {str(e)}")


@app.get("/api/camera/status")
async def get_camera_status():
    """Returns status of the attached Raspberry Pi Camera (Rev 1.3)."""
    return camera_manager.get_status()


@app.get("/api/camera/stream")
def stream_pi_camera():
    """Live MJPEG video stream from the Raspberry Pi Camera."""
    return StreamingResponse(
        camera_manager.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ==========================================
# FreshScan AI 2.0 Alert Management Endpoints
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
    """Comprehensive health check of Pi 4B, Camera, AI engine, MQTT, and ESP32 panel."""
    mqtt_status = event_manager.mqtt.get_status()
    cam_status = camera_manager.get_status()
    return {
        "system": "FreshScan AI 2.0",
        "engine": pipeline.engine,
        "camera": cam_status,
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
        "categories": pipeline.category_labels,
        "freshness_states": pipeline.freshness_labels,
        "produce_info": PRODUCE_METADATA,
        "produce_led_map": Config.PRODUCE_LED_MAP,
        "engine": pipeline.engine
    }


# Mount static files for the HTML/CSS/JS frontend
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
