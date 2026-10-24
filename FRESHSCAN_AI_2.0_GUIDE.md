# FreshScan AI 2.0 — Complete Implementation Guide
### Edge AI Spoilage Detection • Raspberry Pi 4B • ESP32 Wireless Alert Panel • Telegram Bot

FreshScan AI 2.0 is an integrated, modular IoT & Edge AI system:
- **Raspberry Pi 4B + Rev 1.3 CSI Camera**: Runs fast TensorFlow Lite MobileNetV2 inference (~60ms), validates prediction confidence, prevents duplicate alerts, manages a persistent SQLite database, and publishes wireless MQTT events.
- **ESP32 Physical Alert Panel**: Controls a 16×2 I²C LCD (rotating multi-alert display), 10 individually assigned produce LEDs (Blinking = New Alert, Steady ON = Acknowledged, OFF = Cleared), and 2 physical buttons (ACKNOWLEDGE and CLEAR).
- **Telegram Notification Worker**: Asynchronously dispatches instant spoilage warnings with the captured annotated photograph without blocking the physical alerts.

---

## 1. System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                            RASPBERRY PI 4B (Edge AI Controller)                   |
|                                                                                   |
|  [Pi Camera Rev 1.3]                                                              |
|          │                                                                        |
|          ▼                                                                        |
|  [TFLite Dual Engine]                                                             |
|   ├── Category Classifier (10 Classes)                                            |
|   └── Freshness Classifier (Fresh / Rotten)                                       |
|          │                                                                        |
|          ▼                                                                        |
|  [Decision Engine & Event Manager] ◄──────► [SQLite Database (freshscan.db)]      |
|   ├── Confidence Check (>= 0.70)                                                  |
|   ├── Duplicate Alert Prevention                                                  |
|   └── Event ID Generation (FS-XXXX)                                               |
|          │                                       │                                |
|          ▼ (Asynchronous Queue)                  ▼ (Wireless MQTT: Port 1883)     |
|  [Telegram Bot Worker]                 [Mosquitto MQTT Broker]                    |
|   └── Text + Photo Alert                         ▲          │                     |
+──────────────────────────────────────────────────┼──────────┼─────────────────────+
                                        Wi-Fi Link │          │ Wi-Fi Link
                                                   │          ▼
+--------------------------------------------------┴────────────────────────────────+
|                              ESP32 PHYSICAL ALERT PANEL                           |
|                                                                                   |
|    [PubSubClient MQTT] ◄── Subscribes to: freshscan/events/spoilage               |
|          │             └── Publishes to:  freshscan/events/acknowledged & cleared |
|          ▼                                                                        |
|  [Non-Blocking State Manager]                                                     |
|   ├── 16x2 I2C LCD  ──► Displays rotating alerts: "[1/2] SPOILED: TOMATO"         |
|   ├── 10-LED Bank   ──► Blinking (New) | Steady ON (Ack'd) | OFF (Cleared)       |
|   └── 2 Buttons     ──► BTN 1 (GPIO 32): Acknowledge | BTN 2 (GPIO 33): Clear     |
+-----------------------------------------------------------------------------------+
```

---

## 2. Hardware Pinout & Wiring

### 2.1 ESP32 DevKit to Peripherals

| Peripheral | ESP32 GPIO | Description / Wiring |
| :--- | :--- | :--- |
| **16×2 LCD SDA** | **GPIO 21** | I²C Data line (Verify 3.3V logic or use level shifter) |
| **16×2 LCD SCL** | **GPIO 22** | I²C Clock line |
| **LED 1 (Apple)** | **GPIO 13** | Red LED via 220–330 Ω resistor to GND |
| **LED 2 (Banana)** | **GPIO 14** | Red LED via 220–330 Ω resistor to GND |
| **LED 3 (Bellpepper)** | **GPIO 16** | Red LED via 220–330 Ω resistor to GND |
| **LED 4 (Carrot)** | **GPIO 17** | Red LED via 220–330 Ω resistor to GND |
| **LED 5 (Cucumber)** | **GPIO 18** | Red LED via 220–330 Ω resistor to GND |
| **LED 6 (Mango)** | **GPIO 19** | Red LED via 220–330 Ω resistor to GND |
| **LED 7 (Orange)** | **GPIO 23** | Red LED via 220–330 Ω resistor to GND |
| **LED 8 (Potato)** | **GPIO 25** | Red LED via 220–330 Ω resistor to GND |
| **LED 9 (Strawberry)** | **GPIO 26** | Red LED via 220–330 Ω resistor to GND |
| **LED 10 (Tomato)** | **GPIO 27** | Red LED via 220–330 Ω resistor to GND |
| **ACK Button** | **GPIO 32** | Push button to GND (Internal `INPUT_PULLUP` enabled) |
| **CLEAR Button** | **GPIO 33** | Push button to GND (Internal `INPUT_PULLUP` enabled) |

---

## 3. MQTT Topics & Message Formats

| MQTT Topic | Direction | Purpose | Example Payload |
| :--- | :--- | :--- | :--- |
| `freshscan/events/spoilage` | Pi ➔ ESP32 | Transmits newly confirmed spoilage event | `{"event_id":"FS-0001","event":"SPOILAGE_DETECTED","vegetable":"Tomato","status":"Spoiled","confidence":0.962,"led_index":10}` |
| `freshscan/events/active_alerts` | Pi ➔ ESP32 | Retained active alerts list for boot synchronization | `[{"event_id":"FS-0001","vegetable":"Tomato","status":"NEW","led_index":10}]` |
| `freshscan/events/acknowledged` | ESP32 ➔ Pi | Button 1 pressed; user acknowledged warning | `{"vegetable":"Tomato","event_id":"FS-0001","action":"ACKNOWLEDGE"}` |
| `freshscan/events/cleared` | ESP32 ➔ Pi | Button 2 pressed; spoiled item removed | `{"vegetable":"Tomato","event_id":"FS-0001","action":"CLEAR"}` |
| `freshscan/controller/status` | ESP32 ➔ Pi | Heartbeat & Wi-Fi IP reporting | `{"device":"ESP32_Alert_Panel","ip":"192.168.1.150","active_alerts":1}` |

---

## 4. Setting up the ESP32 Firmware

The ESP32 firmware source code is located at:
[`esp32_firmware/FreshScan_Controller/FreshScan_Controller.ino`](file:///home/shashank/Documents/vegies_classifier%20v2/Image-Based-Food-Freshness-Prediction-System/esp32_firmware/FreshScan_Controller/FreshScan_Controller.ino)

### Steps in Arduino IDE:
1. Open Arduino IDE and install the **ESP32 Board Package** (`esp32` by Espressif).
2. Install required libraries from Library Manager:
   - **`PubSubClient`** by Nick O'Leary
   - **`ArduinoJson`** by Benoit Blanchon (v6 or v7)
   - **`LiquidCrystal_I2C`** by Frank de Brabander / Marco Schwartz
3. Open `FreshScan_Controller.ino`.
4. Update the Wi-Fi and MQTT Broker IP settings:
   ```cpp
   const char* WIFI_SSID     = "YOUR_WIFI_SSID";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   const char* MQTT_BROKER   = "192.168.1.100"; // IP address of your Raspberry Pi 4B
   ```
5. Select **ESP32 Dev Module**, choose your serial port, and click **Upload**.

---

## 5. Setting up Telegram Bot Notifications

1. Open Telegram and search for **`@BotFather`**.
2. Send `/newbot`, follow prompts, and copy your **HTTP API Token**.
3. Start a chat with your new bot (click `Start`).
4. Find your chat ID:
   - Message `@userinfobot` or `@RawDataBot` on Telegram to get your numeric `Id`.
5. Configure in `Image-Based-Food-Freshness-Prediction-System/.env`:
   ```ini
   TELEGRAM_ENABLED=true
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
   TELEGRAM_CHAT_ID=987654321
   ```

---

## 6. Running FreshScan AI 2.0 on Raspberry Pi 4B

```bash
cd Image-Based-Food-Freshness-Prediction-System

# 1. Run the one-click Pi setup (installs mosquitto, picamera2, venv):
./setup_pi.sh

# 2. Start the integrated web server and AI engine:
./run.sh
```

- Open the dashboard in any browser: `http://<raspberry-pi-ip>:8000`
- Access the **Active Spoilage Alerts** panel to monitor all alerts syncing live with your ESP32.
- Use the **Hardware Test Studio** in the UI to simulate any vegetable alert (e.g., Tomato LED 10) to test your LCD and LEDs immediately!

---

## 7. Running in Standalone / Headless CLI Mode

If running headless without a browser or using an external GPIO trigger:
```bash
source venv/bin/activate

# Single inspection from Camera Rev 1.3:
python capture_and_classify.py

# Continuous inspection loop every 3 seconds:
python capture_and_classify.py --loop --interval 3.0
```
