import json
import time
import threading
from typing import Callable, Optional, Dict, Any, List
import paho.mqtt.client as mqtt

from src.config import Config


class MQTTManager:
    """
    Handles wireless MQTT communication between Raspberry Pi 4B and ESP32 physical alert panel.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MQTTManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.host = Config.MQTT_BROKER_HOST
        self.port = Config.MQTT_BROKER_PORT
        self.client_id = Config.MQTT_CLIENT_ID
        self.is_connected = False
        self.last_controller_status = {"online": False, "last_seen": None, "ip": None}

        self._on_ack_callbacks: List[Callable[[str], None]] = []
        self._on_clear_callbacks: List[Callable[[str], None]] = []

        # Setup MQTT Client (v2 compatibility)
        try:
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id
            )
        except AttributeError:
            self.client = mqtt.Client(client_id=self.client_id)

        if Config.MQTT_USERNAME and Config.MQTT_PASSWORD:
            self.client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        if Config.MQTT_ENABLED:
            self.start()

    def register_ack_callback(self, cb: Callable[[str], None]):
        self._on_ack_callbacks.append(cb)

    def register_clear_callback(self, cb: Callable[[str], None]):
        self._on_clear_callbacks.append(cb)

    def start(self):
        def _connect_thread():
            try:
                print(f"[MQTTManager] Connecting to MQTT broker at {self.host}:{self.port}...")
                self.client.connect_async(self.host, self.port, keepalive=60)
                self.client.loop_start()
            except Exception as e:
                print(f"[MQTTManager] Warning: Could not connect to MQTT broker ({e}). Will retry in background.")

        t = threading.Thread(target=_connect_thread, daemon=True)
        t.start()

    def stop(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        rc_code = rc if isinstance(rc, int) else getattr(rc, "value", rc)
        if rc_code == 0:
            self.is_connected = True
            print(f"[MQTTManager] Connected to MQTT broker successfully.")
            # Subscribe to controller topics
            self.client.subscribe(Config.MQTT_TOPIC_ACKNOWLEDGED)
            self.client.subscribe(Config.MQTT_TOPIC_CLEARED)
            self.client.subscribe(Config.MQTT_TOPIC_CONTROLLER_STATUS)
            print(f"[MQTTManager] Subscribed to ACK, CLEAR, and CONTROLLER_STATUS topics.")
        else:
            print(f"[MQTTManager] Connection failed with result code {rc}")

    def _on_disconnect(self, client, userdata, flags_or_rc, rc_or_props=None, properties=None):
        self.is_connected = False
        print("[MQTTManager] Disconnected from MQTT broker.")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload_str = msg.payload.decode("utf-8")
            data = json.loads(payload_str) if payload_str else {}
            # Extract target item or event ID
            item_or_id = data.get("event_id") or data.get("vegetable") or data.get("produce") or payload_str

            if topic == Config.MQTT_TOPIC_ACKNOWLEDGED:
                print(f"[MQTTManager] Received ACK from ESP32: {item_or_id}")
                for cb in self._on_ack_callbacks:
                    cb(item_or_id)

            elif topic == Config.MQTT_TOPIC_CLEARED:
                print(f"[MQTTManager] Received CLEAR from ESP32: {item_or_id}")
                for cb in self._on_clear_callbacks:
                    cb(item_or_id)

            elif topic == Config.MQTT_TOPIC_CONTROLLER_STATUS:
                self.last_controller_status = {
                    "online": True,
                    "last_seen": time.time(),
                    "ip": data.get("ip"),
                    "details": data
                }
        except Exception as e:
            print(f"[MQTTManager] Error handling message on {msg.topic}: {e}")

    def publish_spoilage_event(self, event_data: Dict[str, Any]):
        """
        Publishes a spoilage alert event to the ESP32.
        """
        if not self.is_connected:
            print("[MQTTManager] Notice: Broker offline, skipping real-time MQTT publish.")
            return False

        produce = event_data.get("produce") or event_data.get("vegetable")
        led_idx = Config.PRODUCE_LED_MAP.get(produce, 1)

        payload = {
            "event_id": event_data.get("event_id"),
            "event": "SPOILAGE_DETECTED",
            "vegetable": produce,
            "status": "Spoiled",
            "confidence": round(float(event_data.get("freshness_score", 0.0)), 3),
            "image_path": event_data.get("image_path", ""),
            "timestamp": event_data.get("created_at"),
            "led_index": led_idx
        }

        try:
            self.client.publish(
                Config.MQTT_TOPIC_SPOILAGE,
                json.dumps(payload),
                qos=1
            )
            print(f"[MQTTManager] Published spoilage alert for {produce} (LED #{led_idx}) to {Config.MQTT_TOPIC_SPOILAGE}")
            return True
        except Exception as e:
            print(f"[MQTTManager] Failed to publish event: {e}")
            return False

    def sync_active_alerts(self, active_alerts: List[Dict[str, Any]]):
        """
        Publishes the retained active alerts state so reconnecting ESP32 immediately recovers.
        """
        if not self.is_connected:
            return False

        minimal_list = []
        for a in active_alerts:
            produce = a.get("produce")
            minimal_list.append({
                "event_id": a.get("event_id"),
                "vegetable": produce,
                "status": a.get("status"),
                "led_index": Config.PRODUCE_LED_MAP.get(produce, 1)
            })

        try:
            self.client.publish(
                Config.MQTT_TOPIC_ACTIVE_ALERTS,
                json.dumps(minimal_list),
                qos=1,
                retain=True
            )
            return True
        except Exception as e:
            print(f"[MQTTManager] Failed to sync active alerts: {e}")
            return False

    def get_status(self) -> dict:
        is_alive = False
        if self.last_controller_status["last_seen"]:
            is_alive = (time.time() - self.last_controller_status["last_seen"]) < 60

        return {
            "mqtt_broker_connected": self.is_connected,
            "broker_host": f"{self.host}:{self.port}",
            "esp32_online": is_alive,
            "esp32_last_seen": self.last_controller_status.get("last_seen"),
            "esp32_ip": self.last_controller_status.get("ip")
        }
