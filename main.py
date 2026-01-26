# Endpoint to save contact messages to Supabase
from flask import Flask, render_template, jsonify, request
import time
from datetime import datetime, timedelta
from collections import defaultdict

from dateutil import parser
from threading import Timer, Lock
import random
from apscheduler.schedulers.background import BackgroundScheduler
from device_identifier import determineDeviceName
from supabase import create_client, Client
import os
from dotenv import load_dotenv
last_update = datetime.now()
disconnect_timeout = timedelta(seconds=10)
import atexit



def check_timeout():
    global latest_data
    if datetime.now() - last_update > disconnect_timeout:
        keys_to_reset = ["voltage", "current", "power", "frequency", "pf"]
        for k in keys_to_reset:
            latest_data[k] = 0


load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


app = Flask(__name__)

latest_data = {
    "voltage": 0,
    "current": 0,
    "power": 0,
    "energy": 0,
    "frequency": 0,
    "pf": 0
}

latest_command = ""
power_limit = 100
reset_timer = None
timer_lock = Lock()
# Timer data storage
timer_data = {"end_time": 0, "paused": False, "remaining": 0}

def schedule_reset(delay=15):
    global reset_timer
    def do_reset():
        global latest_command
        with timer_lock:
            latest_command = ""
            reset_timer = None

    with timer_lock:
        if isinstance(reset_timer, Timer):  # Ensure reset_timer is a Timer object
            reset_timer.cancel()
        reset_timer = Timer(delay, do_reset)
        reset_timer.start()


@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/consumption')
def consumption():
    return render_template('consumption.html')

@app.route('/reports')
def reports():
    return render_template('base_report.html')

@app.route('/settings')
def settings():
    return render_template('Settings.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('Contact.html')


@app.route('/data', methods=['POST'])
def receive_data():
    global latest_data, last_update  # Add this line

    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        if data.get('sensor_status') == 'offline':
            latest_data = {
                "voltage": 0,
                "current": 0,
                "power": 0,
                "energy": 0,
                "frequency": 0,
                "pf": 0
            }
            return jsonify({"status": "sensor-offline"})

        required_fields = [
            'device', 'power', 'voltage', 'current',
            'energy_consumption', 'active_power',
            'frequency', 'power_factor', 'active_energy'
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing field: {field}', 'status': 'error'}), 400

        latest_data = {
            "voltage": float(data['voltage']),
            "current": float(data['current']),
            "power": float(data['power']),
            "energy": float(data['energy_consumption']),
            "frequency": float(data['frequency']),
            "pf": float(data['power_factor'])
        }
        # استقبلت داتا جديدة — حدّث timestamp
        last_update = datetime.now()


        return jsonify({"status": "received"})

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}", "status": "error"}), 500
##########################

def monitor_power_limit():
    global latest_command
    if latest_command == "on" and latest_data["power"] > power_limit:
        latest_command = "off"
        print(f"⚠️ Power exceeded limit ({power_limit}W). Sending OFF to ESP.")

@app.route('/latest')
def latest():
    print("📥 /latest endpoint called")

    # ✅ لو كل القيم في latest_data أصفار → رجّع داتا كلها صفر
    if all(value == 0 for value in latest_data.values()):
        print("⚠️ Sensor is offline or no data → Returning zeros")
        return jsonify({
            "voltage": {"current": 0, "trend": 0, "history": [0, 0, 0, 0]},
            "current": {"current": 0, "trend": 0, "history": [0, 0, 0, 0]},
            "power": {"current": 0, "trend": 0, "history": [0, 0, 0, 0]},
            "energy": {"current": 0, "trend": 0, "history": [0, 0, 0, 0]},
            "frequency": {"current": 0, "trend": 0, "history": [0, 0, 0, 0]},
            "powerFactor": {"current": 0, "trend": 0, "history": [0, 0, 0, 0]}
        })



    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    yesterday_end = today_start - timedelta(seconds=1)

    try:
        history_resp = supabase.table("energy_usage_hourly") \
            .select('"Voltage", "Current", "Power(W)", "Energy Consumption(kWh)", "Frequency (Hz)", "Power Factor"') \
            .gte("Timestamp", today_start.isoformat()) \
            .order("Timestamp", desc=True) \
            .limit(4) \
            .execute()

        history_rows = history_resp.data[::-1]
        print("✅ history rows:", history_rows)

        yesterday_resp = supabase.table("energy_usage_hourly") \
            .select('"Voltage", "Current", "Power(W)", "Energy Consumption(kWh)", "Frequency (Hz)", "Power Factor"') \
            .gte("Timestamp", yesterday_start.isoformat()) \
            .lte("Timestamp", yesterday_end.isoformat()) \
            .order("Timestamp", desc=True) \
            .limit(1) \
            .execute()

        yesterday_row = yesterday_resp.data[0] if yesterday_resp.data else {}
        print("✅ yesterday row:", yesterday_row)

        fallback = {
            "Voltage": latest_data["voltage"],
            "Current": latest_data["current"],
            "Power(W)": latest_data["power"],
            "Energy Consumption(kWh)": latest_data["energy"],
            "Frequency (Hz)": latest_data["frequency"],
            "Power Factor": latest_data["pf"]
        }

        if not yesterday_row:
            yesterday_row = fallback
            print("⚠️ Using fallback")

        def get_history(field):
            return [round(row.get(field, 0), 2) for row in history_rows]

        def calc_trend(today_val, yesterday_val):
            try:
                if yesterday_val == 0:
                    return 0
                return round(((today_val - yesterday_val) / yesterday_val) * 100, 2)
            except:
                return 0

        def wrap_metric(field_name, current_val, yesterday_val):
            return {
                "current": round(current_val, 2),
                "trend": calc_trend(current_val, yesterday_val),
                "history": get_history(field_name)
            }

        return jsonify({
            "voltage": wrap_metric("Voltage", latest_data["voltage"], yesterday_row["Voltage"]),
            "current": wrap_metric("Current", latest_data["current"], yesterday_row["Current"]),
            "power": wrap_metric("Power(W)", latest_data["power"], yesterday_row["Power(W)"]),
            "energy": wrap_metric("Energy Consumption(kWh)", latest_data["energy"], yesterday_row["Energy Consumption(kWh)"]),
            "frequency": wrap_metric("Frequency (Hz)", latest_data["frequency"], yesterday_row["Frequency (Hz)"]),
            "powerFactor": wrap_metric("Power Factor", latest_data["pf"], yesterday_row["Power Factor"])
        })

    except Exception as e:
        print("❌ ERROR in /latest:", str(e))
        return jsonify({"message": f"Error generating trend: {str(e)}"}), 500



# ############################

@app.route('/historical')
def historical_data():
    start = request.args.get("start")
    end = request.args.get("end")

    if not start or not end:
        return jsonify({"message": "Start date and end date are required."}), 400

    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid date format"}), 400

    # Supabase expects ISO 8601 timestamps, and we want full-day range
    start_iso = start + "T00:00:00"
    end_iso = end + "T23:59:59"

    try:
        response = supabase.table("energy_usage_hourly") \
            .select("*") \
            .gte("Timestamp", start_iso) \
            .lte("Timestamp", end_iso) \
            .order("Timestamp", desc=False) \
            .execute()

        rows = response.data

        if not rows:
            return jsonify({
                "labels": [],
                "power": [],
                "energy": [],
                "message": "No data found for selected range."
            })

        result = {
            "labels": [],
            "power": [],
            "energy": [],
            "table_data": []
        }

        for row in rows:
            hour = parser.isoparse(row["Timestamp"]).strftime("%Y-%m-%d %H:00:00")
            power = round(row["Power(W)"], 2)
            energy = round(row["Energy Consumption(kWh)"], 2)
            voltage = round(row["Voltage"], 2)
            current = round(row["Current"], 2)
            active_power = round(row["Active Power (kW)"], 2)
            frequency = round(row["Frequency (Hz)"], 2)
            power_factor = round(row["Power Factor"], 2)
            active_energy = round(row["Active Energy (kWh)"], 2)

            result["labels"].append(hour)
            result["power"].append(power)
            result["energy"].append(energy)
            result["table_data"].append({
                "hour": hour,
                "power": power,
                "energy": energy,
                "voltage": voltage,
                "current": current,
                "active_power": active_power,
                "frequency": frequency,
                "power_factor": power_factor,
                "active_energy": active_energy
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({"message": f"Supabase error: {str(e)}"}), 500
    
########################################

def save_hourly_snapshot():
    try:
        if (latest_data['voltage'] == 0 and
            latest_data['current'] == 0 and
            latest_data['power'] == 0 and
            latest_data['energy'] == 0):
            return

        voltage = float(latest_data['voltage'])
        current = float(latest_data['current'])
        power = float(latest_data['power'])
        energy = float(latest_data['energy'])

        if (voltage > 0 and current == 0) or (current > 0 and power == 0):
            print(f"Skipped saving: Invalid sensor reading. "
                  f"Readings - V: {voltage}, A: {current}, W: {power}, kWh: {energy}")
            return

        timestamp = datetime.now().isoformat()
        device_name = determineDeviceName(voltage, current, power)

        data = {
            "Timestamp": timestamp,
            "Device": device_name,
            "Power(W)": power,
            "Energy Consumption(kWh)": energy,
            "Voltage": voltage,
            "Current": current,
            "Active Power (kW)": power / 1000,
            "Frequency (Hz)": float(latest_data['frequency']),
            "Power Factor": float(latest_data['pf']),
            "Active Energy (kWh)": energy
        }

        response = supabase.table("energy_usage_hourly").insert(data).execute()

        if response.data:
            print(f"[{timestamp}] Hourly snapshot saved for {device_name} - Power: {power}W, Current: {current}A")
        else:
            print("❌ Failed to save to Supabase: No data returned. Possible error in insert.")

    except Exception as e:
        print(f"❌ Error saving hourly snapshot: {e}")






@app.route('/report/daily')
def daily_report():
    try:
        today = datetime.today().strftime('%Y-%m-%d')
        start_iso = today + "T00:00:00"
        end_iso = today + "T23:59:59"

        # جلب البيانات من supabase خلال اليوم
        response = supabase.table("energy_usage_hourly") \
        .select('"Timestamp", "Power(W)", "Energy Consumption(kWh)"') \
        .gte("Timestamp", start_iso) \
        .lte("Timestamp", end_iso) \
        .order("Timestamp") \
        .execute()



        rows = response.data

        if not rows:
            return jsonify({"message": "No data found for today."}), 400

        # تجميع البيانات حسب الساعة
        from collections import defaultdict
        hourly_data = defaultdict(list)

        for row in rows:

            timestamp = parser.isoparse(row["Timestamp"])
            hour_str = timestamp.strftime("%H:00")

            energy = float(row["Energy Consumption(kWh)"])
            power = float(row["Power(W)"])

            hourly_data[hour_str].append({
                "energy": energy,
                "power": power
            })

        labels = []
        data = []
        all_avg_powers = []

        for hour in sorted(hourly_data.keys()):
            entries = hourly_data[hour]
            total_energy = sum(e["energy"] for e in entries)
            avg_power = sum(e["power"] for e in entries) / len(entries)
            peak_power = max(e["power"] for e in entries)
           

            labels.append(hour)
            data.append(round(total_energy, 2))
            all_avg_powers.append(avg_power)
        # احسب المتوسط للطاقة لكل ساعة مرة واحدة بعد اللوب
        all_avg_energies = [
            round(sum(e["energy"] for e in hourly_data[hour]) / len(hourly_data[hour]), 2)
            for hour in sorted(hourly_data.keys())
]


        total_consumption = sum(data)
        avg_consumption = total_consumption / len(data)
        peak_consumption = max(all_avg_powers)

        report_data = {
            "total_consumption": round(total_consumption, 2),
            "avg_consumption": round(avg_consumption, 2),
            "peak_consumption": round(peak_consumption, 2),
            "labels": labels,
            "data": data,
            "avg_data": [round(p, 2) for p in all_avg_powers],
            "avg_energy_data": all_avg_energies

        }

        return jsonify(report_data)

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500



@app.route('/report/weekly')
def weekly_report():
    try:
        today = datetime.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        start_of_week = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = week_end.replace(hour=23, minute=59, second=59, microsecond=0)

        start_iso = start_of_week.isoformat() + "+00:00"
        end_iso = end_of_week.isoformat() + "+00:00"


        # Fetch from Supabase
        response = supabase.table("energy_usage_hourly") \
            .select('"Timestamp", "Power(W)", "Energy Consumption(kWh)"') \
            .gte("Timestamp", start_iso) \
            .lte("Timestamp", end_iso) \
            .order("Timestamp") \
            .execute()

        rows = response.data

        if not rows:
            return jsonify({"message": "No data found for this week."}), 400

        # Prepare days of the week
        days_of_week = [(week_start + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

        daily_data = defaultdict(list)

        for row in rows:
            ts = parser.isoparse(row["Timestamp"])  # ✅ يعالج +00:00 تلقائيًا
            day_str = ts.strftime('%Y-%m-%d')
            daily_data[day_str].append({
                "energy": float(row["Energy Consumption(kWh)"]),
                "power": float(row["Power(W)"])
            })

        labels = []
        data = []
        total_consumption = 0
        avg_power_list = []
        peak_power_list = []
        avg_energy_list = []


        for day in days_of_week:
            labels.append(day)
            entries = daily_data.get(day, [])
            
            

            if entries:
                total_energy = sum(e["energy"] for e in entries)
                avg_power = sum(e["power"] for e in entries) / len(entries)
                peak_power = max(e["power"] for e in entries)
            else:
                total_energy = 0
                avg_power = 0
                peak_power = 0

            data.append(round(total_energy, 2))
            total_consumption += total_energy
            avg_power_list.append(avg_power)
            peak_power_list.append(peak_power)
            avg_energy = total_energy / len(entries) if entries else 0
            avg_energy_list.append(round(avg_energy, 2))

        avg_consumption = total_consumption / 7
        peak_consumption = max(peak_power_list)

        
        report_data = {
            "total_consumption": round(total_consumption, 2),
            "avg_consumption": round(avg_consumption, 2),
            "peak_consumption": round(peak_consumption, 2),
            "labels": labels,
            "data": data,
            "avg_data": [round(p, 2) for p in avg_power_list] ,
            "avg_energy_data": avg_energy_list

        }


        return jsonify(report_data)

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


@app.route('/report/monthly')
def monthly_report():
    try:
        today = datetime.today()
        month_start = today.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_end = next_month - timedelta(seconds=1)

        # استخدم isoformat() لإخراج "YYYY-MM-DDTHH:MM:SS"
        start_iso = month_start.isoformat()      # e.g. "2025-06-01T00:00:00"
        end_iso   = month_end.isoformat() + "+00:00"  # e.g. "2025-06-30T23:59:59+00:00"

        response = supabase.table("energy_usage_hourly") \
            .select('"Timestamp", "Power(W)", "Energy Consumption(kWh)"') \
            .gte("Timestamp", start_iso) \
            .lte("Timestamp", end_iso) \
            .order("Timestamp", desc=False) \
            .execute()

        rows = response.data
        if not rows:
            return jsonify({"message": "No data found for this month."}), 400

        # جمع البيانات أسبوعيًا
        weekly_data = {
            "Week 1": {"total_energy": 0, "power_list": []},
            "Week 2": {"total_energy": 0, "power_list": []},
            "Week 3": {"total_energy": 0, "power_list": []},
            "Week 4": {"total_energy": 0, "power_list": []}
        }

        for row in rows:
            # حل مشكلة الـ timezone باستخدام parser
            dt = parser.isoparse(row["Timestamp"])
            # احسب رقم الأسبوع داخل الشهر
            week_number = ((dt.day - 1) // 7) + 1
            week_key = f"Week {week_number}"

            energy = float(row["Energy Consumption(kWh)"])
            power  = float(row["Power(W)"])

            weekly_data[week_key]["total_energy"] += energy
            weekly_data[week_key]["power_list"].append(power)

        # تجهيز المخرجات
        labels = []
        data   = []
        all_avg_powers = []
        all_peak_powers = []
        avg_energy_list = []


        for week in ["Week 1", "Week 2", "Week 3", "Week 4"]:
            wd = weekly_data[week]
            labels.append(week)
            data.append(round(wd["total_energy"], 2))

            if wd["power_list"]:
                avg_power  = sum(wd["power_list"]) / len(wd["power_list"])
                peak_power = max(wd["power_list"])
            else:
                avg_power  = 0
                peak_power = 0

            all_avg_powers.append(avg_power)
            all_peak_powers.append(peak_power)
            avg_energy = wd["total_energy"] / len(wd["power_list"]) if wd["power_list"] else 0
            avg_energy_list.append(round(avg_energy, 2))

        weeks_with_data = [d for d in data if d > 0]
        avg_consumption = sum(weeks_with_data) / len(weeks_with_data) if weeks_with_data else 0

        report_data = {
            "total_consumption": round(sum(data), 2),
            "avg_consumption":   round(avg_consumption, 2),
            "peak_consumption":  round(max(all_peak_powers), 2),
            "labels": labels,
            "data":   data,
            "avg_data": [round(p, 2) for p in all_avg_powers] ,
            "avg_energy_data": avg_energy_list

        }


        return jsonify(report_data)

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# --------------------------------------------------

@app.route('/report/device_breakdown/<report_type>')
def device_breakdown(report_type):
    try:
        today = datetime.today()

        # تحديد الفترة بناء على report_type
        if report_type == "daily":
            start_date = today.strftime('%Y-%m-%d') + "T00:00:00"
            end_date = today.strftime('%Y-%m-%d') + "T23:59:59"

        elif report_type == "weekly":
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            start_date = start_of_week.strftime('%Y-%m-%d') + "T00:00:00"
            end_date = end_of_week.strftime('%Y-%m-%d') + "T23:59:59"

        elif report_type == "monthly":
            start_of_month = today.replace(day=1)
            next_month = (start_of_month + timedelta(days=32)).replace(day=1)
            start_date = start_of_month.strftime('%Y-%m-%d') + "T00:00:00"
            end_date = (next_month - timedelta(days=1)).strftime('%Y-%m-%d') + "T23:59:59"

        else:
            return jsonify({"message": "Invalid report type"}), 400

        # جلب البيانات من Supabase
        response = supabase.table("energy_usage_hourly") \
            .select('"Device", "Energy Consumption(kWh)"') \
            .gte("Timestamp", start_date) \
            .lte("Timestamp", end_date) \
            .execute()

        rows = response.data

        if not rows:
            return jsonify({"devices": []})

        device_data = defaultdict(float)

        for row in rows:
            device = row.get("Device", "Unknown")
            energy_val = row.get("Energy Consumption(kWh)", 0)

            try:
                energy = float(energy_val) if energy_val is not None else 0
            except ValueError:
                energy = 0

            device_data[device] += energy

        device_list = []
        for device, energy in device_data.items():
            cost = round(energy * 0.125, 2)
            device_list.append({
                "device": device,
                "consumption": f"{round(energy, 2)} kWh",
                "cost": f"${cost:.2f}"
            })

        # ترتيب القائمة تنازليًا حسب الاستهلاك
        device_list.sort(
            key=lambda x: float(x["consumption"].split()[0]),
            reverse=True
        )

        return jsonify({"devices": device_list})

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500
    
# ---------------------------------------

@app.route('/control', methods=['POST'])
def control():
    global latest_command,reset_timer 
    data = request.get_json() or {}
    cmd = data.get('command')
    if cmd in ('on', 'off'):
        latest_command = cmd
        if cmd == 'on':
            pass
            # جدولة إعادة الضبط بعد 15 ثانية
        else:
            # إذا جاء “off” قبل انتهاء المؤقت، نلغي المؤقت
            with timer_lock:
                if reset_timer:
                    reset_timer.cancel()
                    reset_timer = None
        return jsonify({'message': f'Command {cmd} received'})
    return jsonify({'message': 'Invalid command'}), 400

@app.route('/esp_command', methods=['GET'])
def esp_command():
    return jsonify({"command": latest_command})


@app.route('/set_limit', methods=['POST'])
def set_limit():
    global power_limit
    data = request.get_json()
    if not data or 'limit' not in data:
        return jsonify({'message': 'Invalid data'}), 400

    try:
        power_limit = float(data['limit'])
        return jsonify({'message': f'Power limit set to {power_limit}W'})
    except ValueError:
        return jsonify({'message': 'Invalid number format'}), 400


@app.route('/esp_limit', methods=['GET'])
def esp_setlimit():
    return jsonify({"power_limit": power_limit})



@app.route('/pause_timer', methods=['POST'])
def pause_timer():
    try:
        current_time = int(time.time())
        if not timer_data["paused"] and timer_data["end_time"] > current_time:
            timer_data["remaining"] = timer_data["end_time"] - current_time
            timer_data["paused"] = True
        return jsonify({"message": "Timer paused", "remaining": timer_data["remaining"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/resume_timer', methods=['POST'])
def resume_timer():
    try:
        if timer_data["paused"] and timer_data["remaining"] > 0:
            timer_data["end_time"] = int(time.time()) + timer_data["remaining"]
            timer_data["paused"] = False
            timer_data["remaining"] = 0
        return jsonify({"message": "Timer resumed", "end_time": timer_data["end_time"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/set_timer', methods=['POST'])
def set_timer():
    data = request.get_json()
    duration_minutes = data.get("duration_minutes", 0)

    if duration_minutes > 0:
        timer_data["end_time"] = int(time.time()) + duration_minutes * 60
        timer_data["paused"] = False
        timer_data["remaining"] = 0
        return jsonify({"message": "Timer set successfully", "end_time": timer_data["end_time"]}), 200
    else:
        return jsonify({"error": "Invalid duration"}), 400

@app.route('/get_timer', methods=['GET'])
def get_timer():
    current_time = int(time.time())
    if timer_data["paused"]:
        remaining = timer_data["remaining"]
    else:
        remaining = timer_data["end_time"] - current_time

    if remaining > 0:
        return jsonify({"remaining_seconds": remaining, "paused": timer_data["paused"]})
    else:
        timer_data["end_time"] = 0
        timer_data["paused"] = False
        timer_data["remaining"] = 0
        return jsonify({"remaining_seconds": 0, "paused": False})




@app.route('/reset_timer', methods=['POST'])
def reset_timer():
    try:
        timer_data["end_time"] = 0
        timer_data["paused"] = False
        timer_data["remaining"] = 0
        return jsonify({"message": "Timer reset successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/contact_message', methods=['POST'])
def contact_message():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        subject = data.get('subject')
        message = data.get('message')

        if not name or not message:
            return jsonify({'status': 'error', 'message': 'Name and message are required.'}), 400

        # Insert into Supabase table
        response = supabase.table('contact_messages').insert({
            'name': name,
            'email': email,
            'subject': subject,
            'message': message
        }).execute()
        
        if response.data:
            # بعد حفظ الرسالة في Supabase
            send_email_notification(name, email, subject, message)

            return jsonify({'status': 'success', 'message': 'Message saved successfully.'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to save message.'}), 500
    except Exception as e:
        print("🔥 ERROR in /contact_message:", str(e))  # ✅ اطبع الخطأ الحقيقي
        return jsonify({'status': 'error', 'message': str(e)}), 500

import smtplib
from email.mime.text import MIMEText

def send_email_notification(name, email, subject, message):
    sender = 'youseftaklo@students.du.edu.eg'  # إيميلك
    app_password = 'wdmo uzdn nsol uimj'  # App password من جوجل
    receiver = 'youseftaklo@students.du.edu.eg'  # ممكن يكون نفس الإيميل أو أي إيميل تاني

    full_message = f'''
    New contact message:

    Name: {name}
    Email: {email}
    Subject: {subject}
    Message: {message}
    '''

    msg = MIMEText(full_message)
    msg['Subject'] = 'New Contact Form Message'
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(msg)
        print("✅ Email sent successfully")
    except Exception as e:
        print("❌ Failed to send email:", str(e))




@app.route('/device_power')
def historical_device_power():
    from collections import defaultdict
    from dateutil import parser

    start = request.args.get("start")
    end = request.args.get("end")

    if not start or not end:
        return jsonify({"message": "Start and end dates required"}), 400

    try:
        start_iso = start + "T00:00:00"
        end_iso = end + "T23:59:59"

        response = supabase.table("energy_usage_hourly") \
            .select('"Timestamp", "Power(W)", "Current", "Voltage"') \
            .gte("Timestamp", start_iso) \
            .lte("Timestamp", end_iso) \
            .order("Timestamp", desc=False) \
            .execute()

        rows = response.data
        if not rows:
            return jsonify({"labels": [], "datasets": []})

        device_power_total = defaultdict(float)

        for row in rows:
            try:
                power = float(row["Power(W)"])
                current = float(row["Current"])
                voltage = float(row["Voltage"])
                device_name = determineDeviceName(voltage, current, power)

                device_power_total[device_name] += power
            except Exception as e:
                print(f"⚠️ Skipping row due to error: {e}")

        device_names = list(device_power_total.keys())
        total_power = [round(device_power_total[name], 2) for name in device_names]

        return jsonify({
            "labels": device_names,
            "datasets": [{
                "label": "Total Power (W)",
                "data": total_power,
                "fill": False,
                "tension": 0.4
            }]
        })

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500



@app.route('/device_energy')
def device_energy():
    start = request.args.get("start")
    end = request.args.get("end")

    if not start or not end:
        return jsonify({"message": "Start and end dates required"}), 400

    try:
        start_iso = start + "T00:00:00"
        end_iso = end + "T23:59:59"

        response = supabase.table("energy_usage_hourly") \
            .select('"Power(W)", "Current", "Energy Consumption(kWh)", "Voltage"') \
            .gte("Timestamp", start_iso) \
            .lte("Timestamp", end_iso) \
            .execute()

        rows = response.data
        if not rows:
            return jsonify({"device_names": [], "device_energy": []})

        device_energy = {}

        for row in rows:
            try:
                power = float(row["Power(W)"])
                current = float(row["Current"])
                voltage = float(row["Voltage"])
                energy = float(row["Energy Consumption(kWh)"])

                device_name = determineDeviceName(voltage, current, power)

                if device_name not in device_energy:
                    device_energy[device_name] = 0
                device_energy[device_name] += energy
            except Exception as e:
                print(f"Error processing row: {e}")

        names = list(device_energy.keys())
        values = [round(device_energy[name], 2) for name in names]

        return jsonify({"device_names": names, "device_energy": values})

    except Exception as e:
        return jsonify({"message": f"Error fetching device energy: {str(e)}"}), 500


def monitor_timer():
    global latest_command
    if not timer_data["paused"] and timer_data["end_time"] > 0:
        now = int(time.time())
        if now >= timer_data["end_time"]:
            if latest_command == "on":
                latest_command = "off"
                print("⏰ Timer finished. Sending OFF to ESP.")



# ---------------------- Start Safe Boot Setup ----------------------

import atexit

def safe_boot():
    # Debug: Check .env variables
    print(f"[INFO] SUPABASE_URL = {SUPABASE_URL}")
    print(f"[INFO] SUPABASE_KEY = {SUPABASE_KEY[:6]}..." if SUPABASE_KEY else "[WARN] No SUPABASE_KEY found")

    # Try Supabase client connection
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Missing Supabase credentials.")
        # Just trigger a harmless call to test:
        supabase.table("energy_usage_hourly").select("*").limit(1).execute()
        print("[✅] Supabase client initialized successfully.")
    except Exception as e:
        print(f"[❌] Failed to connect to Supabase: {e}")

    # Setup scheduler
    scheduler = BackgroundScheduler()
# داخل safe_boot بعد scheduler.start()
    scheduler.add_job(func=save_hourly_snapshot, trigger='interval', seconds=60)
    scheduler.add_job(func=save_hourly_snapshot, trigger='interval', hours=1)
    scheduler.add_job(func=monitor_power_limit, trigger='interval', seconds=3)
    scheduler.add_job(func=monitor_timer, trigger='interval', seconds=1)


    
    scheduler.start()

    atexit.register(lambda: scheduler.shutdown())

    # Detect environment
    is_dev = os.environ.get("FLASK_ENV") == "development"

    # Default to development if not explicitly set
    if "FLASK_ENV" not in os.environ:
        os.environ["FLASK_ENV"] = "development"
        is_dev = True

    host = '0.0.0.0'
    port = int(os.environ.get("PORT", 5000 if is_dev else 8080))

    if is_dev:
        print(f"[🚀] Starting app on http://{host}:{port} (mode: development)")
        app.run(host=host, port=port, debug=True)
    else:
        print("[✅] App initialized in production mode. Gunicorn will handle running.")

# Run only if script is executed directly
if __name__ == '__main__':
    safe_boot()
0