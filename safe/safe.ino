#include <WiFi.h>
#include <HTTPClient.h>
#include <PZEM004Tv30.h>
#include <ArduinoJson.h>
#include <WiFiManager.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Preferences.h>

const char *baseURL = "http://192.168.1.2:5000";

String command = "off";
String espid = "0"; 
Preferences preferences;

float currentLimit = 50.0;
unsigned long countdownStart = 0;
unsigned long countdownDuration = 0;
bool countdownActive = false;

bool hasTripped = false;
int lastSystemState = -1;
unsigned long lastPostTime = 0;
unsigned long lastScreenUpdate = 0;

unsigned long tripTime = 0;
bool alarmActive = false;

float v = 0.0, i = 0.0, p = 0.0, e = 0.0, f = 0.0, pf = 0.0;

#define PZEM_RX_PIN 16
#define PZEM_TX_PIN 17
#define RELAY_PIN 5
#define BUZZER_PIN 14
#define LED_PIN 12
#define RESET_BUTTON_PIN 4

PZEM004Tv30 pzem(Serial2, PZEM_RX_PIN, PZEM_TX_PIN);
LiquidCrystal_I2C lcd(0x27, 16, 2);

WiFiClient wifiClient; 

void setup()
{
    Serial.begin(115200);
    delay(100);
    
    Serial.println("\n\n=================================");
    Serial.println("[SYSTEM] Sentra ESP32 Booting...");
    Serial.println("=================================");

    preferences.begin("sentra", false);
    espid = preferences.getString("espid", "0");
    Serial.println("[MEMORY] Loaded ESP ID: " + espid);

    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    lcd.print("System Booting...");
    delay(2000);
    
    pinMode(RESET_BUTTON_PIN, INPUT_PULLUP);

    WiFiManager wm;
    WiFiManagerParameter custom_espid("espid", "Enter ESP ID", espid.c_str(), 10);
    wm.addParameter(&custom_espid);

    if (digitalRead(RESET_BUTTON_PIN) == LOW)
    {
        Serial.println("[SYSTEM] Reset button pressed. Clearing memory...");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Resetting Memory");
        wm.resetSettings();
        preferences.clear();
        delay(1500);
        Serial.println("[SYSTEM] Memory cleared. Restarting...");
        ESP.restart();
    }

    Serial2.begin(9600, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
    pinMode(RELAY_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_PIN, OUTPUT);
    
    digitalWrite(RELAY_PIN, LOW); 
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(LED_PIN, LOW);

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Connecting WiFi.");
    lcd.setCursor(0, 1);
    lcd.print("AP: ESP Setup   ");
    
    Serial.println("[WIFI] Attempting to connect to saved network...");

    if (!wm.autoConnect("ESP Setup")) {
        Serial.println("[WIFI] Failed to connect. Restarting...");
        ESP.restart();
    }
    
    Serial.println("[WIFI] Connected Successfully!");
    Serial.print("[WIFI] IP Address: ");
    Serial.println(WiFi.localIP());

    String new_id = String(custom_espid.getValue());
    if (new_id != "" && new_id != espid) {
        espid = new_id;
        preferences.putString("espid", espid);
        Serial.println("[MEMORY] Saved new ESP ID: " + espid);
    }
    
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Connected!");
    delay(1000);
    lcd.clear();
}

void checkCountdown()
{
    if (countdownActive)
    {
        if (millis() - countdownStart >= countdownDuration)
        {
            countdownActive = false;
            command = "off"; 
            digitalWrite(RELAY_PIN, LOW); 
            Serial.println("[TIMER] Countdown finished. Relay turned OFF.");

            if (WiFi.status() == WL_CONNECTED) {
                HTTPClient http;
                http.begin(wifiClient, String(baseURL) + "/set_command");
                http.addHeader("Content-Type", "application/json");
                http.POST("{\"command\":\"off\", \"espid\":" + espid + "}"); 
                http.end();
                Serial.println("[HTTP] Server notified of timer completion.");
            }
        }
    }
}

void applyCommand()
{
    if (command == "on" && !hasTripped) {
        digitalWrite(RELAY_PIN, HIGH); 
    } else {
        digitalWrite(RELAY_PIN, LOW);  
    }
}

void loop()
{
    checkCountdown();
    
    if (alarmActive && (millis() - tripTime >= 5000)) {
        alarmActive = false;
        digitalWrite(BUZZER_PIN, LOW);
        digitalWrite(LED_PIN, LOW);
        Serial.println("[ALERT] 5 seconds passed. Buzzer and LED turned OFF.");
    }
    
    if (millis() - lastScreenUpdate >= 1000) {
        v = pzem.voltage(); if(isnan(v)) v = 0.0;
        i = pzem.current(); if(isnan(i)) i = 0.0;
        p = pzem.power();   if(isnan(p)) p = 0.0;
        e = pzem.energy();  if(isnan(e)) e = 0.0;
        
        f = pzem.frequency(); if(isnan(f)) f = 0.0;
        pf = pzem.pf(); if(isnan(pf)) pf = 0.0;

        if (i > currentLimit && !hasTripped) {
            command = "off";
            hasTripped = true;
            
            alarmActive = true;
            tripTime = millis();
            digitalWrite(BUZZER_PIN, HIGH);
            digitalWrite(LED_PIN, HIGH);
            
            Serial.println("\n[ALERT] OVERCURRENT TRIPPED!");
            Serial.print("[ALERT] Current: "); Serial.print(i);
            Serial.print("A > Limit: "); Serial.println(currentLimit);
            
            if (WiFi.status() == WL_CONNECTED) {
                HTTPClient http;
                http.begin(wifiClient, String(baseURL) + "/set_command");
                http.addHeader("Content-Type", "application/json");
                http.POST("{\"command\":\"off\", \"espid\":" + espid + "}");
                http.end();
                Serial.println("[HTTP] Server notified of overcurrent trip.");
            }
        }
        
        if (i <= currentLimit && hasTripped) {
            hasTripped = false;
            alarmActive = false;
            digitalWrite(BUZZER_PIN, LOW);
            digitalWrite(LED_PIN, LOW);
            Serial.println("[ALERT] Current normalized. Trip cleared.");
        }
        
        int currentState = 0;
        if (hasTripped) currentState = 1;
        else if (command == "off") currentState = 2;
        else if (countdownActive && digitalRead(RELAY_PIN) == HIGH) currentState = 3;

        if (currentState != lastSystemState) {
            lcd.clear();
            lastSystemState = currentState;
        }

        if (hasTripped) {
            lcd.setCursor(0, 0);
            lcd.print("LIMIT EXCEEDED  ");
            lcd.setCursor(0, 1); lcd.print("Relay OFF       ");
        }
        else if (command == "off") {
            lcd.setCursor(0, 0);
            lcd.print("System Ready    ");
            lcd.setCursor(0, 1); lcd.print("Relay: OFF      ");
            digitalWrite(BUZZER_PIN, LOW); 
            digitalWrite(LED_PIN, LOW);
        }
        else { 
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
            
            lcd.print("L:"); lcd.print(currentLimit, 1); lcd.print("A");
            digitalWrite(BUZZER_PIN, LOW); 
            digitalWrite(LED_PIN, LOW);
        }
        
        lastScreenUpdate = millis();
    }

    applyCommand();
    
    if (millis() - lastPostTime >= 2000) {
        
        Serial.print("[SENSOR] V: "); Serial.print(v);
        Serial.print("V | I: "); Serial.print(i);
        Serial.print("A | P: "); Serial.print(p);
        Serial.print("W | L: "); Serial.print(currentLimit);
        Serial.print("A | Cmd: "); Serial.println(command);

        if (WiFi.status() == WL_CONNECTED) {
            HTTPClient http;
            http.begin(wifiClient, String(baseURL) + "/data");
            http.addHeader("Content-Type", "application/json");
            
            String payload = "{\"espid\":" + espid + 
                             ",\"voltage\":" + String(v, 1) + 
                             ",\"current\":" + String(i, 2) + 
                             ",\"power\":" + String(p, 1) + 
                             ",\"energy\":" + String(e, 3) + 
                             ",\"frequency\":" + String(f, 1) + 
                             ",\"pf\":" + String(pf, 2) + "}";
                             
            int httpCode = http.POST(payload);
            
            if(httpCode == 200) {
                String responsePayload = http.getString();
                StaticJsonDocument<256> doc;
                DeserializationError error = deserializeJson(doc, responsePayload);
                
                if (!error) {
                    String serverCmd = doc["command"] | "off";
                    if(serverCmd == "off" || hasTripped) {
                         command = "off";
                         countdownActive = false;
                    } else {
                         command = serverCmd;
                    }

                    float srvLimit = doc["current_limit"] | 0.0;
                    if (srvLimit > 0) currentLimit = srvLimit;

                    int remainingSeconds = doc["timer"] | 0;
                    if (remainingSeconds > 0) {
                        countdownDuration = remainingSeconds * 1000UL;
                        if(!countdownActive) countdownStart = millis(); 
                        countdownActive = true;
                        
                        long diff = (long)((countdownDuration - (millis() - countdownStart))/1000) - remainingSeconds;
                        if (abs(diff) > 2) {
                             countdownStart = millis();
                        }
                    } else {
                        countdownActive = false;
                    }
                } else {
                    Serial.println("[HTTP] JSON Parsing Error!");
                }
            } else {
                Serial.print("[HTTP] POST Failed. Error Code: ");
                Serial.println(httpCode);
            }
            http.end();
        } else {
            Serial.println("[WIFI] Connection Lost!");
        }
        lastPostTime = millis();
    }
    delay(50);
}