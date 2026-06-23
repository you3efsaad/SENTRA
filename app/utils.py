from datetime import datetime
import app.globals as g
from dateutil import parser
# Creates and stores a new notification in the database with the appropriate device name.
# Change this line:
def create_notification(user_id, title, message, type='info', espid=None):
    try:
        if not user_id or len(str(user_id)) < 10 or str(user_id) == "0":
            return
            
        if g.esps.get(espid, {}).get("is_main", False):
            return
            
        device_name = f"ESP {espid}"
        
        if g.supabase:
            try:
                dev_res = g.supabase.table("safe_power_devices").select("device_name").eq("espid", espid).execute()
                if dev_res.data:
                    device_name = str(dev_res.data[0]["device_name"]).upper()
            except Exception:
                pass
                
        prefix = f"ESP {espid}"
        if title.startswith(prefix):
            title = title.replace(prefix, device_name)

        data = {
            "user_id": str(user_id),
            "title": str(title),
            "message": str(message),
            "type": str(type),
            "espid": int(espid)
        }
        g.supabase.table("notifications").insert(data).execute()
        print(f"[Notification] {title} created.")
    except Exception as e:
        print(f"[Error] Failed to create notification: {e}")
        
# Checks if a specific device's power consumption exceeds its predefined normal operating range.
def check_device_power_range(user_id, espid, device_name, power, esp_state):
    DEVICE_MAX_POWER = {
        "fridge": 600.0,
        "washing machine": 3500.0,
        "kettle": 3200.0,
        "microwave": 2000.0,
        "tv": 400.0,
        "iron": 2500.0,
        "ac": 4000.0,
        "heater": 3000.0,
        "fan": 150.0,
        "router": 50.0
    }

    if esp_state.get("is_main", False) or not device_name or device_name.lower() == "idle":
        return

    dev_key = device_name.lower()
    limit = None

    for key, val in DEVICE_MAX_POWER.items():
        if key in dev_key:
            limit = val
            break

    if limit is None:
        limit = float(esp_state["control"].get('power_limit', 3000.0))

    flag_key = f"flag_overload_{espid}"

    if power > limit:
        esp_state["control"]["latest_command"] = 'off'
        if not esp_state["settings"].get(flag_key, False):
            
            esp_state["settings"][flag_key] = True
    else:
        esp_state["settings"][flag_key] = False

# Continuously monitors all connected ESP devices for conditions, limits, and anomalies.
# Continuously monitors all connected ESP devices for conditions, limits, and anomalies.
def monitor_background_logic():
    try:
        for espid, esp in list(g.esps.items()):
            
            if esp["timer"]["end_time"]:
                now = datetime.now()
                if now >= esp["timer"]["end_time"]:
                    if not esp.get("is_main", False):  
                        esp["control"]["latest_command"] = 'off'
                    esp["timer"]["end_time"] = None
                    esp["timer"]["paused_remaining"] = None

            if (datetime.now() - esp["last_update_time"]).total_seconds() > 30:
                for key in ['voltage', 'current', 'power', 'frequency', 'pf']:
                    esp["data"][key] = 0

            user_id = esp["data"].get('user_id')
            
            if user_id and len(str(user_id)) > 10 and g.supabase:
                try:
                    user_check = g.supabase.table("users").select("id").eq("id", str(user_id)).execute()
                    if not user_check.data:
                        user_id = None
                        esp["data"]["user_id"] = None
                except Exception:
                    pass

            if not user_id or len(str(user_id)) < 10 or str(user_id) == "0":
                user_id = None
            
            # Fetch user_id from database if missing
            if not user_id and g.supabase:
                try:
                    user_res = g.supabase.table("safe_power_devices").select("user_id").eq("espid", espid).execute()
                    if user_res.data:
                        user_id = user_res.data[0]['user_id']
                        esp["data"]["user_id"] = user_id
                except Exception as e:
                    print(f"Background monitor failed to resolve user_id: {e}")

            if not user_id or len(str(user_id)) < 10 or str(user_id) == "0":
                continue

            if not esp["settings"].get('settings_loaded_from_db', False):
                try:
                    settings_res = g.supabase.table("user_settings").select("*").eq("user_id", user_id).eq("espid", espid).execute()
                    if settings_res.data:
                        esp["control"]["current_limit"] = float(settings_res.data[0].get('current_limit', 50.0))
                        
                        if esp["settings"].get('budget_kwh', 0.0) == 0.0:
                            esp["settings"]["budget_kwh"] = float(settings_res.data[0].get('budget_kwh', 0.0))
                            esp["settings"]["consumed_since_budget"] = float(settings_res.data[0].get('consumed_since_budget', 0.0))
                            esp["settings"]["budget_start_time"] = settings_res.data[0].get('budget_start_time')
                    
                    esp["settings"]['settings_loaded_from_db'] = True
                except Exception:
                    pass
            
            voltage = float(esp["data"].get('voltage', 0))
            max_v = float(esp["settings"].get('max_voltage', 250.0))
            min_v = float(esp["settings"].get('min_voltage', 190.0))

            if voltage > max_v:
                if not esp.get("is_main", False):
                    esp["control"]["latest_command"] = 'off'
                    
                if not esp["settings"].get('flag_high_voltage', False):
                    create_notification(
                        user_id, 
                        f"ESP {espid} - HIGH VOLTAGE", 
                        f"Voltage spiked to {voltage}V! Exceeds maximum limit of {max_v}V.", 
                        "error", 
                        espid
                    )
                    esp["settings"]['flag_high_voltage'] = True
                    
            elif 0 < voltage < min_v: 
                if not esp.get("is_main", False):
                    esp["control"]["latest_command"] = 'off'
                    
                if not esp["settings"].get('flag_low_voltage', False):
                    create_notification(
                        user_id, 
                        f"ESP {espid} - LOW VOLTAGE", 
                        f"Voltage dropped to {voltage}V! Below minimum limit of {min_v}V.", 
                        "maintenance", 
                        espid
                    )
                    esp["settings"]['flag_low_voltage'] = True
            else:
                esp["settings"]['flag_high_voltage'] = False
                esp["settings"]['flag_low_voltage'] = False

            if not esp.get("is_main", False):
                current = float(esp["data"].get('current', 0))
                c_limit = float(esp["control"].get('current_limit', 100))
                if current > c_limit:
                    esp["control"]["latest_command"] = 'off'
                    if not esp["settings"].get('flag_current_limit', False):
                        create_notification(user_id, f"ESP {espid} - CURRENT LIMIT", f"Amperage reached {current}A.", "error", espid)
                        esp["settings"]['flag_current_limit'] = True
                else:
                    esp["settings"]['flag_current_limit'] = False

            power = float(esp["data"].get('power', 0))
            device_name = str(esp["data"].get('ac_device_name', 'Idle'))
            
            if esp.get("is_main", False):
                pass 
            else:
                check_device_power_range(user_id, espid, device_name, power, esp)

            if not esp.get("is_main", False):
                budget_kwh = float(esp["settings"].get('budget_kwh', 0))
                consumed = float(esp["settings"].get('consumed_since_budget', 0))
                
                if budget_kwh > 0:
                    start_time = esp["settings"].get("budget_start_time")
                    days = int(esp["settings"].get("budget_days", 0))
                    
                    if start_time and days > 0:
                        if isinstance(start_time, str):
                            try:
                                start_time = parser.parse(start_time).replace(tzinfo=None)
                            except Exception:
                                start_time = datetime.now()
                                
                        elapsed_seconds = (datetime.now() - start_time).total_seconds()
                        if elapsed_seconds >= (days * 86400):
                            esp["settings"]["budget_kwh"] = 0.0
                            esp["settings"]["consumed_since_budget"] = 0.0
                            esp["settings"]["budget_locked"] = False
                            esp["settings"]["flag_budget_100"] = False
                            
                            if g.supabase and user_id:
                                try:
                                    g.supabase.table("user_settings").update({
                                        "budget_kwh": 0,
                                        "budget_duration_days": 0
                                    }).eq("user_id", user_id).eq("espid", espid).execute()
                                except Exception as e:
                                    print(f"Failed to clear budget in DB for {espid}: {e}")
                            
                            continue 

                    percent = (consumed / budget_kwh) * 100
                    
                    if 50 <= percent < 75:
                        if not esp["settings"].get('flag_budget_50', False):
                            create_notification(user_id, f"ESP {espid} - BUDGET ALERT", "50% budget used.", "info", espid)
                            esp["settings"]['flag_budget_50'] = True
                    elif 75 <= percent < 99:
                        if not esp["settings"].get('flag_budget_75', False):
                            create_notification(user_id, f"ESP {espid} - BUDGET WARNING", "75% budget used.", "maintenance", espid)
                            esp["settings"]['flag_budget_75'] = True
                    elif percent >= 99:
                        if not esp["settings"].get('flag_budget_100', False):
                            create_notification(user_id, f"ESP {espid} - BUDGET EXCEEDED", "100% budget reached.", "error", espid)
                            esp["settings"]['flag_budget_100'] = True
                            
                            esp["settings"]["budget_kwh"] = 0.0
                            esp["settings"]["consumed_since_budget"] = 0.0
                            
                            if g.supabase and user_id:
                                try:
                                    g.supabase.table("user_settings").update({
                                        "budget_kwh": 0,
                                        "consumed_since_budget": 0
                                    }).eq("user_id", user_id).eq("espid", espid).execute()
                                except Exception as e:
                                    print(f"Failed to clear budget in DB for {espid}: {e}")

    except Exception as e:
        print(f"DEBUG: Monitor Logic Error: {e}")

# Saves the current main meter readings to the database as an hourly snapshot.
def save_hourly_snapshot():
    try:
        if g.supabase:
            for eid, esp_data in list(g.esps.items()):
                if esp_data.get("is_main", False):
                    main_data = esp_data["data"]
                    user_id = main_data.get("user_id")
                    
                    if user_id and (main_data.get('power', 0) > 0 or main_data.get('energy', 0) > 0):
                        data = {
                            "user_id": user_id,
                            "espid": eid,
                            "Timestamp": datetime.now().isoformat(),
                            "Voltage(V)": float(main_data.get('voltage', 0)),
                            "Current(A)": float(main_data.get('current', 0)),
                            "Power(W)": float(main_data.get('power', 0)),
                            "Energy Consumption(kWh)": float(main_data.get('energy', 0)),
                            "Frequency(Hz)": float(main_data.get('frequency', 0)),
                            "Power Factor": float(main_data.get('pf', 0))
                        }
                        g.supabase.table("energy_usage_hourly").insert(data).execute()
                
                else:
                    user_id = esp_data["data"].get("user_id")
                    if user_id:
                        consumed = float(esp_data["settings"].get("consumed_since_budget", 0.0))
                        try:
                            g.supabase.table("user_settings").update({
                                "consumed_since_budget": consumed
                            }).eq("user_id", user_id).eq("espid", eid).execute()
                        except Exception as sub_e:
                            print(f"[Error] Failed to save budget for {eid}: {sub_e}")
                            
            print("[Snapshot] Hourly data and budget consumption saved.")
            
    except Exception as e:
        print(f"[Error] Snapshot failed: {e}")