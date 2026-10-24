import os
import time
import queue
import threading
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from src.config import Config


class TelegramWorker:
    """
    Asynchronous, non-blocking background notification worker for Telegram alerts.
    Dispatches spoilage warnings and high-resolution annotated photographs to the user.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TelegramWorker, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db=None):
        if self._initialized:
            return
        self._initialized = True

        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.enabled = Config.TELEGRAM_ENABLED and bool(self.bot_token and self.chat_id)
        self.db = db

        self._queue: queue.Queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

        if self.enabled:
            print("[TelegramWorker] Telegram notifications enabled and background queue active.")
        else:
            print("[TelegramWorker] Telegram credentials not set. Notifications in standby mode.")

    def enqueue_spoilage_alert(self, event_data: Dict[str, Any]):
        """
        Non-blocking enqueue of spoilage event. Physical alerts continue immediately.
        """
        self._queue.put(event_data)

    def _process_queue(self):
        while True:
            event = self._queue.get()
            try:
                self._send_alert_with_retry(event)
            except Exception as e:
                print(f"[TelegramWorker] Error processing telegram queue item: {e}")
            finally:
                self._queue.task_done()

    def _send_alert_with_retry(self, event: Dict[str, Any], max_retries: int = 3):
        if not self.enabled and not (Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID):
            print(f"[TelegramWorker] Notice: Telegram credentials missing, skipping alert for {event.get('event_id')}.")
            return

        token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_CHAT_ID
        event_id = event.get("event_id", "UNKNOWN")
        produce = event.get("produce", "Item")
        confidence = float(event.get("freshness_score", 0.0)) * 100
        timestamp = event.get("created_at", "")
        img_path = event.get("image_path")

        caption = (
            f"🚨 <b>FRESHSCAN AI 2.0 — SPOILAGE ALERT</b>\n\n"
            f"🥬 <b>Item:</b> {produce}\n"
            f"⚠️ <b>Status:</b> Potentially Spoiled\n"
            f"📊 <b>AI Confidence:</b> {confidence:.1f}%\n"
            f"🆔 <b>Event ID:</b> {event_id}\n"
            f"⏰ <b>Time:</b> {timestamp}\n\n"
            f"📷 <i>Photograph attached above. Please inspect the vegetable and confirm its condition.</i>"
        )

        success = False
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                # Check if image file exists
                if img_path and Path(img_path).exists():
                    url = f"https://api.telegram.org/bot{token}/sendPhoto"
                    with open(img_path, "rb") as f:
                        files = {"photo": f}
                        data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
                        resp = requests.post(url, data=data, files=files, timeout=12)
                else:
                    # Fallback to plain text message
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    data = {"chat_id": chat_id, "text": caption, "parse_mode": "HTML"}
                    resp = requests.post(url, data=data, timeout=10)

                if resp.status_code == 200:
                    print(f"[TelegramWorker] Successfully dispatched Telegram alert for {event_id} ({produce}).")
                    success = True
                    break
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text}"
                    print(f"[TelegramWorker] Attempt {attempt} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                print(f"[TelegramWorker] Network error on attempt {attempt}: {e}")

            time.sleep(2 ** attempt)

        # Update database status if DB reference is provided
        if self.db:
            try:
                self.db.update_telegram_status(event_id, sent=success, error=last_error if not success else None)
            except Exception as e:
                print(f"[TelegramWorker] Could not update DB telegram status: {e}")

    def test_connection(self) -> Dict[str, Any]:
        """
        Validates bot token and chat ID by sending a ping message.
        """
        token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_CHAT_ID

        if not token or not chat_id:
            return {"success": False, "error": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured."}

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            msg = "🍓 <b>FreshScan AI 2.0</b>: Telegram Bot communication link verified successfully!"
            resp = requests.post(url, data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)
            if resp.status_code == 200:
                return {"success": True, "message": "Telegram ping message delivered successfully!"}
            else:
                return {"success": False, "error": f"Telegram API returned {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
