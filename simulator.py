import requests
import time
import random

SERVER_URL = "http://127.0.0.1:5000/data"
ESP_ID = 62355

total_energy = 0.0
last_time = time.time()

print("Starting SENTRA ESP32 Realistic Simulator...")
print(f"Targeting: {SERVER_URL}")

kettle_active = False
kettle_timer = 0
fridge_active = True
fridge_timer = 0

while True:
    current_time = time.time()
    delta_time = current_time - last_time
    last_time = current_time

    fridge_timer += delta_time
    if fridge_active and fridge_timer > 60:
        fridge_active = False
        fridge_timer = 0
    elif not fridge_active and fridge_timer > 120:
        fridge_active = True
        fridge_timer = 0

    fridge_power = random.uniform(150.0, 180.0) if fridge_active else 0.0

    if not kettle_active and random.random() < 0.05:
        kettle_active = True
        kettle_timer = 0

    if kettle_active:
        kettle_timer += delta_time
        if kettle_timer > 45:
            kettle_active = False
    
    kettle_power = random.uniform(1800.0, 2200.0) if kettle_active else 0.0

    power = round(fridge_power + kettle_power, 1)
    
    if power > 0:
        voltage = round(random.uniform(218.0, 224.0), 1)
        pf = round(random.uniform(0.92, 0.98), 2)
        current = round(power / (voltage * pf), 2)
    else:
        voltage = round(random.uniform(218.0, 224.0), 1)
        pf = 0.0
        current = 0.0
        
    frequency = round(random.uniform(49.9, 50.1), 1)
    
    energy_increment = (power / 1000.0) * (delta_time / 3600.0)
    total_energy += energy_increment
    
    payload = {
        "espid": ESP_ID,
        "voltage": voltage,
        "current": current,
        "power": power,
        "energy": round(total_energy, 6),
        "frequency": frequency,
        "pf": pf,
        "device_name": "TOTAL (MAIN)",
        "ai_devices": "Fridge - Kettle",
    }

    try:
        response = requests.post(SERVER_URL, json=payload, timeout=2)
        if response.status_code == 200:
            res_data = response.json()
            server_command = res_data.get("command", "on")
            
            print(f"Sent -> V:{voltage} I:{current} P:{power}W E:{round(total_energy, 6)}kWh | Cmd: {server_command}")
            
            if server_command == "off":
                fridge_active = False
                kettle_active = False
        else:
            print(f"Error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Connection failed: {e}")

    time.sleep(3)