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

    # Target Hardware Platform
    PLATFORM_NAME = "Raspberry Pi 5"

    # TFLite Model Paths for Edge & Embedded Devices (Raspberry Pi 5 ARM Cortex-A76)
    TFLITE_CATEGORY_MODEL = os.path.join(MODEL_DIR, 'category_classifier.tflite')
    TFLITE_FRESHNESS_MODEL = os.path.join(MODEL_DIR, 'mobilenetv2_baseline.tflite')
    KERAS_CATEGORY_MODEL = os.path.join(MODEL_DIR, 'category_classifier.keras')
    KERAS_FRESHNESS_MODEL = os.path.join(MODEL_DIR, 'mobilenetv2_baseline.keras')

    # External USB Camera settings (V4L2 on Raspberry Pi 5)
    CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', '1280'))
    CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', '720'))
    CAMERA_FPS = int(os.getenv('CAMERA_FPS', '20'))
    # CAMERA_INDEX can be an integer, 'auto', or a device path like '/dev/video2'
    CAMERA_INDEX = os.getenv('CAMERA_INDEX', 'auto')

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
    MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'freshscan_pi5_controller')

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

    # =========================================================================
    # Gemini AI Pro Settings (Multimodal Quality Inspection & Token Optimizer)
    # =========================================================================
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    GEMINI_AUTO_INTERVAL = float(os.getenv('GEMINI_AUTO_INTERVAL', '15.0'))  # Seconds between auto-captures
    GEMINI_COOLDOWN = float(os.getenv('GEMINI_COOLDOWN', '10.0'))           # Minimum seconds between API calls
    GEMINI_FRAME_DIFF_THRESHOLD = float(os.getenv('GEMINI_FRAME_DIFF_THRESHOLD', '10.0'))  # % diff to qualify as new scene
    GEMINI_MAX_IMAGE_DIM = int(os.getenv('GEMINI_MAX_IMAGE_DIM', '512'))    # Downscale dimension for minimal tokens
