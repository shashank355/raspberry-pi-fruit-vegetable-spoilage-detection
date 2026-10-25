# FreshScan AI 2.0 — Complete Implementation Guide
### Edge AI Spoilage Detection • Raspberry Pi 5 • External USB Camera • Gemini AI Pro • ESP32 Wireless Panel • Telegram Bot

FreshScan AI 2.0 is an integrated, modular IoT & Edge AI system:
- **Raspberry Pi 5 + External USB Camera**: Runs ultra-fast TensorFlow Lite MobileNetV2 inference (~15–25ms on Cortex-A76), validates prediction confidence, prevents duplicate alerts, manages a persistent SQLite database, and publishes wireless MQTT events.
- **Gemini AI Pro Quality Inspector**: Features an interactive dashboard toggle switch that auto-captures live photos from the USB camera at frequent intervals, performing deep multimodal quality analysis, defect detection, and shelf-life estimation via Gemini API with strict **Token-Saving Guardrails** (scene-change gating, 512px downscaling, and adaptive cooldowns).
- **ESP32 Physical Alert Panel**: Controls a 16×2 I²C LCD (rotating multi-alert display), 10 individually assigned produce LEDs (Blinking = New Alert, Steady ON = Acknowledged, OFF = Cleared), and 2 physical buttons (ACKNOWLEDGE and CLEAR).
- **Telegram Notification Worker**: Asynchronously dispatches instant spoilage warnings with the captured annotated photograph without blocking the physical alerts.

---

## 1. System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                            RASPBERRY PI 5 (Edge AI Controller)                    |
|                                                                                   |
|  [External USB Camera (V4L2)]                                                     |
|          │                                                                        |
|          ├──► [Local Edge TFLite SIMD] (~20ms latency, 0 tokens)                  |
|          │     ├── Category Classifier (10 Classes)                               |
|          │     └── Freshness Classifier (Fresh / Rotten)                          |
|          │                                                                        |
|          └──► [Gemini AI Pro Engine] (When AI Pro Toggle is ON)                   |
|                ├── Motion / Frame Diff Gating (Skips static frames)               |
|                ├── 512px JPEG Downscaling (~258 tokens vs 1000+)                  |
|                ├── Adaptive Cooldown Protection (Guards rate limits)              |
|                └── Structured Agronomic Quality Report                            |
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
| **16×2 LCD SDA** | **GPIO 21** | I²C Data line (3.3V logic) |
| **16×2 LCD SCL** | **GPIO 22** | I²C Clock line |
| **LED 1 (Apple)** | **GPIO 13** | Red LED via 220–330 Ω resistor to GND |
| **LED 2 (Banana)** | **GPIO 14** | Red LED via 220–330 Ω resistor to GND |
| **LED 3 (Bell Pepper)** | **GPIO 16** | Red LED via 220–330 Ω resistor to GND |
| **LED 4 (Carrot)** | **GPIO 17** | Red LED via 220–330 Ω resistor to GND |
| **LED 5 (Cucumber)** | **GPIO 18** | Red LED via 220–330 Ω resistor to GND |
| **LED 6 (Mango)** | **GPIO 19** | Red LED via 220–330 Ω resistor to GND |
| **LED 7 (Orange)** | **GPIO 23** | Red LED via 220–330 Ω resistor to GND |
| **LED 8 (Potato)** | **GPIO 25** | Red LED via 220–330 Ω resistor to GND |
| **LED 9 (Strawberry)** | **GPIO 26** | Red LED via 220–330 Ω resistor to GND |
| **LED 10 (Tomato)** | **GPIO 27** | Red LED via 220–330 Ω resistor to GND |
| **Button 1 (ACKNOWLEDGE)** | **GPIO 32** | Momentary push button to GND (Internal PULLUP) |
| **Button 2 (CLEAR)** | **GPIO 33** | Momentary push button to GND (Internal PULLUP) |

---

## 3. Gemini AI Pro & Token Efficiency Architecture

The user can enable the **AI Pro** toggle button in the dashboard for continuous quality inspection. To prevent token exhaustion under limited quotas, FreshScan AI 2.0 incorporates 4 tiers of token protection:

```
[Camera Frame]
      │
      ▼
[Is Scene Changed? (64x64 Grayscale Diff >= 10%)]
      ├── NO ──► SKIP Gemini call! Re-use verified verdict (Tokens Saved: ~300)
      │
      └── YES ─► [Is Cooldown Expired? (>= 10s elapsed)]
                     ├── NO ──► SKIP Gemini call! Wait for cooldown
                     │
                     └── YES ─► [Pre-Downscale to 512x512 JPEG]
                                    │ (Reduces token consumption by ~75%)
                                    ▼
                                [Gemini 2.5 Flash API Call (~258 tokens)]
                                    │
                                    ▼
                         [Render Results in Dashboard]
```

---

## 4. Quick Start Commands

```bash
# 1. Run camera diagnostics:
python test_camera.py

# 2. Run the main web application:
./run.sh
```
