#include <WiFi.h>
#include <HTTPClient.h>
#include <PZEM004Tv30.h>
#include <ArduinoJson.h>
#include <WiFiManager.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Preferences.h>

#define SCREEN_WIDTH 128 
#define SCREEN_HEIGHT 64 
#define OLED_RESET    -1 
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Custom I2C Pins
#define SDA_PIN 27
#define SCK_PIN 2

// PZEM Pins
#define PZEM_RX_PIN 16
#define PZEM_TX_PIN 17

PZEM004Tv30 pzem(Serial2, PZEM_RX_PIN, PZEM_TX_PIN);
WiFiClient wifiClient; 
Preferences preferences;

// const char *baseURL = "http://192.168.1.7:5000";
const char *baseURL = "http://192.168.137.1:5000";
String espid = "0";

float v = 0.0, i = 0.0, p = 0.0, e = 0.0, f = 0.0, pf = 0.0;
unsigned long lastPostTime = 0;
unsigned long lastScreenUpdate = 0;

void setup()
{
    Serial.begin(115200);
    delay(100);
    
    // Initialize I2C with custom pins
    Wire.begin(SDA_PIN, SCK_PIN);

    // Initialize OLED Display
    if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { 
        Serial.println("OLED connection failed");
        for(;;); 
    }

    display.clearDisplay();
    display.setTextSize(1);      
    display.setTextColor(SSD1306_WHITE); 
    display.setCursor(0, 0);     
    display.println("System Booting...");
    display.display();
    delay(1500);

    // Initialize Preferences
    preferences.begin("sentra", false);
    espid = preferences.getString("espid", "0");

    Serial2.begin(9600, SERIAL_8N1, PZEM_RX_PIN, PZEM_TX_PIN);
    
    // WiFiManager Setup
    WiFiManager wm;
    WiFiManagerParameter custom_espid("espid", "Enter ESP ID", espid.c_str(), 10);
    wm.addParameter(&custom_espid);
    
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("Connecting WiFi...");
    display.println("AP: ESP Setup Maine ");
    display.display();
    
    if (!wm.autoConnect("ESP Setup Maine")) {
        Serial.println("Failed to connect. Restarting...");
        ESP.restart();
    }
    
    // Save New ESP ID if changed
    String new_id = String(custom_espid.getValue());
    if (new_id != "" && new_id != espid) {
        espid = new_id;
        preferences.putString("espid", espid);
    }
    
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("WiFi Connected!");
    display.display();
    delay(1500);
}

void loop()
{
    // Read Sensor Data
    float temp_v = pzem.voltage();
    if(!isnan(temp_v)) v = temp_v;
    
    float temp_i = pzem.current();
    if(!isnan(temp_i)) i = temp_i;
    
    float temp_p = pzem.power();
    if(!isnan(temp_p)) p = temp_p;
    
    e = pzem.energy();    if(isnan(e)) e = 0.0;
    f = pzem.frequency(); if(isnan(f)) f = 0.0;
    pf = pzem.pf();       if(isnan(pf)) pf = 0.0;
    
    // Update OLED Screen (Every 1 Second)
    if (millis() - lastScreenUpdate >= 1000) {
        display.clearDisplay();
        display.setTextSize(2); // Same font size for all readings
        display.setTextColor(SSD1306_WHITE);
        
        // Voltage Line
        display.setCursor(0, 0);
        display.print("V: "); 
        display.print(v, 1); 
        display.print(" V");
        
        // Current Line
        display.setCursor(0, 22);
        display.print("I: "); 
        display.print(i, 2); 
        display.print(" A");
        
        // Power Line
        display.setCursor(0, 44);
        display.print("P: "); 
        display.print(p, 1); 
        display.print(" W");
        
        display.display();
        lastScreenUpdate = millis();
    }
    
    // HTTP POST Data to Server (Every 2 Seconds)
    if (millis() - lastPostTime >= 2000) {
        if (WiFi.status() == WL_CONNECTED) {
            HTTPClient http;
            http.begin(wifiClient, String(baseURL) + "/data");
            http.addHeader("Content-Type", "application/json");
            
            StaticJsonDocument<256> doc;
            doc["espid"] = espid.toInt();
            doc["voltage"] = v;
            doc["current"] = i;
            doc["power"] = p;
            doc["energy"] = e;
            doc["frequency"] = f;
            doc["pf"] = pf;
            
            String payload;
            serializeJson(doc, payload);
            
            int httpCode = http.POST(payload);
            if(httpCode == 200) {
                String responsePayload = http.getString();
                StaticJsonDocument<256> responseDoc;
                DeserializationError error = deserializeJson(responseDoc, responsePayload);
                if (!error) {
                    // Handled server commands can be added here if needed
                }
            }
            http.end();
        }
        lastPostTime = millis();
    }
    delay(50);
}