/*
  ==============================================================================
  FreshScan AI 2.0 — ESP32 Wireless Physical Spoilage Alert Panel
  ==============================================================================
  Hardware:
    - ESP32 DevKit
    - 16x2 I2C LCD (LiquidCrystal_I2C) at address 0x27 or 0x3F
    - 10 Red Produce Category LEDs (Apple to Tomato)
    - 2 Push Buttons (ACKNOWLEDGE & CLEAR) with internal pullups

  Pin Configuration:
    - I2C LCD: SDA = GPIO 21, SCL = GPIO 22
    - Produce LEDs (via 220-330 ohm resistors):
        LED 1  (Apple)       : GPIO 13
        LED 2  (Banana)      : GPIO 14
        LED 3  (Bellpepper)  : GPIO 16
        LED 4  (Carrot)      : GPIO 17
        LED 5  (Cucumber)    : GPIO 18
        LED 6  (Mango)       : GPIO 19
        LED 7  (Orange)      : GPIO 23
        LED 8  (Potato)      : GPIO 25
        LED 9  (Strawberry)  : GPIO 26
        LED 10 (Tomato)      : GPIO 27
    - Buttons (Active LOW with internal INPUT_PULLUP):
        ACKNOWLEDGE Button   : GPIO 32
        CLEAR Button         : GPIO 33

  Required Arduino Libraries:
    - WiFi (built-in ESP32 core)
    - PubSubClient (by Nick O'Leary)
    - ArduinoJson (v6 or v7 by Benoit Blanchon)
    - LiquidCrystal_I2C (by Frank de Brabander / Marco Schwartz)
  ==============================================================================
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ArduinoJson.h>

// ==========================================
// Network & MQTT Configuration
// ==========================================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// IP Address of the Raspberry Pi 4B running the Mosquitto broker
const char* MQTT_BROKER   = "192.168.1.100";
const int   MQTT_PORT     = 1883;
const char* MQTT_USER     = "";  // Leave empty if unauthenticated
const char* MQTT_PASS     = "";

// MQTT Topics
const char* TOPIC_SPOILAGE     = "freshscan/events/spoilage";
const char* TOPIC_ACKNOWLEDGED = "freshscan/events/acknowledged";
const char* TOPIC_CLEARED      = "freshscan/events/cleared";
const char* TOPIC_STATUS       = "freshscan/controller/status";
const char* TOPIC_ACTIVE_SYNC  = "freshscan/events/active_alerts";

// ==========================================
// Hardware Pin Definitions
// ==========================================
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22

#define BTN_ACK_PIN   32
#define BTN_CLEAR_PIN 33

const int NUM_CATEGORIES = 10;
const char* CATEGORY_NAMES[NUM_CATEGORIES] = {
  "Apple", "Banana", "Bellpepper", "Carrot", "Cucumber",
  "Mango", "Orange", "Potato", "Strawberry", "Tomato"
};

const int LED_PINS[NUM_CATEGORIES] = {
  13, // Apple
  14, // Banana
  16, // Bellpepper
  17, // Carrot
  18, // Cucumber
  19, // Mango
  23, // Orange
  25, // Potato
  26, // Strawberry
  27  // Tomato
};

// ==========================================
// Alert States & Data Structures
// ==========================================
enum AlertState {
  STATE_OFF = 0,         // No active alert
  STATE_NEW = 1,         // Spoilage detected: Blinking LED
  STATE_ACKNOWLEDGED = 2 // User acknowledged: Steady ON
};

struct ProduceAlert {
  AlertState state;
  String event_id;
  unsigned long timestamp;
};

ProduceAlert alerts[NUM_CATEGORIES];

// ==========================================
// Global Peripherals
// ==========================================
LiquidCrystal_I2C lcd(0x27, 16, 2);
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// Timing variables (non-blocking millis)
unsigned long lastBlinkTime    = 0;
bool          blinkState       = false;
const unsigned long BLINK_INTERVAL = 350; // ms

unsigned long lastLcdRotate    = 0;
int           currentDisplayIndex = -1;
const unsigned long LCD_ROTATE_INTERVAL = 2500; // ms

unsigned long lastHeartbeat    = 0;
const unsigned long HEARTBEAT_INTERVAL = 30000; // ms

// Button debounce tracking
unsigned long lastAckPress   = 0;
unsigned long lastClearPress = 0;
const unsigned long DEBOUNCE_DELAY = 250; // ms

// ==========================================
// Forward Declarations
// ==========================================
void setupWiFi();
void reconnectMQTT();
void handleMqttMessage(char* topic, byte* payload, unsigned int length);
void updateLeds();
void updateLcd();
void checkButtons();
int findCategoryIndex(const char* name);
int countActiveAlerts();

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n🍓 ============================================");
  Serial.println("   FreshScan AI 2.0 — ESP32 Physical Panel");
  Serial.println("🍓 ============================================");

  // Initialize LEDs & Turn OFF
  for (int i = 0; i < NUM_CATEGORIES; i++) {
    pinMode(LED_PINS[i], OUTPUT);
    digitalWrite(LED_PINS[i], LOW);
    alerts[i].state = STATE_OFF;
    alerts[i].event_id = "";
    alerts[i].timestamp = 0;
  }

  // Initialize Buttons
  pinMode(BTN_ACK_PIN, INPUT_PULLUP);
  pinMode(BTN_CLEAR_PIN, INPUT_PULLUP);

  // Initialize I2C & LCD
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("FreshScan AI 2.0");
  lcd.setCursor(0, 1);
  lcd.print("Connecting WiFi...");

  setupWiFi();

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(handleMqttMessage);
  mqttClient.setBufferSize(2048);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("FreshScan AI 2.0");
  lcd.setCursor(0, 1);
  lcd.print("System Ready OK");
}

// ==========================================
// MAIN LOOP (Non-Blocking)
// ==========================================
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setupWiFi();
  }

  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  // 1. Non-blocking LED Blinking for NEW alerts
  unsigned long now = millis();
  if (now - lastBlinkTime >= BLINK_INTERVAL) {
    lastBlinkTime = now;
    blinkState = !blinkState;
    updateLeds();
  }

  // 2. Non-blocking LCD Rotation
  if (now - lastLcdRotate >= LCD_ROTATE_INTERVAL) {
    lastLcdRotate = now;
    updateLcd();
  }

  // 3. Check Physical Buttons (ACK & CLEAR)
  checkButtons();

  // 4. Send Periodic Heartbeat to Raspberry Pi
  if (now - lastHeartbeat >= HEARTBEAT_INTERVAL) {
    lastHeartbeat = now;
    StaticJsonDocument<128> doc;
    doc["device"] = "ESP32_Alert_Panel";
    doc["ip"] = WiFi.localIP().toString();
    doc["active_alerts"] = countActiveAlerts();
    doc["uptime_sec"] = millis() / 1000;
    char buffer[128];
    serializeJson(doc, buffer);
    mqttClient.publish(TOPIC_STATUS, buffer);
  }
}

// ==========================================
// Wi-Fi Connection
// ==========================================
void setupWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("[WiFi] Connecting to: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(300);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n[WiFi] Connection timeout. Retrying in background...");
  }
}

// ==========================================
// MQTT Connection & Subscription
// ==========================================
void reconnectMQTT() {
  static unsigned long lastMqttAttempt = 0;
  if (millis() - lastMqttAttempt < 4000) return;
  lastMqttAttempt = millis();

  Serial.print("[MQTT] Connecting to broker...");
  String clientId = "ESP32_FreshScan_" + String(random(0xffff), HEX);

  bool connected = false;
  if (strlen(MQTT_USER) > 0) {
    connected = mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASS);
  } else {
    connected = mqttClient.connect(clientId.c_str());
  }

  if (connected) {
    Serial.println(" Connected!");
    mqttClient.subscribe(TOPIC_SPOILAGE, 1);
    mqttClient.subscribe(TOPIC_ACTIVE_SYNC, 1);

    // Announce online status
    StaticJsonDocument<128> doc;
    doc["device"] = "ESP32_Alert_Panel";
    doc["event"] = "ONLINE";
    doc["ip"] = WiFi.localIP().toString();
    char buf[128];
    serializeJson(doc, buf);
    mqttClient.publish(TOPIC_STATUS, buf);
  } else {
    Serial.print(" Failed (rc=");
    Serial.print(mqttClient.state());
    Serial.println("). Retrying...");
  }
}

// ==========================================
// MQTT Message Handler
// ==========================================
void handleMqttMessage(char* topic, byte* payload, unsigned int length) {
  char jsonBuffer[length + 1];
  memcpy(jsonBuffer, payload, length);
  jsonBuffer[length] = '\0';

  Serial.print("[MQTT] Received on ");
  Serial.print(topic);
  Serial.print(": ");
  Serial.println(jsonBuffer);

  // Case A: Single Spoilage Event Received
  if (String(topic) == TOPIC_SPOILAGE) {
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, jsonBuffer);
    if (error) {
      Serial.println("[MQTT] JSON parse error");
      return;
    }

    const char* veg = doc["vegetable"];
    const char* eid = doc["event_id"];
    int idx = findCategoryIndex(veg);

    if (idx >= 0) {
      alerts[idx].state = STATE_NEW;
      alerts[idx].event_id = String(eid);
      alerts[idx].timestamp = millis();
      Serial.printf("[Alert] Spoilage alert set for %s (LED GPIO %d)\n", veg, LED_PINS[idx]);
      lastLcdRotate = 0; // Force immediate LCD refresh
    }
  }

  // Case B: Active Alerts State Sync (on reboot or Pi state update)
  else if (String(topic) == TOPIC_ACTIVE_SYNC) {
    DynamicJsonDocument doc(2048);
    DeserializationError error = deserializeJson(doc, jsonBuffer);
    if (error) return;

    // Reset all alerts not present in active list
    bool activeMap[NUM_CATEGORIES] = {false};

    JsonArray array = doc.as<JsonArray>();
    for (JsonObject item : array) {
      const char* veg = item["vegetable"];
      const char* status = item["status"];
      const char* eid = item["event_id"];
      int idx = findCategoryIndex(veg);
      if (idx >= 0) {
        activeMap[idx] = true;
        alerts[idx].event_id = String(eid);
        alerts[idx].state = (String(status) == "ACKNOWLEDGED") ? STATE_ACKNOWLEDGED : STATE_NEW;
      }
    }

    for (int i = 0; i < NUM_CATEGORIES; i++) {
      if (!activeMap[i]) {
        alerts[i].state = STATE_OFF;
        alerts[i].event_id = "";
      }
    }
    updateLeds();
  }
}

// ==========================================
// LED Management (3 States)
// ==========================================
void updateLeds() {
  for (int i = 0; i < NUM_CATEGORIES; i++) {
    switch (alerts[i].state) {
      case STATE_OFF:
        digitalWrite(LED_PINS[i], LOW);
        break;
      case STATE_NEW:
        // Blink LED
        digitalWrite(LED_PINS[i], blinkState ? HIGH : LOW);
        break;
      case STATE_ACKNOWLEDGED:
        // Steady ON
        digitalWrite(LED_PINS[i], HIGH);
        break;
    }
  }
}

// ==========================================
// 16x2 LCD Display Rotation
// ==========================================
void updateLcd() {
  int totalActive = countActiveAlerts();

  if (totalActive == 0) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("FreshScan AI 2.0");
    lcd.setCursor(0, 1);
    lcd.print("All Produce OK");
    currentDisplayIndex = -1;
    return;
  }

  // Find next active alert to display
  int nextIdx = (currentDisplayIndex + 1) % NUM_CATEGORIES;
  int searchCount = 0;
  while (alerts[nextIdx].state == STATE_OFF && searchCount < NUM_CATEGORIES) {
    nextIdx = (nextIdx + 1) % NUM_CATEGORIES;
    searchCount++;
  }

  currentDisplayIndex = nextIdx;
  String produceName = CATEGORY_NAMES[currentDisplayIndex];
  produceName.toUpperCase();

  lcd.clear();
  // Row 1: SPOILED: <NAME>
  lcd.setCursor(0, 0);
  lcd.print("SPOILED: ");
  lcd.print(produceName);

  // Row 2: Status & Instruction
  lcd.setCursor(0, 1);
  if (alerts[currentDisplayIndex].state == STATE_NEW) {
    lcd.print("NEW! BTN1=ACK");
  } else {
    lcd.print("ACK'D BTN2=CLR");
  }
}

// ==========================================
// Physical Buttons (ACK & CLEAR)
// ==========================================
void checkButtons() {
  unsigned long now = millis();

  // Button 1: ACKNOWLEDGE
  if (digitalRead(BTN_ACK_PIN) == LOW && (now - lastAckPress > DEBOUNCE_DELAY)) {
    lastAckPress = now;

    if (currentDisplayIndex >= 0 && alerts[currentDisplayIndex].state == STATE_NEW) {
      alerts[currentDisplayIndex].state = STATE_ACKNOWLEDGED;
      updateLeds();

      // Publish ACK to Raspberry Pi
      StaticJsonDocument<128> doc;
      doc["vegetable"] = CATEGORY_NAMES[currentDisplayIndex];
      doc["event_id"] = alerts[currentDisplayIndex].event_id;
      doc["action"] = "ACKNOWLEDGE";
      char buffer[128];
      serializeJson(doc, buffer);
      mqttClient.publish(TOPIC_ACKNOWLEDGED, buffer, 1);

      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print(CATEGORY_NAMES[currentDisplayIndex]);
      lcd.setCursor(0, 1);
      lcd.print("ACKNOWLEDGED OK");
      delay(800);
      updateLcd();
    }
  }

  // Button 2: CLEAR
  if (digitalRead(BTN_CLEAR_PIN) == LOW && (now - lastClearPress > DEBOUNCE_DELAY)) {
    lastClearPress = now;

    if (currentDisplayIndex >= 0 && alerts[currentDisplayIndex].state != STATE_OFF) {
      String clearedName = CATEGORY_NAMES[currentDisplayIndex];
      String clearedEid  = alerts[currentDisplayIndex].event_id;

      alerts[currentDisplayIndex].state = STATE_OFF;
      alerts[currentDisplayIndex].event_id = "";
      updateLeds();

      // Publish CLEAR to Raspberry Pi
      StaticJsonDocument<128> doc;
      doc["vegetable"] = clearedName;
      doc["event_id"] = clearedEid;
      doc["action"] = "CLEAR";
      char buffer[128];
      serializeJson(doc, buffer);
      mqttClient.publish(TOPIC_CLEARED, buffer, 1);

      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print(clearedName);
      lcd.setCursor(0, 1);
      lcd.print("ALERT CLEARED");
      delay(800);
      updateLcd();
    }
  }
}

// ==========================================
// Utilities
// ==========================================
int findCategoryIndex(const char* name) {
  if (!name) return -1;
  for (int i = 0; i < NUM_CATEGORIES; i++) {
    if (strcasecmp(name, CATEGORY_NAMES[i]) == 0) {
      return i;
    }
  }
  return -1;
}

int countActiveAlerts() {
  int count = 0;
  for (int i = 0; i < NUM_CATEGORIES; i++) {
    if (alerts[i].state != STATE_OFF) count++;
  }
  return count;
}
