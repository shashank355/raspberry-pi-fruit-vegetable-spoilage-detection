import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if available
load_dotenv()


class Config:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    DATA_DIR = os.path.join(PROJECT_ROOT, 'artifacts', 'data')
    RAW_DATA_DIR = os.path.join(PROJECT_ROOT, 'artifacts', 'data', 'raw')
    PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, 'artifacts', 'data', 'processed')
    MODEL_DIR = os.path.join(PROJECT_ROOT, 'artifacts', 'models')
    RESULTS_DIR = os.path.join(PROJECT_ROOT, 'artifacts', 'results')
    CAPTURED_IMAGES_DIR = os.path.join(PROJECT_ROOT, 'captured_images')

    METADATA_FILE = os.path.join(PROJECT_ROOT, 'artifacts', 'data', 'metadata.json')
    CATEGORY_NAMES = ['Fruits', 'Vegetables']
    FRUIT_NAMES = ['Apple', 'Banana', 'Mango', 'Orange', 'Strawberry']
    VEGETABLE_NAMES = ['Bellpepper', 'Carrot', 'Cucumber', 'Potato', 'Tomato']
    CLASS_NAMES = ['Fresh', 'Rotten']

    # 10 produce categories exactly in model label order
    PRODUCE_CATEGORIES = [
        "Apple", "Banana", "Bellpepper", "Carrot", "Cucumber",
        "Mango", "Orange", "Potato", "Strawberry", "Tomato"
    ]

    # Category to LED index mapping (1 to 10)
    PRODUCE_LED_MAP = {
        "Apple": 1,
        "Banana": 2,
        "Bellpepper": 3,
        "Carrot": 4,
        "Cucumber": 5,
        "Mango": 6,
        "Orange": 7,
        "Potato": 8,
        "Strawberry": 9,
        "Tomato": 10
    }

    # TFLite Model Paths for Edge & Embedded Devices (Raspberry Pi 4B)
    TFLITE_CATEGORY_MODEL = os.path.join(MODEL_DIR, 'category_classifier.tflite')
    TFLITE_FRESHNESS_MODEL = os.path.join(MODEL_DIR, 'mobilenetv2_baseline.tflite')
    KERAS_CATEGORY_MODEL = os.path.join(MODEL_DIR, 'category_classifier.keras')
    KERAS_FRESHNESS_MODEL = os.path.join(MODEL_DIR, 'mobilenetv2_baseline.keras')

    # Raspberry Pi Camera settings
    CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', '1280'))
    CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', '720'))
    CAMERA_FPS = int(os.getenv('CAMERA_FPS', '20'))
    CAMERA_INDEX = int(os.getenv('CAMERA_INDEX', '0'))

    # AI Decision Engine Threshold
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.70'))

    # SQLite Database
    DB_PATH = os.path.join(PROJECT_ROOT, 'artifacts', 'freshscan.db')

    # MQTT Settings for ESP32 Wireless Alert Panel
    MQTT_ENABLED = os.getenv('MQTT_ENABLED', 'true').lower() in ('true', '1', 'yes')
    MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', '127.0.0.1')
    MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', None)
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
    MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'freshscan_pi_controller')

    # MQTT Topics
    MQTT_TOPIC_SPOILAGE = "freshscan/events/spoilage"
    MQTT_TOPIC_ACKNOWLEDGED = "freshscan/events/acknowledged"
    MQTT_TOPIC_CLEARED = "freshscan/events/cleared"
    MQTT_TOPIC_CONTROLLER_STATUS = "freshscan/controller/status"
    MQTT_TOPIC_ACTIVE_ALERTS = "freshscan/events/active_alerts"

    # Telegram Notification Settings
    TELEGRAM_ENABLED = os.getenv('TELEGRAM_ENABLED', 'true').lower() in ('true', '1', 'yes')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
