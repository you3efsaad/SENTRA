#include <WiFi.h>
#include <HTTPClient.h>
#include <PZEM004Tv30.h>
#include <ArduinoJson.h>
#include <WiFiManager.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

const char *baseURL = "https://safepower.up.railway.app";

String deviceName = "";
String command = "";
float powerLimit = 100.0;
unsigned long countdownStart = 0;
unsigned long countdownDuration = 0;
bool countdownActive = false;
bool relayOpened = false;
bool hasTripped = false;

#define PZEM_RX_PIN 16
#define PZEM_TX_PIN 17
#define RELAY_PIN 5
#define BUZZER_PIN 14
#define LED_PIN 14
#define RESET_BUTTON_PIN 4

PZEM004Tv30 pzem(Serial2, PZEM_RX_PIN, PZEM_TX_PIN);
LiquidCrystal_I2C lcd(0x27, 16, 2); // تأكد من العنوان (0x27 أو 0x3F)

void setup()
{
    Serial.begin(115200);
    delay(100);

    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    lcd.print("System Booting...");
    delay(2000);
    lcd.clear();

    pinMode(RESET_BUTTON_PIN, INPUT_PULLUP);
    if (digitalRead(RESET_BUTTON_PIN) == LOW)
    {
        Serial.println("BOOT button pressed - resetting WiFi settings...");
        WiFiManager wm;
        wm.resetSettings();
        delay(1000);
        ESP.restart();
    }

    Serial2.begin(9600, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
    pinMode(RELAY_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, HIGH);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);

    WiFiManager wm;
    bool res = wm.autoConnect("Y & M Setup");
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
            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print("Timer ended");
            lcd.setCursor(0, 1);
            lcd.print("Relay OFF");

            if (WiFi.status() == WL_CONNECTED)
            {
                Serial.println("Sending OFF to server...");
                HTTPClient http;
                http.begin(String(baseURL) + "/control");
                http.addHeader("Content-Type", "application/json");
                String cmdPayload = "{\"command\":\"off\"}";
                int code = http.POST(cmdPayload);

                Serial.print("Server response code: ");
                Serial.println(code);
                http.end();

                if (code == 200)
                {
                    command = "off";
                }
                else
                {
                    Serial.println("Failed to send OFF command.");
                }
            }
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

    if (isnan(voltage))
        voltage = 0.0;
    if (isnan(current))
        current = 0.0;
    if (isnan(power))
        power = 0.0;
    if (isnan(frequency))
        frequency = 0.0;
    if (isnan(pf))
        pf = 0.0;

    lcd.clear();

    if (hasTripped)
    {
        lcd.setCursor(0, 0);
        lcd.print("LIMIT EXCEEDED");
        lcd.setCursor(0, 1);
        lcd.print("Relay OFF");
    }
    else
    {
        if (countdownActive)
        {
            unsigned long now = millis();
            unsigned long elapsed = now - countdownStart;
            unsigned long remaining = (countdownDuration - elapsed) / 1000;

            if (remaining > 0)
            {
                lcd.setCursor(0, 0);
                lcd.print("V:");
                lcd.print(voltage, 1);
                lcd.print(" P:");
                lcd.print(power, 1); // طباعة الجهد بدون فاصلة عشرية

                lcd.setCursor(0, 1); // السطر الثاني
                lcd.print("T:");
                lcd.print(remaining);
                lcd.print("s ");
                lcd.print(" R:");

                lcd.print(digitalRead(RELAY_PIN) ? "  ON " : "  OFF");
            }
            else
            {
                checkCountdown();
            }
        }
        else
        {
            // عرض التيار والجهد في السطر الأول
            lcd.setCursor(0, 0);
            lcd.print("V:");
            lcd.print(voltage, 1);
            lcd.print(" P:");
            lcd.print(power, 1);

            lcd.setCursor(0, 1);
            lcd.print("C:");
            lcd.print(current, 2);
            lcd.print(" R:");
            lcd.print(digitalRead(RELAY_PIN) ? "ON " : "OFF");
        }
    }

    if (power > powerLimit && !hasTripped)
    {
        digitalWrite(RELAY_PIN, LOW);
        digitalWrite(BUZZER_PIN, HIGH);
        digitalWrite(LED_PIN, HIGH);
        delay(5000);
        digitalWrite(BUZZER_PIN, LOW);
        digitalWrite(LED_PIN, LOW);
        hasTripped = true;

        if (WiFi.status() == WL_CONNECTED)
        {
            HTTPClient http;
            http.begin(String(baseURL) + "/control");
            http.addHeader("Content-Type", "application/json");
            String cmdPayload = "{\"command\":\"off\"}";
            int code = http.POST(cmdPayload);
            http.end();
        }
    }

    if (power <= powerLimit && hasTripped)
    {
        hasTripped = false;
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
