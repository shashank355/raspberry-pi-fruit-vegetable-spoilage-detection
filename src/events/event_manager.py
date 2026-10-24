import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from PIL import Image

from src.config import Config
from src.database.db import Database
from src.mqtt.mqtt_manager import MQTTManager
from src.notifications.telegram_worker import TelegramWorker


class EventManager:
    """
    Core AI Decision Engine & Event Manager for FreshScan AI 2.0.
    Implements:
      - Confidence validation
      - Spoilage detection logic
      - Duplicate notification prevention
      - State persistence & multi-alert lifecycle
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EventManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.db = Database()
        self.mqtt = MQTTManager()
        self.telegram = TelegramWorker(db=self.db)

        # Wire MQTT callbacks from ESP32 buttons
        self.mqtt.register_ack_callback(self.acknowledge_alert)
        self.mqtt.register_clear_callback(self.clear_alert)

        # Ensure captured_images directory exists
        Path(Config.CAPTURED_IMAGES_DIR).mkdir(parents=True, exist_ok=True)

    def process_inspection(self, raw_result: Dict[str, Any], annotated_img: Optional[Image.Image] = None) -> Dict[str, Any]:
        """
        Processes a raw AI prediction through the Decision Engine.
        """
        cat_data = raw_result.get("category", {})
        fresh_data = raw_result.get("freshness", {})

        produce = cat_data.get("label", "Unknown")
        cat_score = float(cat_data.get("score", 0.0))
        fresh_label = fresh_data.get("label", "Unknown")
        fresh_score = float(fresh_data.get("score", 0.0))

        # Check confidence threshold
        is_confident = fresh_score >= Config.CONFIDENCE_THRESHOLD
        is_spoiled = fresh_label.lower() in ("rotten", "spoiled")

        if not is_confident:
            condition = "Uncertain"
        elif is_spoiled:
            condition = "Spoiled"
        else:
            condition = "Fresh"

        response = {
            "produce": produce,
            "condition": condition,
            "category_confidence": cat_score,
            "freshness_confidence": fresh_score,
            "threshold": Config.CONFIDENCE_THRESHOLD,
            "is_spoiled": is_spoiled,
            "is_confident": is_confident,
            "alert_created": False,
            "event_id": None
        }

        # If not spoiled or uncertain, no spoilage alert is generated
        if not is_spoiled:
            return response

        # ==========================================
        # Duplicate Notification Prevention
        # ==========================================
        active_alert = self.db.get_active_alert_by_produce(produce)
        if active_alert:
            print(f"[EventManager] Produce '{produce}' already has an unresolved alert ({active_alert['event_id']}, Status: {active_alert['status']}). Preventing duplicate notification.")
            response["alert_created"] = False
            response["event_id"] = active_alert["event_id"]
            response["message"] = f"Unresolved alert already active for {produce}."
            return response

        # ==========================================
        # Create New Spoilage Alert Event
        # ==========================================
        event_id = self.db.get_next_event_id()
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_filename = f"{event_id}_{produce}_{timestamp_str}.jpg"
        img_save_path = os.path.join(Config.CAPTURED_IMAGES_DIR, img_filename)

        if annotated_img:
            annotated_img.save(img_save_path, quality=92)
        elif "pil_img" in raw_result:
            raw_result["pil_img"].save(img_save_path, quality=92)

        # 1. Save to Database
        event_record = self.db.create_event(
            event_id=event_id,
            produce=produce,
            condition=condition,
            freshness_score=fresh_score,
            category_score=cat_score,
            image_path=img_save_path,
            status="NEW"
        )

        # 2. Publish wirelessly to ESP32 alert panel via MQTT
        self.mqtt.publish_spoilage_event(event_record)
        self.mqtt.sync_active_alerts(self.db.get_active_alerts())

        # 3. Asynchronously enqueue Telegram notification (does not block physical alert)
        self.telegram.enqueue_spoilage_alert(event_record)

        response["alert_created"] = True
        response["event_id"] = event_id
        response["event_record"] = event_record
        response["led_index"] = Config.PRODUCE_LED_MAP.get(produce, 1)

        print(f"[EventManager] New Spoilage Alert created: {event_id} ({produce}) -> ESP32 notified, Telegram queued.")
        return response

    def acknowledge_alert(self, item_or_id: str) -> bool:
        """
        Acknowledges an active alert (triggered by ESP32 button 1 or Web UI).
        Changes LED from blinking to steady ON.
        """
        print(f"[EventManager] Acknowledging alert for '{item_or_id}'...")
        success = self.db.acknowledge_alert(item_or_id)
        if success:
            self.mqtt.sync_active_alerts(self.db.get_active_alerts())
        return success

    def clear_alert(self, item_or_id: str) -> bool:
        """
        Clears an alert (triggered by ESP32 button 2 or Web UI) after inspection/removal.
        Turns off LED and removes from LCD rotation.
        """
        print(f"[EventManager] Clearing alert for '{item_or_id}'...")
        success = self.db.clear_alert(item_or_id)
        if success:
            self.mqtt.sync_active_alerts(self.db.get_active_alerts())
        return success

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return self.db.get_active_alerts()

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.db.get_event_history(limit)
