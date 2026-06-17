import os
from flask import Blueprint, request, jsonify
import app.globals as g
from datetime import datetime
import google.generativeai as genai
from collections import defaultdict
from datetime import datetime, timedelta, timezone
# from app.ai_engine.core import SentraNILMEngine

api_bp = Blueprint('api', __name__)

# engine = SentraNILMEngine()

@api_bp.route('/api/process_nilm', methods=['POST'])
def process_nilm():
    data = request.json
    sequence = data.get('sequence', [0]*480) 
    
    # print("\n" + "="*50)
    # print(f"[AI ENGINE] Received new request.")
    # print(f"[AI ENGINE] Sequence length: {len(sequence)}")
    # if len(sequence) >= 5:
    #     print(f"[AI ENGINE] Sample data (first 5): {sequence[:5]}")
    
    # predictions = engine.predict_parallel(sequence)
    
    # print(f"[AI ENGINE] Prediction Results:")
    # for device, result in predictions.items():
    #     print(f"  -> {device.upper()}: Status={result['status']}, Power={result['power']}W")
    # print("="*50 + "\n")
    predictions = {}
    return jsonify({
        "status": "success",
        "data": predictions
    })

# ==========================================
# 1. Receive Data from ESP32 (The Heartbeat)
# ==========================================
@api_bp.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        if not data or "espid" not in data:
            return jsonify({"status": "error", "message": "Missing espid"}), 400

        espid = int(data["espid"])
        g.init_esp_state(espid)
        esp = g.esps[espid]

        new_power = float(data.get("power", 0))
        
        esp["power_buffer"].append(new_power)

        if g.ai_engine is not None and len(esp["power_buffer"]) == 480:
            predictions = g.ai_engine.predict_parallel(list(esp["power_buffer"]))
            
            detected_devices = [dev for dev, res in predictions.items() if res['status'] == 'ON']
            if detected_devices:
                esp["data"]["ai_device_name"] = ", ".join(detected_devices)
            else:
                esp["data"]["ai_device_name"] = "Idle"
        
        g.init_esp_state(espid)
        esp = g.esps[espid]

        new_energy = float(data.get("energy", 0))
        old_energy = float(esp["data"].get("energy", 0))
        
        if old_energy == 0 and new_energy > 0 and g.supabase:
            try:
                last_record = g.supabase.table("user_readings").select("energy_consumption").eq("espid", espid).order("timestamp", desc=True).limit(1).execute()
                if last_record.data and len(last_record.data) > 0:
                    old_energy = float(last_record.data[0]["energy_consumption"])
            except Exception:
                pass

        if old_energy > 0 and new_energy >= old_energy:
            current_consumed = esp["settings"].get('consumed_since_budget', 0.0)
            increment = new_energy - old_energy
            esp["settings"]["consumed_since_budget"] = current_consumed + increment

        esp["data"]["voltage"] = float(data.get("voltage", 0))
        esp["data"]["current"] = float(data.get("current", 0))
        esp["data"]["power"] = float(data.get("power", 0))
        esp["data"]["energy"] = new_energy
        esp["data"]["frequency"] = float(data.get("frequency", 0))
        esp["data"]["pf"] = float(data.get("pf", 0))

        if "device_name" in data and data["device_name"]:
            esp["data"]["ac_device_name"] = data["device_name"]

        if ("device_db_id" not in esp["data"] or esp["data"]["user_id"] is None) and g.supabase:
            try:
                dev_res = g.supabase.table("safe_power_devices").select("id, user_id, device_name, is_main").eq("espid", espid).execute()
                if dev_res.data:
                    esp["data"]["user_id"] = dev_res.data[0]['user_id']
                    
                    if "ac_device_name" not in esp["data"] or not esp["data"]["ac_device_name"]:
                        esp["data"]["ac_device_name"] = dev_res.data[0]['device_name']
                        
                    esp["data"]["device_db_id"] = dev_res.data[0]['id']
                    esp["is_main"] = dev_res.data[0].get('is_main', False) 
                else:
                    return jsonify({"status": "error", "message": "Unregistered ESP"}), 401
            except Exception:
                pass

        if "ac_device_name" not in esp["data"] or not esp["data"]["ac_device_name"]:
            esp["data"]["ac_device_name"] = "Unknown Device"

        esp["last_update_time"] = datetime.now()

        user_id = esp["data"].get("user_id")

        if user_id:
            try:
                now = datetime.now()
                last_insert = esp.get("last_db_insert_time")
                
                # Update the threshold from 120 to 8 seconds
                if not last_insert or (now - last_insert).total_seconds() >= 8:
                    db_device_name = esp["data"]["ai_device_name"] if esp.get("is_main", False) and "ai_device_name" in esp["data"] else esp["data"]["ac_device_name"]
                    
                    g.supabase.table("user_readings").insert({
                        "user_id": user_id,
                        "espid": espid,
                        "voltage": esp["data"]["voltage"],
                        "current": esp["data"]["current"],
                        "power": esp["data"]["power"],
                        "energy_consumption": esp["data"]["energy"],
                        "frequency": esp["data"]["frequency"],
                        "pf": esp["data"]["pf"], 
                        "device_name": db_device_name,
                        "timestamp": now.isoformat()
                    }).execute()
                    
                    esp["last_db_insert_time"] = now
            except Exception:
                pass

        remaining_time = 0
        if esp["timer"]["end_time"]:
            now = datetime.now()
            if now < esp["timer"]["end_time"]:
                remaining_time = int((esp["timer"]["end_time"] - now).total_seconds())
            else:
                remaining_time = 0
                esp["timer"]["end_time"] = None
                if esp["control"].get("latest_command", "off") == "on":
                    esp["control"]["latest_command"] = "off"

        response = {
            "status": "success",
            "command": esp["control"].get("latest_command", "off"),
            "current_limit": esp["control"].get("current_limit", 0),
            "timer": remaining_time
        }
        
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/get_device', methods=['GET'])
def get_device():
    espid = request.args.get('espid', type=int)
    
    # Return Idle if no espid is provided
    if not espid:
        return jsonify({"device": "Idle"})
        
    if g.supabase:
        try:
            # Fetch device name from safe_power_devices
            res = g.supabase.table("safe_power_devices").select("device_name").eq("espid", espid).execute()
            if res.data:
                return jsonify({"device": res.data[0]["device_name"]})
        except Exception as e:
            print(f"Database error while fetching device name: {e}")
            
    return jsonify({"device": "Idle"}) 
# ==========================================
# 2. Update WiFi Config
# ==========================================
@api_bp.route('/api/wifi-config', methods=['POST'])
def update_wifi_config():
    try:
        data = request.json
        new_ssid = data.get('ssid')
        new_pass = data.get('password')
        
        # Save to Globals for ESP32 to pick up
        g.pending_wifi_config = {
            "ssid": new_ssid,
            "password": new_pass
        }
        
        print(f"[📡] New WiFi Config Received: SSID={new_ssid}")
        return jsonify({"status": "success", "message": "Config saved and waiting for ESP"})
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
# ==========================================
# 3. Emergency Trip / Control Sync
# ==========================================
@api_bp.route('/control', methods=['GET', 'POST'])
@api_bp.route('/esp_command', methods=['GET', 'POST'])
@api_bp.route('/set_command', methods=['POST']) 
def control_device():
    data = request.get_json(silent=True) or {}
    
    espid_raw = request.args.get('espid') or data.get('espid')
    
    if not espid_raw or espid_raw in ['0', 'null', 'undefined', 0]:
        return jsonify({"command": "off"}), 400
        
    try:
        espid = int(espid_raw)
    except (ValueError, TypeError):
        return jsonify({"command": "off"}), 400
    
    if hasattr(g, 'esps') and espid in g.esps:
        esp_settings = g.esps[espid]["settings"]
        
        if request.method == 'POST' and 'command' in data:
            cmd = data['command']
            g.esps[espid]["control"]["latest_command"] = cmd
            
            if cmd == "off":
                esp_settings["manual_locked"] = True
                g.esps[espid]["timer"]["end_time"] = None
            elif cmd == "on":
                esp_settings["manual_locked"] = False
                
        is_locked = esp_settings.get("manual_locked", False)
        
        return jsonify({
            "command": g.esps[espid]["control"].get("latest_command", "off"),
            "locked": is_locked
        })
        
    return jsonify({"command": "off", "locked": False})


# ==========================================
# ANALYTICS DATA ENDPOINTS (API)
# ==========================================

def get_working_model():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                return genai.GenerativeModel(m.name)
    except Exception:
        pass
    return genai.GenerativeModel('gemini-1.5-flash')

gemini_model = get_working_model()

@api_bp.route('/api/readings/history', methods=['GET'])
def get_historical_readings():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    user_id = request.args.get('user_id')

    if not start_date or not end_date:
        return jsonify({"error": "Start and end dates are required"}), 400

    try:
        query = g.supabase.table('user_readings') \
            .select('*') \
            .gte('timestamp', start_date) \
            .lte('timestamp', end_date)
        
        if user_id:
            query = query.eq('user_id', str(user_id))
            
        response = query.order('timestamp', desc=False).limit(10000).execute()
        print("======== DATA SENT TO FRONTEND ========", response.data)
        return jsonify(response.data if response.data else []), 200
                
    except Exception as e:
        print(f"[API LOG] Database Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/report/<period>', methods=['GET'])
def get_report(period):
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400
        
    try:
        latest_record = g.supabase.table('user_readings') \
            .select('timestamp') \
            .eq('user_id', str(user_id)) \
            .order('timestamp', desc=True) \
            .limit(1) \
            .execute()
            
        if latest_record.data:
            latest_time_str = latest_record.data[0]['timestamp']
            if latest_time_str.endswith('Z'):
                latest_time_str = latest_time_str[:-1] + '+00:00'
            now = datetime.fromisoformat(latest_time_str)
        else:
            now = datetime.now(timezone.utc)
            
        mode = 'standard'
        if period == 'daily':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            label_fmt = '%H:00'
        elif period == 'weekly':
            start_date = now - timedelta(days=7)
            label_fmt = '%a'
        elif period == 'monthly':
            start_date = now - timedelta(days=30)
            mode = 'monthly_weeks'
        elif period == 'yearly':
            start_date = now - timedelta(days=365)
            label_fmt = '%b'
            mode = 'yearly'
        else:
            start_date = now - timedelta(days=1)
            label_fmt = '%H:00'
            
        start_iso = start_date.isoformat() 
        
        response = g.supabase.table('user_readings') \
            .select('timestamp, power') \
            .eq('user_id', str(user_id)) \
            .gte('timestamp', start_iso) \
            .order('timestamp') \
            .limit(5000) \
            .execute()
            
        data = response.data if response.data else []
        
        aggregated_energy = defaultdict(float)
        aggregated_peak = defaultdict(float)
        keys_order = []
        
        for item in data:
            ts_str = item['timestamp']
            if ts_str.endswith('Z'):
                ts_str = ts_str[:-1] + '+00:00'
            dt = datetime.fromisoformat(ts_str)
            
            power = float(item.get('power') or 0)
            energy = (power / 1000.0) * (8.0 / 3600.0)
            
            if mode == 'monthly_weeks':
                days_diff = (dt - start_date).days
                week_num = min((days_diff // 7) + 1, 4)
                key = f"Week {week_num}"
            else:
                key = dt.strftime(label_fmt)
                
            if key not in aggregated_energy:
                keys_order.append(key)
                
            aggregated_energy[key] += energy
            if power > aggregated_peak[key]:
                aggregated_peak[key] = power
                
        labels = keys_order
        values_total = [round(aggregated_energy[k], 4) for k in keys_order]
        values_peak = [round(aggregated_peak[k], 2) for k in keys_order]
        
        total_consumption = sum(values_total)
        total_cost = total_consumption * 1.5
        
        return jsonify({
            "labels": labels,
            "values_total": values_total,
            "values_peak": values_peak,
            "total_consumption": round(total_consumption, 3),
            "total_cost": round(total_cost, 2),
            "peak_consumption": round(max(values_peak) if values_peak else 0, 2)
        }), 200
        
    except Exception as e:
        print(f"Error in {period} report: {str(e)}")
        return jsonify({"error": str(e)}), 500



api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY is not set.")
genai.configure(api_key=api_key)

@api_bp.route('/api/ai/recommendations', methods=['POST'])
def get_gemini_recommendations():
    try:
        req_data = request.get_json()
        devices_data = req_data.get('devices', {})
        
        if not devices_data:
            return jsonify({"error": "No devices data provided"}), 400
      
        data_summary = ""
        for device, power in devices_data.items():
            data_summary += f"- Device: {device}, Total power observed: {round(power, 1)} Watts.\n"
            
        prompt = (
            f"You are an expert energy efficiency engineering consultant for the SENTRA smart system. Based on the following real consumption data for the devices:\n{data_summary}\n"
            "Analyze the consumption of each device accurately, and provide exactly ONE highly effective, practical recommendation IN ENGLISH, based on engineering facts, to optimize consumption and immediately reduce the bill.\n"
            "💡 Recommendation Conditions:\n"
            "- The recommendation must be realistic, impactful, and entirely tailored to the specific operating nature of the device (whether cooling, heating, lighting, or otherwise).\n"
            "⚠️ Strict Formatting and Maximum Speed Constraints:\n"
            "1. Start the recommendation directly for each device without any introductions, greetings, or conversational filler to ensure maximum response speed.\n"
            "2. Strictly adhere to the exact following format so the JavaScript code can parse it automatically. Use an asterisk (*) to separate devices:\n"
            "Device_Name: The recommendation here\n"
            "*Next_Device_Name: The recommendation here"
        )
        
        response = gemini_model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.0,
                "max_output_tokens": 2000
            }
        )
        
        if response and response.text:
            return jsonify({"recommendations": response.text.strip()}), 200
        else:
            return jsonify({"error": "AI response was empty."}), 500
            
    except Exception as e:
        error_msg = str(e)
        print(f"Gemini API Error: {error_msg}")
        
        if "429" in error_msg or "quota" in error_msg.lower():
            return jsonify({"error": "API rate limit exceeded. Please wait about 40 seconds and try again."}), 429
            
        return jsonify({"error": "Error connecting to the AI server.", "details": error_msg}), 500