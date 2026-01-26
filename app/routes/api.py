from flask import Blueprint, request, jsonify
from app.globals import latest_data, latest_command, power_limit, timer_end_time
from datetime import datetime

# تعريف البلوبرنت الخاص بالهاردوير
api_bp = Blueprint('api', __name__)

# 1. استقبال البيانات من ESP32
@api_bp.route('/data', methods=['POST'])
def receive_data():
    global power_limit, latest_command
    try:
        data = request.json
        
        # تحديث المتغيرات العامة (Live Data)
        latest_data["voltage"] = data.get("voltage", 0)
        latest_data["current"] = data.get("current", 0)
        latest_data["power"] = data.get("power", 0)
        latest_data["energy"] = data.get("energy_consumption", 0)
        latest_data["frequency"] = data.get("frequency", 0)
        latest_data["pf"] = data.get("pf", 0)
        
        # تحديث وقت آخر اتصال (عشان نعرف لو الجهاز فصل)

        # منطق التايمر (Timer Logic)
        remaining_time = 0
        if timer_end_time:
            now = datetime.now()
            if now < timer_end_time:
                remaining_time = int((timer_end_time - now).total_seconds())
            else:
                remaining_time = 0 
                # لو الوقت خلص والجهاز شغال، اطفيه
                if latest_command == "on":
                     latest_command = "off"

        # الرد على الـ ESP32 بالأوامر الجديدة
        response = {
            "status": "success",
            "command": latest_command,       # هل يشغل ولا يفصل؟
            "power_limit": power_limit,      # حد الحمل الأقصى
            "timer": remaining_time          # وقت التايمر المتبقي
        }
        return jsonify(response), 200

    except Exception as e:
        print(f"Error in /data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# 2. استقبال تنبيه الفصل الطارئ (Trip)
@api_bp.route('/control', methods=['POST'])
def control_device():
    global latest_command
    try:
        data = request.json
        # لو الـ ESP فصل الكهرباء عشان الحمل زاد، بيبلغنا هنا
        if 'command' in data:
            latest_command = data['command'] # المفروض تكون 'off'
            print(f"⚠️ Device Tripped! Command set to: {latest_command}")
            return jsonify({"status": "updated", "command": latest_command}), 200
        return jsonify({"error": "No command provided"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    


    