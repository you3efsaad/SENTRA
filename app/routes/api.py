from flask import Blueprint, request, jsonify
import app.globals as g  # ✅ استخدام globals الموحد عشان نوصل للـ AI
from datetime import datetime

api_bp = Blueprint('api', __name__)

# ==========================================
# 1. استقبال البيانات من ESP32 (القلب النابض)
# ==========================================
@api_bp.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400

        # 1. تحديث القراءات الحية (Live Data)
        # بنستخدم g.latest_data عشان الموقع يشوفها
        g.latest_data["voltage"] = float(data.get("voltage", 0))
        g.latest_data["current"] = float(data.get("current", 0))
        g.latest_data["power"] = float(data.get("power", 0))
        g.latest_data["energy"] = float(data.get("energy_consumption", 0))
        g.latest_data["frequency"] = float(data.get("frequency", 0))
        g.latest_data["pf"] = float(data.get("pf", 0))

        # 2. تحديث وقت آخر اتصال (عشان نعرف لو الجهاز فصل)
        g.last_update_time = datetime.now()

        # ==================================================
        # 🧠 3. تشغيل الذكاء الاصطناعي (AI Integration)
        # ==================================================
        if g.ai_engine:
            # بنشغل الموديل بس لو الباور أكبر من 5 وات (عشان الشوشرة)
            if g.latest_data["power"] > 5:
                # الدالة دي هتعمل حاجتين: تتوقع الاسم، وتتعلم من القراءة دي
                device_name, cluster_id = g.ai_engine.process_reading(
                    g.latest_data["power"], 
                    g.latest_data["pf"]
                )
                
                # بنسجل النتيجة عشان تظهر في الموقع
                g.latest_data["ai_device_name"] = device_name
                g.latest_data["ai_cluster_id"] = cluster_id
            else:
                # لو الباور قليل، يبقى الجهاز في وضع خمول
                g.latest_data["ai_device_name"] = "Idle"
                g.latest_data["ai_cluster_id"] = -1

        # ==================================================

        # 4. الرد على الـ ESP32 بالأوامر (التحكم والتايمر)
        remaining_time = 0
        
        # منطق التايمر
        if g.timer_end_time:
            now = datetime.now()
            if now < g.timer_end_time:
                remaining_time = int((g.timer_end_time - now).total_seconds())
            else:
                remaining_time = 0
                g.timer_end_time = None
                # لو التايمر خلص وكان شغال، افصله
                if g.latest_command == 'on':
                    g.latest_command = 'off'
                    print("[⏰] Timer finished. Command set to OFF.")

        # الرد النهائي للـ ESP
        response = {
            "status": "success",
            "command": g.latest_command,  # 'on' or 'off'
            "power_limit": g.power_limit, # حد الفصل (Overload)
            "timer": remaining_time       # وقت التايمر المتبقي للـ LCD
        }
        
        return jsonify(response), 200

    except Exception as e:
        print(f"[⚠️] Error in /data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 2. استقبال تنبيه الفصل الطارئ (Trip)
# ==========================================
@api_bp.route('/control', methods=['GET', 'POST'])
def control_device():
    # الـ ESP بيبعت هنا لو فصل لوحده (Trip) أو بيستعلم عن الحالة
    try:
        if request.method == 'POST':
            data = request.json
            if data and 'command' in data:
                g.latest_command = data['command'] # المفروض تكون 'off'
                print(f"[⚠️] Device Tripped! Command synced to: {g.latest_command}")
        
        return jsonify({"command": g.latest_command})
    except Exception:
        return jsonify({"command": g.latest_command}) # Fallback