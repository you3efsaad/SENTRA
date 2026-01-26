#include <WiFi.h>
#include <HTTPClient.h>
#include <PZEM004Tv30.h>
#include <ArduinoJson.h>
#include <WiFiManager.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const char *baseURL = "https://safe-power.up.railway.app";

String deviceName = "";
String command = "";
float powerLimit = 100.0;
unsigned long countdownStart = 0;
unsigned long countdownDuration = 0;
bool countdownActive = false;
bool relayOpened = false;

#define PZEM_RX_PIN 16
#define PZEM_TX_PIN 17
#define RELAY_PIN 5
#define BUZZER_PIN 14

#define LED_PIN 14
#define RESET_BUTTON_PIN 4 // تم تغييره إلى D2 (GPIO4)
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
PZEM004Tv30 pzem(Serial2, PZEM_RX_PIN, PZEM_TX_PIN);

void setup()
{
    Serial.begin(115200);
    delay(100);

    pinMode(RESET_BUTTON_PIN, INPUT_PULLUP);
    if (digitalRead(RESET_BUTTON_PIN) == LOW)
    {
        Serial.println("BOOT button pressed - resetting WiFi settings...");
        WiFiManager wm;
        wm.resetSettings();
        delay(1000);
        ESP.restart();
    }

    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C))
    {
        Serial.println(F("SSD1306 allocation failed"));
        for (;;)
            ;
    }
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("Booting...");
    display.display();
    delay(1000);

    Serial2.begin(9600, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
    pinMode(RELAY_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, HIGH);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);

    WiFiManager wm;
    bool res = wm.autoConnect("\xe2\x9c\x8c\xef\xb8\x8f y & m \xe2\x9c\x8c\xef\xb8\x8f");
    if (!res)
    {
        Serial.println("Failed to connect to WiFi.");
        ESP.restart();
    }
    else
    {
        Serial.println("Connected to WiFi.");
        Serial.println(WiFi.localIP());
    }

    HTTPClient http;
    http.begin(String(baseURL) + "/get_device");
    int httpCode = http.GET();
    if (httpCode == 200)
    {
        String payload = http.getString();
        Serial.println("Device payload: " + payload);
        StaticJsonDocument<200> doc;
        DeserializationError error = deserializeJson(doc, payload);
        if (!error)
        {
            deviceName = doc["device"].as<String>();
            Serial.println("Device Name Fetched: " + deviceName);
        }
        else
        {
            Serial.println("Failed to parse JSON");
            deviceName = "FallbackDevice";
        }
    }
    else
    {
        Serial.println("Failed to get device name");
        deviceName = "FallbackDevice";
    }
    http.end();
}

void getControllimit()
{
    if (WiFi.status() == WL_CONNECTED)
    {
        HTTPClient http;
        http.begin(String(baseURL) + "/esp_limit");
        int httpCode = http.GET();
        if (httpCode == 200)
        {
            String payload = http.getString();
            Serial.println("Received limit: " + payload);
            StaticJsonDocument<200> doc;
            DeserializationError error = deserializeJson(doc, payload);
            if (!error)
            {
                powerLimit = doc["power_limit"].as<float>();
            }
        }
        http.end();
    }
}

void getControlCommand()
{
    if (WiFi.status() == WL_CONNECTED)
    {
        HTTPClient http;
        http.begin(String(baseURL) + "/esp_command");
        int httpCode = http.GET();
        if (httpCode == 200)
        {
            String payload = http.getString();
            Serial.println("Received command: " + payload);
            StaticJsonDocument<200> doc;
            DeserializationError error = deserializeJson(doc, payload);
            if (!error)
            {
                command = doc["command"].as<String>();
            }
        }
        http.end();
    }
}

void applyCommand()
{
    if (command == "on")
    {
        digitalWrite(RELAY_PIN, HIGH);
        Serial.println("Relay ON");
    }
    else if (command == "off")
    {
        digitalWrite(RELAY_PIN, LOW);
        Serial.println("Relay OFF");
    }
}

void getCountdownFromServer()
{
    if (WiFi.status() == WL_CONNECTED)
    {
        HTTPClient http;
        http.begin(String(baseURL) + "/get_timer");
        int httpCode = http.GET();
        if (httpCode == 200)
        {
            String payload = http.getString();
            Serial.println("Timer payload: " + payload);
            StaticJsonDocument<200> doc;
            DeserializationError error = deserializeJson(doc, payload);
            if (!error)
            {
                int remainingSeconds = doc["remaining_seconds"];
                if (remainingSeconds > 0)
                {
                    countdownDuration = remainingSeconds * 1000UL;
                    countdownStart = millis();
                    countdownActive = true;
                    relayOpened = false;
                    digitalWrite(RELAY_PIN, HIGH);
                }
            }
        }
        http.end();
    }
}

void checkCountdown()
{
    if (countdownActive && !relayOpened)
    {
        if (millis() - countdownStart >= countdownDuration)
        {
            digitalWrite(RELAY_PIN, LOW);
            relayOpened = true;
            countdownActive = false;
            Serial.println("Timer ended, relay off");
        }
    }
}

void loop()
{
    getControllimit();

    float voltage = pzem.voltage();
    float current = pzem.current();
    float power = pzem.power();
    float energy = pzem.energy();
    float frequency = pzem.frequency();
    float pf = pzem.pf();

    if (isnan(voltage) || isnan(current) || isnan(power))
    {
        Serial.println("Sensor read error");
        delay(2000);
        return;
    }

    display.clearDisplay();
    display.setCursor(0, 0);

    display.print("Volt: ");
    display.print(voltage);
    display.println(" V");

    display.print("Curr: ");
    display.print(current);
    display.println(" A");

    display.print("Power: ");
    display.print(power);
    display.println(" W");

    if (countdownActive)
    {
        unsigned long remaining = (countdownDuration - (millis() - countdownStart)) / 1000;
        display.print("Timer: ");
        display.print(remaining);
        display.println("s");
    }

    display.print("Relay: ");
    display.println(digitalRead(RELAY_PIN) ? "ON" : "OFF");
    display.display();

    if (power > powerLimit)
    {
        digitalWrite(RELAY_PIN, LOW);
        digitalWrite(BUZZER_PIN, HIGH);
        digitalWrite(LED_PIN, HIGH);
        delay(3000);
        digitalWrite(BUZZER_PIN, LOW);
        digitalWrite(LED_PIN, LOW);

        if (WiFi.status() == WL_CONNECTED)
        {
            HTTPClient http;
            http.begin(String(baseURL) + "/esp_command");
            http.addHeader("Content-Type", "application/json");
            String cmdPayload = "{\"command\":\"off\"}";
            http.POST(cmdPayload);
            http.end();
        }
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        HTTPClient http;
        http.begin(String(baseURL) + "/data");
        http.addHeader("Content-Type", "application/json");

        String payload = "{";
        payload += "\"device\":\"" + deviceName + "\",";
        payload += "\"voltage\":" + String(voltage, 1) + ",";
        payload += "\"current\":" + String(current, 2) + ",";
        payload += "\"power\":" + String(power, 1) + ",";
        payload += "\"energy_consumption\":" + String(energy, 3) + ",";
        payload += "\"active_power\":" + String(power, 1) + ",";
        payload += "\"frequency\":" + String(frequency, 1) + ",";
        payload += "\"power_factor\":" + String(pf, 2) + ",";
        payload += "\"active_energy\":" + String(energy, 3);
        payload += "}";

        http.POST(payload);
        http.end();

        getControlCommand();
        applyCommand();

        if (!countdownActive)
        {
            getCountdownFromServer();
        }

        checkCountdown();
    }

    delay(2000);
}
