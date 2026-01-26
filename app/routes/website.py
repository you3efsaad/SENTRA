from flask import Blueprint, render_template, jsonify, request
import app.globals as g  # ✅ Correct import for globals
from datetime import datetime, timedelta
from dateutil import parser
from collections import defaultdict
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

website_bp = Blueprint('website', __name__)

# --- Helper Functions ---
def calculate_cost(kwh):
    if kwh <= 50: return kwh * 0.48
    elif kwh <= 100: return kwh * 0.58
    elif kwh <= 200: return kwh * 0.77
    elif kwh <= 350: return kwh * 1.06
    elif kwh <= 650: return kwh * 1.28
    elif kwh <= 1000: return kwh * 1.28
    else: return kwh * 1.45

# ==========================================
# 🌐 ROUTES
# ==========================================

# --- 1. Dashboard & Basic Routes ---

@website_bp.route('/')
def dashboard():
    return render_template('dashboard.html')

@website_bp.route('/latest')
@website_bp.route('/get_readings')
def get_latest_readings():
    # Update last connection time
    g.last_update_time = datetime.now()
    
    # Safely get data from globals
    safe_data = {k: (v if v is not None else 0) for k, v in g.latest_data.items()}
    
    # Support old graph format if needed
    if request.args.get('format') == 'full': 
        return jsonify({
            "voltage": {"current": safe_data.get('voltage', 0), "trend": 0, "history": []},
            "current": {"current": safe_data.get('current', 0), "trend": 0, "history": []},
            "power": {"current": safe_data.get('power', 0), "trend": 0, "history": []},
            "energy": {"current": safe_data.get('energy', 0), "trend": 0, "history": []},
            "frequency": {"current": safe_data.get('frequency', 0), "trend": 0, "history": []},
            "powerFactor": {"current": safe_data.get('pf', 0), "trend": 0, "history": []}
        })
    return jsonify(safe_data)

# --- 2. Control (ON/OFF) ---

@website_bp.route('/control', methods=['GET', 'POST'])
@website_bp.route('/esp_command', methods=['GET', 'POST'])
@website_bp.route('/set_command', methods=['GET', 'POST']) 
def handle_command():
    if request.method == 'POST':
        data = request.json
        cmd = data.get('command')
        if cmd in ['on', 'off']:
            g.latest_command = cmd
            return jsonify({"status": "success", "command": cmd, "message": f"Command {cmd} received"})
        return jsonify({"status": "error", "message": "Invalid command"}), 400
    else:
        return jsonify({"command": g.latest_command})

# --- 3. Power Limit ---

@website_bp.route('/esp_limit', methods=['GET', 'POST'])
@website_bp.route('/set_limit', methods=['GET', 'POST'])
def handle_limit():
    if request.method == 'POST':
        data = request.json
        limit = data.get('limit')
        if limit:
            try:
                g.power_limit = float(limit)
                return jsonify({"status": "success", "power_limit": g.power_limit, "message": f"Limit set to {g.power_limit}"})
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid number"}), 400
        return jsonify({"status": "error"}), 400
    else:
        return jsonify({"power_limit": g.power_limit})

# --- 4. Timer Logic ---

@website_bp.route('/get_timer')
def get_timer():
    remaining = 0
    is_paused = False
    
    if g.timer_paused_remaining is not None:
        remaining = int(g.timer_paused_remaining)
        is_paused = True
    elif g.timer_end_time:
        now = datetime.now()
        if now < g.timer_end_time:
            remaining = int((g.timer_end_time - now).total_seconds())
        else:
            remaining = 0
            g.timer_end_time = None 
            if g.latest_command == 'on':
                g.latest_command = 'off'

    return jsonify({"remaining_seconds": remaining, "remaining_time": remaining, "paused": is_paused})

@website_bp.route('/set_timer', methods=['POST'])
def set_timer():
    data = request.json
    minutes = data.get('duration_minutes', 0)
    
    if hasattr(g, 'timer_paused_remaining'):
        g.timer_paused_remaining = None

    if minutes > 0:
        g.timer_end_time = datetime.now() + timedelta(minutes=int(minutes))
        g.latest_command = 'on'
        print(f"[⏳] Timer set for {minutes} minutes. Command forced to ON.")
        return jsonify({"status": "success", "message": "Timer set", "end_time": g.timer_end_time.isoformat()})
    else:
        g.timer_end_time = None
        g.latest_command = 'off'
        return jsonify({"status": "success", "message": "Timer reset"})

@website_bp.route('/pause_timer', methods=['POST'])
def pause_timer():
    if g.timer_end_time:
        now = datetime.now()
        if now < g.timer_end_time:
            remaining = (g.timer_end_time - now).total_seconds()
            g.timer_paused_remaining = remaining
            g.timer_end_time = None
            return jsonify({"message": "Timer paused", "remaining": remaining})
    return jsonify({"message": "No active timer to pause"}), 400

@website_bp.route('/resume_timer', methods=['POST'])
def resume_timer():
    if hasattr(g, 'timer_paused_remaining') and g.timer_paused_remaining:
        g.timer_end_time = datetime.now() + timedelta(seconds=g.timer_paused_remaining)
        g.timer_paused_remaining = None
        return jsonify({"message": "Timer resumed"})
    return jsonify({"message": "No paused timer found"}), 400

@website_bp.route('/reset_timer', methods=['POST'])
def reset_timer():
    g.timer_end_time = None
    if hasattr(g, 'timer_paused_remaining'):
        g.timer_paused_remaining = None
    return jsonify({"message": "Timer reset successfully"})

# --- 5. Historical Data & Charts ---

@website_bp.route('/historical')
def historical_data():
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        if not start_str:
            start_str = (datetime.now() - timedelta(days=7)).isoformat()
        
        if 'T' not in start_str: start_str += "T00:00:00"
        if end_str and 'T' not in end_str: end_str += "T23:59:59"

        # ✅ Use g.supabase instead of direct import
        query = g.supabase.table("energy_usage_hourly").select("*").gte("Timestamp", start_str).order("Timestamp")
        if end_str:
            query = query.lte("Timestamp", end_str)
            
        response = query.execute()
        
        data = response.data
        if not data:
            return jsonify({"labels": [], "power": [], "energy": [], "values": []})

        labels = []
        power_vals = []
        energy_vals = []

        for row in data:
            dt = parser.parse(row['Timestamp'])
            labels.append(dt.strftime('%Y-%m-%d %H:%M'))
            power_vals.append(row.get('Power(W)', 0))
            energy_vals.append(row.get('Energy Consumption(kWh)', 0))
        
        return jsonify({
            "labels": labels, 
            "values": energy_vals,
            "power": power_vals,
            "energy": energy_vals
        })
    except Exception as e:
        print(f"Error in historical: {e}")
        return jsonify({"labels": [], "power": [], "energy": []})

@website_bp.route('/device_energy')
def device_energy():
    return jsonify({
        "device_names": ["Main Device"],
        "device_energy": [10.5] 
    })

@website_bp.route('/device_power')
def device_power():
    return historical_data()

# --- 6. Reports ---

@website_bp.route('/reports')
def reports():
    return render_template('base_report.html')

@website_bp.route('/report/<report_type>')
def get_report_by_type(report_type):
    now = datetime.now()
    try:
        if report_type == 'daily':
            start_time = now.replace(hour=0, minute=0, second=0).isoformat()
            label_fmt = '%H:00'
        elif report_type == 'weekly':
            start_time = (now - timedelta(weeks=1)).isoformat()
            label_fmt = '%a'
        elif report_type == 'monthly':
            start_time = (now - timedelta(days=30)).isoformat()
            label_fmt = '%d %b'
        else:
            return jsonify({"error": "Invalid type"}), 400

        # ✅ Use g.supabase
        response = g.supabase.table("energy_usage_hourly")\
            .select("*")\
            .gte("Timestamp", start_time)\
            .order("Timestamp")\
            .execute()
        
        rows = response.data
        aggregated = defaultdict(float)
        
        for row in rows:
            dt = parser.parse(row['Timestamp'])
            key = dt.strftime(label_fmt)
            aggregated[key] += float(row.get('Energy Consumption(kWh)', 0))

        labels = list(aggregated.keys())
        values = list(aggregated.values())
        costs = [calculate_cost(v) for v in values]

        return jsonify({
            "labels": labels,
            "values": values,
            "costs": costs,
            "avg_energy_data": values,
            "total_consumption": round(sum(values), 2),
            "total_cost": round(sum(costs), 2),
            "peak_consumption": round(max(values) if values else 0, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@website_bp.route('/report/device_breakdown/<report_type>')
def device_breakdown(report_type):
    return jsonify({"devices": []})

# --- 7. Static Pages & Contact ---

@website_bp.route('/settings')
def settings():
    return render_template('Settings.html')

@website_bp.route('/about')
def about():
    return render_template('about.html')

@website_bp.route('/contact')
def contact():
    return render_template('Contact.html')

@website_bp.route('/contact_message', methods=['POST'])
def contact_message():
    try:
        data = request.json
        # ✅ Use g.supabase
        g.supabase.table("contact_messages").insert({
            "name": data.get('name'),
            "email": data.get('email'),
            "subject": data.get('subject'),
            "message": data.get('message'),
            "timestamp": datetime.now().isoformat()
        }).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/consumption')
def consumption():
    return render_template('consumption.html')