#include <WiFi.h>
#include <HTTPClient.h>
#include <PZEM004Tv30.h>
#include <ArduinoJson.h>
#include <WiFiManager.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

const char *baseURL = "http://192.168.1.6:5000";

String deviceName = "";
String command = "";
float powerLimit = 100;
unsigned long countdownStart = 0;
unsigned long countdownDuration = 0;
bool countdownActive = false;
bool relayOpened = false;
bool hasTripped = false;

// متغير عشان نعرف الحالة اتغيرت ولا لأ (لمنع رعشة الشاشة)
int lastSystemState = -1; 

#define PZEM_RX_PIN 16
#define PZEM_TX_PIN 17
#define RELAY_PIN 5
#define BUZZER_PIN 14
#define LED_PIN 12
#define RESET_BUTTON_PIN 4

PZEM004Tv30 pzem(Serial2, PZEM_RX_PIN, PZEM_TX_PIN);
LiquidCrystal_I2C lcd(0x27, 16, 2); 

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
        WiFiManager wm;
        wm.resetSettings();
        ESP.restart();
    }

    Serial2.begin(9600, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
    pinMode(RELAY_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, HIGH); // الافتراضي شغال
    
    WiFiManager wm;
    if (!wm.autoConnect("Y & M Setup")) {
        ESP.restart();
    }
    
    // جلب اسم الجهاز
    HTTPClient http;
    http.begin(String(baseURL) + "/get_device");
    if (http.GET() == 200) {
        String payload = http.getString();
        StaticJsonDocument<200> doc;
        if (!deserializeJson(doc, payload)) {
            deviceName = doc["device"].as<String>();
        }
    }
    http.end();
}

void getControllimit()
{
    if (WiFi.status() == WL_CONNECTED)
    {
        HTTPClient http;
        http.begin(String(baseURL) + "/esp_limit");
        if (http.GET() == 200) {
            StaticJsonDocument<200> doc;
            deserializeJson(doc, http.getString());
            float val = doc["power_limit"] | doc["limit"] | 0.0;
            if (val > 1.0) powerLimit = val;
        }
        http.end();
    }
}

void getControlCommand()
{
    if (WiFi.status() == WL_CONNECTED)
    {
        HTTPClient http;
        http.begin(String(baseURL) + "/control"); // ده بيرجع الحالة المسجلة في السيرفر
        if (http.GET() == 200) {
            StaticJsonDocument<200> doc;
            deserializeJson(doc, http.getString());
            // ملحوظة: مش هنحدث المتغير command هنا لو التايمر خلصان في نفس اللفة
            // سيب التحديث لآخر اللوب
            String serverCmd = doc["command"].as<String>();
            
            // لو التايمر شغال أو السيستم طبيعي، اقبل أمر السيرفر
            if (!countdownActive && !hasTripped) {
                command = serverCmd;
            }
        }
        http.end();
    }
}

// دالة التايمر المعدلة (الأهم)
void getCountdownFromServer()
{
    if (WiFi.status() == WL_CONNECTED)
    {
        HTTPClient http;
        http.begin(String(baseURL) + "/get_timer");
        if (http.GET() == 200)
        {
            StaticJsonDocument<200> doc;
            deserializeJson(doc, http.getString());
            
            int remainingSeconds = doc["remaining_seconds"];
            bool isServerPaused = doc["paused"]; 

            // 1. لو معمول Pause
            if (isServerPaused) {
                countdownActive = false;
                command = "off"; // اجبار الفصل
            }
            // 2. لو شغال
            else if (remainingSeconds > 0) {
                if (!countdownActive) {
                    countdownDuration = remainingSeconds * 1000UL;
                    countdownStart = millis();
                    countdownActive = true;
                    command = "on"; // اجبار التشغيل
                }
                // Sync
                long diff = (long)((countdownDuration - (millis() - countdownStart))/1000) - remainingSeconds;
                if (abs(diff) > 2) {
                     countdownDuration = remainingSeconds * 1000UL;
                     countdownStart = millis();
                }
            }
            // 3. لو خلص (صفر)
            else {
                countdownActive = false;
                // هنا مش بنعمل حاجة، بنسيب checkCountdown تتصرف
            }
        }
        http.end();
    }
}

// الدالة اللي بتخلص التايمر وتحدث السيرفر
void checkCountdown()
{
    if (countdownActive)
    {
        if (millis() - countdownStart >= countdownDuration)
        {
            // 1. وقف التايمر وافصل محلياً
            countdownActive = false;
            command = "off"; 
            digitalWrite(RELAY_PIN, LOW); 

            // 2. بلغ السيرفر فوراً (عشان يحدث نفسه لـ OFF)
            if (WiFi.status() == WL_CONNECTED) {
                HTTPClient http;
                http.begin(String(baseURL) + "/set_command");
                http.addHeader("Content-Type", "application/json");
                http.POST("{\"command\":\"off\"}"); // دي الخطوة اللي كانت ناقصة تزامن
                http.end();
                Serial.println("Timer Ended -> Server Updated to OFF");
            }
        }
    }
}

void applyCommand()
{
    // تنفيذ الأمر المخزن في المتغير command
    if (command == "on" && !hasTripped) {
        digitalWrite(RELAY_PIN, HIGH);
    } else {
        digitalWrite(RELAY_PIN, LOW);
    }
}

void loop()
{
    getControllimit();

    // قراءات الحساس
    float v = pzem.voltage(); if(isnan(v)) v = 0.0;
    float i = pzem.current(); if(isnan(i)) i = 0.0;
    float p = pzem.power();   if(isnan(p)) p = 0.0;
    float e = pzem.energy();  if(isnan(e)) e = 0.0;
    float f = pzem.frequency(); if(isnan(f)) f = 0.0;
    float pf = pzem.pf(); if(isnan(pf)) pf = 0.0;

    // --- منطق التحكم (بالترتيب) ---
    
    // 1. هات حالة السيرفر (مبدئياً)
    getControlCommand(); 
    
    // 2. شوف التايمر (ممكن يغير رأي السيرفر لو فيه Pause)
    getCountdownFromServer();

    // 3. شوف هل التايمر خلص؟ (لو خلص هيبعت للسيرفر OFF ويغير المتغير المحلي)
    checkCountdown();

    // 4. الحماية (أقوى حاجة)
    if (p > powerLimit && !hasTripped) {
        command = "off";
        hasTripped = true;
        // نبلغ السيرفر
        if (WiFi.status() == WL_CONNECTED) {
            HTTPClient http;
            http.begin(String(baseURL) + "/set_command");
            http.addHeader("Content-Type", "application/json");
            http.POST("{\"command\":\"off\"}");
            http.end();
        }
    }
    if (p <= powerLimit && hasTripped) hasTripped = false;


    // --- تحديث الشاشة (بدون رعشة) ---
    
    // تحديد رقم الحالة الحالية
    int currentState = 0; 
    if (hasTripped) currentState = 1;
    else if (command == "off") currentState = 2;
    else if (countdownActive && digitalRead(RELAY_PIN) == LOW) currentState = 3; // Paused logic check
    
    if (currentState != lastSystemState) {
        lcd.clear();
        lastSystemState = currentState;
    }

    if (hasTripped) {
        lcd.setCursor(0, 0); lcd.print("LIMIT EXCEEDED  ");
        lcd.setCursor(0, 1); lcd.print("Relay OFF       ");
        digitalWrite(BUZZER_PIN, HIGH); digitalWrite(LED_PIN, HIGH);
    }
    else if (command == "off") {
        lcd.setCursor(0, 0); lcd.print("System Ready    ");
        lcd.setCursor(0, 1); lcd.print("Relay: OFF      ");
        digitalWrite(BUZZER_PIN, LOW); digitalWrite(LED_PIN, LOW);
    }
    else { // شغال (ON)
        lcd.setCursor(0, 0);
        lcd.print("V:"); lcd.print((int)v); lcd.print(" ");
        lcd.print("P:"); lcd.print((int)p); lcd.print("W   ");

        lcd.setCursor(0, 1);
        if (countdownActive) {
             unsigned long elapsed = millis() - countdownStart;
             long rem = (countdownDuration > elapsed) ? (countdownDuration - elapsed)/1000 : 0;
             lcd.print("T:"); lcd.print(rem); lcd.print("s ");
        } else {
             lcd.print("C:"); lcd.print(i, 2); lcd.print("A ");
        }
        lcd.print("L:"); lcd.print((int)powerLimit);

        digitalWrite(BUZZER_PIN, LOW); digitalWrite(LED_PIN, LOW);
    }

    // --- التنفيذ النهائي وإرسال الداتا ---
    applyCommand();

    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin(String(baseURL) + "/data");
        http.addHeader("Content-Type", "application/json");
        String payload = "{\"device\":\"" + deviceName + "\",\"voltage\":" + String(v, 1) + 
                         ",\"current\":" + String(i, 2) + ",\"power\":" + String(p, 1) + 
                         ",\"energy_consumption\":" + String(e, 3) + ",\"frequency\":" + String(f, 1) + 
                         ",\"power_factor\":" + String(pf, 2) + "}";
        http.POST(payload);
        http.end();
    }

    delay(1000);
}