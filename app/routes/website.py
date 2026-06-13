import random
import traceback
from datetime import datetime, timedelta
from collections import defaultdict
from dateutil import parser
from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_mail import Mail, Message
from authlib.integrations.flask_client import OAuth
import app.globals as g
import time
website_bp = Blueprint('website', __name__)

# ==========================================
# OAUTH CONFIGURATION
# ==========================================

oauth = OAuth()

@website_bp.record_once
def on_load(state):
    oauth.init_app(state.app)

google = oauth.register(
    name='google',
    client_id='673834878535-e57b25tik1bn94t8hqnanao1lmme2j2i.apps.googleusercontent.com',
    client_secret='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',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

facebook = oauth.register(
    name='facebook',
    client_id='1252617043250615',
    client_secret='cfc5e48dc7345d70ad384c97db676d7c',
    access_token_url='https://graph.facebook.com/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    api_base_url='https://graph.facebook.com/',
    client_kwargs={'scope': 'email public_profile'}
)

# ==========================================
# HELPERS & DECORATORS
# ==========================================

@website_bp.context_processor
def inject_user_data():
    user_data = {'avatar_url': None, 'tariff_type': '1'}
    user_id = session.get('user_id')
    
    if user_id:
        try:
            res = g.supabase.table("users").select("avatar_url, tariff_type").eq("id", user_id).execute()
            if res.data and len(res.data) > 0:
                user_data['avatar_url'] = res.data[0].get('avatar_url')
                user_data['tariff_type'] = str(res.data[0].get('tariff_type') or '1')
        except Exception as e:
            print("Error fetching user data:", e)
            
    return dict(current_user=user_data)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('website.auth_page'))
        return f(*args, **kwargs)
    return decorated_function

def calculate_cost(kwh):
    if kwh <= 50: return kwh * 0.48
    elif kwh <= 100: return kwh * 0.58
    elif kwh <= 200: return kwh * 0.77
    elif kwh <= 350: return kwh * 1.06
    elif kwh <= 650: return kwh * 1.28
    elif kwh <= 1000: return kwh * 1.28
    else: return kwh * 1.45

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@website_bp.route('/auth')
def auth_page():
    if 'user_id' in session:
        return redirect(url_for('website.dashboard'))
    return render_template('auth.html')

@website_bp.route('/login/<provider>')
def login_oauth(provider):
    client = oauth.create_client(provider)
    redirect_uri = url_for('website.authorize_oauth', provider=provider, _external=True)
    return client.authorize_redirect(redirect_uri)

@website_bp.route('/authorize/<provider>')
def authorize_oauth(provider):
    client = oauth.create_client(provider)
    token = client.authorize_access_token()
    
    if provider == 'google':
        user_info = token.get('userinfo')
        email = user_info.get('email')
        name = user_info.get('name')
    elif provider == 'facebook':
        resp = client.get('me?fields=id,name,email')
        user_info = resp.json()
        email = user_info.get('email')
        name = user_info.get('name')

    max_retries = 3
    existing_user = None
    
    # Retry logic for fetching the user
    for attempt in range(max_retries):
        try:
            existing_user = g.supabase.table("users").select("*").eq("email", email).execute()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1)

    if existing_user is not None and len(existing_user.data) == 0:
        # Retry logic for inserting a new user
        for attempt in range(max_retries):
            try:
                response = g.supabase.table("users").insert({
                    "name": name,
                    "email": email,
                    "password_hash": "OAUTH_USER_NO_PASSWORD" 
                }).execute()
                user_id = response.data[0]['id']
                db_name = name
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(1)
    else:
        user_id = existing_user.data[0]['id']
        db_name = existing_user.data[0].get('name', name) 

    session['user_id'] = user_id
    session['user_name'] = db_name
    return redirect(url_for('website.dashboard'))

@website_bp.route('/api/signup_send_otp', methods=['POST'])
def signup_send_otp():
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email').strip().lower()
        password = data.get('password')

        existing_user = g.supabase.table("users").select("*").eq("email", email).execute()
        if len(existing_user.data) > 0:
            return jsonify({"status": "error", "message": "Email already registered"}), 400

        otp = str(random.randint(100000, 999999))
        hashed_password = generate_password_hash(password)
        
        session['pending_signup'] = {
            'name': name,
            'email': email,
            'password_hash': hashed_password,
            'otp': otp
        }

        msg = Message(
            subject="SENTRA - Account Verification Code",
            sender="noreply@sentra-system.com",
            recipients=[email]
        )
        msg.body = f"Hello {name},\n\nWelcome to SENTRA. Your account verification code is: {otp}\n\nPlease enter this code to complete your registration."
        g.mail.send(msg)

        return jsonify({"status": "success", "message": "Verification code sent to your email"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@website_bp.route('/api/signup_verify', methods=['POST'])
def signup_verify():
    try:
        data = request.json
        code = data.get('code')
        pending = session.get('pending_signup')

        if not pending:
            return jsonify({"status": "error", "message": "Session expired. Please sign up again."}), 400

        if code == pending['otp']:
            g.supabase.table("users").insert({
                "name": pending['name'],
                "email": pending['email'],
                "password_hash": pending['password_hash']
            }).execute()

            session.pop('pending_signup', None)
            return jsonify({"status": "success", "message": "Registration successful. Please login."})
        else:
            return jsonify({"status": "error", "message": "Invalid Verification Code"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email').strip().lower()
        password = data.get('password')

        response = g.supabase.table("users").select("*").eq("email", email).execute()
        user_data = response.data

        if len(user_data) == 0:
            return jsonify({"status": "error", "message": "Invalid email or password"}), 401

        user = user_data[0]
        
        if check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return jsonify({"status": "success", "redirect": url_for('website.dashboard')})
        else:
            return jsonify({"status": "error", "message": "Invalid email or password"}), 401

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('website.auth_page'))

@website_bp.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email').strip().lower()
    user = g.supabase.table("users").select("*").eq("email", email).execute()
    
    if len(user.data) > 0:
        otp = str(random.randint(100000, 999999))
        session['reset_otp'] = otp
        session['reset_email'] = email
        
        try:
            msg = Message(
                subject="SENTRA - Security Verification Code",
                sender="noreply@sentra-system.com",
                recipients=[email]
            )
            msg.body = f"Hello Operator,\n\nYour security verification code is: {otp}\n\nIf you did not request this, please ignore this email."
            g.mail.send(msg)
            return jsonify({"status": "success", "message": "Verification code sent to your email"})
        except Exception as e:
            print(f"MAIL ERROR: {e}")
            return jsonify({"status": "error", "message": "Failed to send email. Check console."}), 500
    
    return jsonify({"status": "error", "message": "Email not found in our database"}), 404

@website_bp.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    code = request.json.get('code')
    if code == session.get('reset_otp'):
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid code"}), 400

@website_bp.route('/api/reset-password', methods=['POST'])
def reset_password():
    email_data = request.json.get('email')
    if not email_data:
        return jsonify({"status": "error", "message": "Email is missing"}), 400
        
    email = email_data.strip().lower()
    new_password = request.json.get('password')
    
    if email == session.get('reset_email'):
        hashed_password = generate_password_hash(new_password)
        g.supabase.table("users").update({"password_hash": hashed_password}).eq("email", email).execute()
        
        session.pop('reset_otp', None)
        session.pop('reset_email', None)
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "Session expired or email mismatch"}), 400


# ==========================================
# DASHBOARD & REAL-TIME ROUTES
# ==========================================

@website_bp.route('/')
@login_required
def dashboard():
    user_id = session.get('user_id')
    
    devices_res = g.supabase.table("safe_power_devices").select("*").eq("user_id", user_id).eq("is_main", False).execute()
    saved_devices = devices_res.data
    
    return render_template('dashboard.html', saved_devices=saved_devices)

@website_bp.route('/latest')
@website_bp.route('/get_readings')
def get_latest_readings():
    espid_raw = request.args.get('espid')
    
    if not espid_raw or espid_raw in ['0', 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    device_name = "Unknown"
    is_main = False
    
    if g.supabase:
        try:
            res = g.supabase.table("safe_power_devices").select("device_name, is_main").eq("espid", espid).execute()
            if res.data:
                device_name = res.data[0]["device_name"]
                is_main = res.data[0].get("is_main", False)
        except Exception:
            pass

    if not hasattr(g, 'esps') or espid not in g.esps:
        return jsonify({
            "espid": espid,
            "device_name": device_name,
            "voltage": 0,
            "current": 0,
            "power": 0,
            "energy": 0,
            "frequency": 0,
            "pf": 0,
            "command": "off",
            "budget_locked": False,
            "is_main": is_main
        })
        
    esp = g.esps[espid]
    data = esp["data"]

    return jsonify({
        "espid": espid,
        "device_name": device_name,
        "voltage": float(data.get('voltage', 0)),
        "current": float(data.get('current', 0)),
        "power": float(data.get('power', 0)),
        "energy": float(data.get('energy', 0)),
        "frequency": float(data.get('frequency', 0)),
        "pf": float(data.get('pf', 0)),
        "command": esp["control"].get("latest_command", "off"),
        "budget_locked": esp["settings"].get("budget_locked", False),
        "is_main": is_main
    })

@website_bp.route('/ai-status')
def ai_status():
    try:
        espid_raw = request.args.get('espid')
        if not espid_raw or espid_raw in ['0', 'null', 'undefined']:
            return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
            
        espid = int(espid_raw)
        
        if hasattr(g, 'esps') and espid in g.esps:
            esp_data = g.esps[espid]["data"]
            power = esp_data.get("power", 0)
            device_name = esp_data.get("ai_device_name", "Idle")
        else:
            power = 0
            device_name = "Idle"
        
        return jsonify({
            "status": "success",
            "device_name": device_name,
            "badge_status": "Active" if float(power) > 5 else "Standby"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
@website_bp.route('/set_command', methods=['POST'])
@login_required
def handle_web_command():
    user_id = session.get('user_id')
    data = request.json or {}
    espid_raw = data.get('espid')
    
    if not espid_raw or espid_raw in ['0', 0, 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    try:
        espid = int(espid_raw)
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid espid format"}), 400

    cmd = data.get('command')
    if cmd not in ['on', 'off']:
        return jsonify({"status": "error", "message": "Invalid command"}), 400

    if g.supabase:
        ownership_check = g.supabase.table("safe_power_devices").select("id, is_main").eq("espid", espid).eq("user_id", user_id).execute()
        if not ownership_check.data:
            return jsonify({"status": "error", "message": "Unauthorized: Device not owned by user"}), 403
            
        if ownership_check.data[0].get('is_main', False):
            return jsonify({"status": "error", "message": "Forbidden: Cannot control the main meter"}), 403
    
    if hasattr(g, 'esps') and espid in g.esps:
        esp_settings = g.esps[espid]["settings"]
        
        if cmd == 'on' and esp_settings.get("budget_locked", False):
            return jsonify({
                "status": "error", 
                "message": "BUDGET_LOCKED"
            }), 403
            
        g.esps[espid]["control"]["latest_command"] = cmd
        
        if cmd == 'on':
            esp_settings["flag_current_limit"] = False
            esp_settings["flag_power_limit"] = False
            esp_settings["manual_locked"] = False 
        elif cmd == 'off':
            esp_settings["manual_locked"] = True 
            g.esps[espid]["timer"]["end_time"] = None 
            g.esps[espid]["timer"]["paused_remaining"] = None
            
        return jsonify({"status": "success", "command": cmd})
        
    return jsonify({"status": "error", "message": "Device not active in memory"}), 404

@website_bp.route('/api/add_device', methods=['POST'])
@login_required
def add_device():
    try:
        data = request.json
        device_name = data.get('name')
        user_id = session.get('user_id')

        g.supabase.table("user_devices").insert({
            "user_id": user_id,
            "device_name": device_name
        }).execute()

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================================
# SETTINGS, TIMER & BUDGET ROUTES
# ==========================================

@website_bp.route('/settings')
@login_required
def settings():
    return render_template('Settings.html')


@website_bp.route('/esp_limit', methods=['GET', 'POST'])
@website_bp.route('/set_limit', methods=['POST'])
# Removed @login_required to allow ESP32 access
def handle_limit():
    user_id = session.get('user_id')
    data = request.get_json(silent=True) or {}
    espid_raw = data.get('espid') or request.args.get('espid')
    
    if not espid_raw or espid_raw in ['0', 0, 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    limit = data.get('limit')

    # Ownership Check (Only if user_id exists, meaning it's the web UI)
    if g.supabase and user_id:
        ownership = g.supabase.table("safe_power_devices").select("id").eq("espid", espid).eq("user_id", user_id).execute()
        if not ownership.data:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    if limit:
        try:
            if espid not in getattr(g, 'esps', {}):
                g.init_esp_state(espid)
            g.esps[espid]["control"]["current_limit"] = float(limit)
            return jsonify({"status": "success", "current_limit": float(limit)})
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid number"}), 400
            
    if hasattr(g, 'esps') and espid in g.esps:
        return jsonify({"status": "success", "current_limit": g.esps[espid]["control"].get("current_limit", 50.0)})
        
    return jsonify({"status": "error", "message": "Missing limit value"}), 400

@website_bp.route('/get_timer')
# Removed @login_required to allow ESP32 access
def get_timer():
    user_id = session.get('user_id')
    espid_raw = request.args.get('espid')
    
    if not espid_raw or espid_raw in ['0', 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    
    # Ownership Check (Only if user_id exists)
    if g.supabase and user_id:
        ownership = g.supabase.table("safe_power_devices").select("id").eq("espid", espid).eq("user_id", user_id).execute()
        if not ownership.data:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403

    if not hasattr(g, 'esps') or espid not in g.esps:
        return jsonify({"remaining_seconds": 0, "paused": False})
        
    esp_timer = g.esps[espid]["timer"]
    remaining = 0
    is_paused = False
    
    if esp_timer.get("paused_remaining") is not None:
        remaining = int(esp_timer["paused_remaining"])
        is_paused = True
    elif esp_timer.get("end_time"):
        now = datetime.now()
        if now < esp_timer["end_time"]:
            remaining = int((esp_timer["end_time"] - now).total_seconds())
        else:
            esp_timer["end_time"] = None 
            if g.esps[espid]["control"].get("latest_command") == 'on':
                g.esps[espid]["control"]["latest_command"] = 'off'

    return jsonify({"remaining_seconds": remaining, "paused": is_paused})
@website_bp.route('/set_timer', methods=['POST'])
@login_required
def set_timer():
    user_id = session.get('user_id')
    data = request.json or {}
    espid_raw = data.get('espid')
    
    if not espid_raw or espid_raw in ['0', 0, 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    minutes = int(data.get('duration_minutes', 0))

    if g.supabase:
        ownership = g.supabase.table("safe_power_devices").select("id").eq("espid", espid).eq("user_id", user_id).execute()
        if not ownership.data:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    if hasattr(g, 'esps') and espid in g.esps:
        esp = g.esps[espid]
        esp["timer"]["paused_remaining"] = None
        if minutes > 0:
            esp["timer"]["end_time"] = datetime.now() + timedelta(minutes=minutes)
            esp["control"]["latest_command"] = 'on'
            esp["settings"]["manual_locked"] = False
        else:
            esp["timer"]["end_time"] = None
            esp["control"]["latest_command"] = 'off'
            esp["settings"]["manual_locked"] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "ESP not found in memory"}), 404

@website_bp.route('/pause_timer', methods=['POST'])
@login_required
def pause_timer():
    user_id = session.get('user_id')
    data = request.json or {}
    espid_raw = data.get('espid')
    
    if not espid_raw or espid_raw in ['0', 0, 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    
    if g.supabase:
        ownership = g.supabase.table("safe_power_devices").select("id").eq("espid", espid).eq("user_id", user_id).execute()
        if not ownership.data:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403

    if hasattr(g, 'esps') and espid in g.esps:
        esp = g.esps[espid]
        if esp["timer"].get("end_time"):
            now = datetime.now()
            if now < esp["timer"]["end_time"]:
                remaining = (esp["timer"]["end_time"] - now).total_seconds()
                esp["timer"]["paused_remaining"] = remaining
                esp["timer"]["end_time"] = None
                # esp["control"]["latest_command"] = 'off' 
                # esp["settings"]["manual_locked"] = True
                return jsonify({"message": "Timer paused", "remaining": remaining})
                
    return jsonify({"message": "No active timer found"}), 400

@website_bp.route('/resume_timer', methods=['POST'])
@login_required
def resume_timer():
    user_id = session.get('user_id')
    data = request.json or {}
    espid_raw = data.get('espid')
    
    if not espid_raw or espid_raw in ['0', 0, 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    
    if g.supabase:
        ownership = g.supabase.table("safe_power_devices").select("id").eq("espid", espid).eq("user_id", user_id).execute()
        if not ownership.data:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403

    if hasattr(g, 'esps') and espid in g.esps:
        esp = g.esps[espid]
        if esp["timer"].get("paused_remaining"):
            esp["timer"]["end_time"] = datetime.now() + timedelta(seconds=esp["timer"]["paused_remaining"])
            esp["timer"]["paused_remaining"] = None
            esp["control"]["latest_command"] = 'on'
            esp["settings"]["manual_locked"] = False
            return jsonify({"message": "Timer resumed"})
            
    return jsonify({"message": "No paused timer found"}), 400
@website_bp.route('/reset_timer', methods=['POST'])
@login_required
def reset_timer():
    user_id = session.get('user_id')
    data = request.json or {}
    espid_raw = data.get('espid')
    
    if not espid_raw or espid_raw in ['0', 0, 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    
    if g.supabase:
        ownership = g.supabase.table("safe_power_devices").select("id").eq("espid", espid).eq("user_id", user_id).execute()
        if not ownership.data:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403

    if hasattr(g, 'esps') and espid in g.esps:
        esp = g.esps[espid]
        esp["timer"]["end_time"] = None
        esp["timer"]["paused_remaining"] = None
        esp["settings"]["manual_locked"] = False
        return jsonify({"status": "success", "message": "Timer canceled successfully"})
        
    return jsonify({"status": "error", "message": "No active ESP found"}), 400
def get_cost_by_tier(kwh, tier):
    kwh = float(kwh)
    tier = str(tier)
    if tier == "1": return kwh * 0.68
    if tier == "2": return (50 * 0.68) + ((kwh - 50) * 0.78)
    if tier == "3": return kwh * 0.95
    if tier == "4": return (200 * 0.95) + ((kwh - 200) * 1.55)
    if tier == "5": return (200 * 0.95) + (150 * 1.55) + ((kwh - 350) * 1.95)
    if tier == "6": return kwh * 2.10
    if tier == "7": return kwh * 2.23
    return kwh * 0.68

def get_kwh_from_money_by_tier(money, tier):
    money = float(money)
    tier = str(tier)
    if money <= 0: return 0
    if tier == "1": return money / 0.68
    if tier == "2":
        t1_max = 50 * 0.68
        if money <= t1_max: return money / 0.68
        return 50 + ((money - t1_max) / 0.78)
    if tier == "3": return money / 0.95
    if tier == "4":
        t3_max = 200 * 0.95
        if money <= t3_max: return money / 0.95
        return 200 + ((money - t3_max) / 1.55)
    if tier == "5":
        t4_max = (200 * 0.95) + (150 * 1.55)
        if money <= t4_max: return get_kwh_from_money_by_tier(money, "4")
        return 350 + ((money - t4_max) / 1.95)
    if tier == "6": return money / 2.10
    if tier == "7": return money / 2.23
    return money / 0.68

@website_bp.route('/api/calculate_kwh', methods=['POST'])
def calculate_kwh_route():
    try:
        data = request.json
        egp = float(data.get('egp', 0))
        kwh = 0.0

        tier1_max = 50 * 0.68
        tier2_max = tier1_max + (50 * 0.78)
        tier3_max = 200 * 0.95
        tier4_max = (200 * 0.95) + (150 * 1.55)
        tier5_max = (200 * 0.95) + (150 * 1.55) + (300 * 1.95)
        tier6_max = 1000 * 2.10

        if egp <= tier1_max:
            kwh = egp / 0.68
        elif egp <= tier2_max:
            kwh = 50 + ((egp - tier1_max) / 0.78)
        elif egp <= tier3_max:
            kwh = egp / 0.95
        elif egp <= tier4_max:
            kwh = 200 + ((egp - (200 * 0.95)) / 1.55)
        elif egp <= tier5_max:
            kwh = 350 + ((egp - ((200 * 0.95) + (150 * 1.55))) / 1.95)
        elif egp <= tier6_max:
            kwh = egp / 2.10
        else:
            kwh = egp / 2.23

        return jsonify({"status": "success", "kwh": kwh})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    
@website_bp.route('/api/set_budget', methods=['POST'])
@login_required
def set_energy_budget():
    data = request.json or {}
    user_id = session.get('user_id')
    espid_raw = data.get('espid')
    
    if not espid_raw or espid_raw in ['0', 0, 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    try:
        egp = float(data.get('egp', 0))
        kwh = float(data.get('kwh', 0))
        days = int(data.get('days', 0))
        
        if espid not in getattr(g, 'esps', {}):
            g.init_esp_state(espid)
            
        g.esps[espid]["settings"]["budget_egp"] = egp
        g.esps[espid]["settings"]["budget_kwh"] = kwh
        g.esps[espid]["settings"]["budget_days"] = days
        g.esps[espid]["settings"]["consumed_since_budget"] = 0.0
        g.esps[espid]["settings"]["flag_budget_50"] = False
        g.esps[espid]["settings"]["flag_budget_75"] = False
        g.esps[espid]["settings"]["flag_budget_100"] = False
        g.esps[espid]["settings"]["budget_start_time"] = datetime.now()
        g.esps[espid]["settings"]["budget_locked"] = False
        
        res = g.supabase.table("user_settings").select("id").eq("user_id", user_id).eq("espid", espid).execute()
        if not res.data:
            g.supabase.table("user_settings").insert({"user_id": user_id, "espid": espid}).execute()
            
        g.supabase.table("user_settings").update({
            "budget_egp": egp,
            "budget_kwh": kwh,
            "budget_duration_days": days,
            "consumed_since_budget": 0.0,
            "budget_start_time": datetime.now().isoformat()
        }).eq("user_id", user_id).eq("espid", espid).execute()
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@website_bp.route('/api/get_budget', methods=['GET'])
@login_required
def get_energy_budget():
    user_id = session.get('user_id')
    espid_raw = request.args.get('espid')
    
    if not espid_raw or espid_raw in ['0', 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    try:
        res = g.supabase.table("user_settings").select("budget_egp, budget_kwh, budget_duration_days").eq("user_id", user_id).eq("espid", espid).execute()
        if res.data:
            settings_data = res.data[0]
            return jsonify({
                "egp": float(settings_data.get('budget_egp', 0)),
                "kwh": float(settings_data.get('budget_kwh', 0)),
                "days": int(settings_data.get('budget_duration_days', 0))
            })
    except Exception:
        pass

    if hasattr(g, 'esps') and espid in g.esps:
        return jsonify({
            "egp": g.esps[espid]["settings"].get('budget_egp', 0),
            "kwh": g.esps[espid]["settings"].get('budget_kwh', 0),
            "days": g.esps[espid]["settings"].get('budget_days', 0)
        })

    return jsonify({"egp": 0, "kwh": 0, "days": 0})


# ==========================================
# HARDWARE & NOTIFICATION MANAGEMENT ROUTES
# ==========================================

@website_bp.route('/api/notifications')
@login_required
def get_user_notifications():
    user_id = session.get('user_id')
    res = g.supabase.table("notifications")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .limit(50)\
        .execute()
    return jsonify(res.data)

@website_bp.route('/api/clear_notifications', methods=['POST'])
@login_required
def clear_notifications():
    try:
        user_id = session.get('user_id')
        g.supabase.table("notifications").delete().eq("user_id", user_id).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@website_bp.route('/api/get_user_settings')
@login_required
def get_user_settings():
    user_id = session.get('user_id')
    espid_raw = request.args.get('espid')
    
    if not espid_raw or espid_raw in ['0', 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    try:
        res = g.supabase.table("user_settings").select("*").eq("user_id", user_id).eq("espid", espid).execute()
        if not res.data:
            res = g.supabase.table("user_settings").insert({"user_id": user_id, "espid": espid}).execute()
        
        settings_data = res.data[0]
        
        if espid not in getattr(g, 'esps', {}):
            g.init_esp_state(espid)
            
        g.esps[espid]["control"]["current_limit"] = float(settings_data.get('current_limit', 50))
        g.esps[espid]["settings"]["budget_kwh"] = float(settings_data.get('budget_kwh', 0))
        g.esps[espid]["settings"]["consumed_since_budget"] = float(settings_data.get('consumed_since_budget', 0))
        g.esps[espid]["settings"]["budget_start_time"] = settings_data.get('budget_start_time')
        g.esps[espid]["settings"]["min_voltage"] = float(settings_data.get('min_voltage', 190.0))
        g.esps[espid]["settings"]["max_voltage"] = float(settings_data.get('max_voltage', 250.0))
        
        return jsonify({"status": "success", "settings": settings_data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/update_user_settings', methods=['POST'])
@login_required
def update_user_settings():
    user_id = session.get('user_id')
    data = request.get_json() or {}
    espid_raw = data.get('espid')
    
    if not espid_raw or espid_raw in ['0', 0, 'null', 'undefined']:
        return jsonify({"status": "error", "message": "Invalid or missing espid"}), 400
        
    espid = int(espid_raw)
    update_data = {}
    
    if 'current_limit' in data:
        update_data['current_limit'] = float(data['current_limit'])
    if 'min_voltage' in data:
        update_data['min_voltage'] = float(data['min_voltage'])
    if 'max_voltage' in data:
        update_data['max_voltage'] = float(data['max_voltage'])
        
    if not update_data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
        
    try:
        g.supabase.table("user_settings").update(update_data).eq("user_id", user_id).eq("espid", espid).execute()
        
        if espid in getattr(g, 'esps', {}):
            if 'current_limit' in update_data:
                g.esps[espid]["control"]["current_limit"] = update_data['current_limit']
            if 'min_voltage' in update_data:
                g.esps[espid]["settings"]["min_voltage"] = update_data['min_voltage']
            if 'max_voltage' in update_data:
                g.esps[espid]["settings"]["max_voltage"] = update_data['max_voltage']
                
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/active_esps')
@login_required
def get_active_esps():
    user_id = session.get('user_id')
    try:
        res = g.supabase.table("user_settings").select("espid").eq("user_id", user_id).execute()
        db_esps = [row['espid'] for row in res.data]
        
        live_esps = list(getattr(g, 'esps', {}).keys())
        all_esps = sorted(list(set(db_esps + live_esps)))
        
        return jsonify({"status": "success", "esps": all_esps})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@website_bp.route('/api/get_saved_esps')
@login_required
def get_saved_esps():
    user_id = session.get('user_id')
    try:
        res = g.supabase.table("safe_power_devices").select("*").eq("user_id", user_id).execute()
        return jsonify({"status": "success", "esps": res.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/active_unregistered_esps')
@login_required
def active_unregistered_esps():
    user_id = session.get('user_id')
    try:
        res = g.supabase.table("safe_power_devices").select("espid").eq("user_id", user_id).execute()
        registered_esps = [row['espid'] for row in res.data]
        
        active_esps = list(getattr(g, 'esps', {}).keys())
        unregistered = [eid for eid in active_esps if eid not in registered_esps]
        
        return jsonify({"status": "success", "unregistered": unregistered})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Add this new route
@website_bp.route('/api/generate_esp_id', methods=['GET'])
@login_required
def generate_esp_id():
    import random
    try:
        while True:
            new_id = random.randint(10000, 99999)
            res = g.supabase.table("safe_power_devices").select("id").eq("espid", new_id).execute()
            if not res.data:
                return jsonify({"status": "success", "espid": new_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Update the add device route
@website_bp.route('/api/add_safe_power_device', methods=['POST'])
@login_required
def add_safe_power_device():
    user_id = session.get('user_id')
    data = request.json
    name = data.get('name')
    espid = int(data.get('espid', -1))
    is_main = data.get('is_main', False)
    
    if espid <= 0 or not name:
        return jsonify({"status": "error", "message": "Invalid data"}), 400
        
    try:
        check_res = g.supabase.table("safe_power_devices").select("id").eq("espid", espid).execute()
        if check_res.data:
            return jsonify({"status": "error", "message": "ID conflict detected. Please close the window and try adding the device again to generate a new ID."}), 409

        g.supabase.table("safe_power_devices").insert({
            "user_id": user_id,
            "device_name": name,
            "espid": espid,
            "is_main": is_main
        }).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/main_meter_status', methods=['GET'])
@login_required
def main_meter_status():
    user_id = session.get('user_id')
    try:
        res = g.supabase.table("safe_power_devices").select("espid").eq("user_id", user_id).eq("is_main", True).execute()
        if res.data and len(res.data) > 0:
            return jsonify({"status": "exists", "espid": res.data[0]['espid']})
        return jsonify({"status": "not_found"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/my_device_ids', methods=['GET'])
@login_required
def my_device_ids():
    user_id = session.get('user_id')
    try:
        res = g.supabase.table("safe_power_devices").select("device_name, espid, is_main").eq("user_id", user_id).order("is_main", desc=True).execute()
        return jsonify({"status": "success", "devices": res.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@website_bp.route('/api/edit_safe_power_device', methods=['POST'])
@login_required
def edit_safe_power_device():
    user_id = session.get('user_id')
    data = request.json
    espid = data.get('espid')
    new_name = data.get('name')
    
    if not espid or not new_name:
        return jsonify({"status": "error", "message": "بيانات ناقصة"}), 400
        
    try:
        g.supabase.table("safe_power_devices").update({"device_name": new_name})\
            .eq("user_id", user_id).eq("espid", espid).execute()
            
        if hasattr(g, 'esps') and espid in g.esps:
            g.esps[espid]["data"]["ac_device_name"] = new_name
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/delete_safe_power_device', methods=['POST'])
@login_required
def delete_safe_power_device():
    user_id = session.get('user_id')
    data = request.json
    espid = data.get('espid')
    
    if not espid:
        return jsonify({"status": "error", "message": "ESPID مفقود"}), 400
        
    try:
        g.supabase.table("safe_power_devices").delete()\
            .eq("user_id", user_id).eq("espid", espid).execute()
            
        if hasattr(g, 'esps') and espid in g.esps:
            del g.esps[espid]
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
# ==========================================
# ANALYTICS & REPORTS ROUTES
# ==========================================

@website_bp.route('/analytics')
def analytics():
    return render_template('analytics.html')

@website_bp.route('/historical')
@website_bp.route('/device_power')
def historical_data():
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        if not start_str or start_str == 'undefined':
            latest_record = g.supabase.table("house_1").select("Time").order("Time", desc=True).limit(1).execute()
            if latest_record.data:
                base_date = parser.parse(latest_record.data[0]['Time'])
            else:
                base_date = datetime.now()
                
            start_str = (base_date - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")
            end_str = base_date.strftime("%Y-%m-%d 23:59:59")
        else:
            if len(start_str) <= 10: start_str += " 00:00:00"
            if end_str and len(end_str) <= 10: end_str += " 23:59:59"

        response = g.supabase.table("house_1")\
            .select("Time, Aggregate")\
            .gte("Time", start_str)\
            .lte("Time", end_str)\
            .order("Time")\
            .limit(15000)\
            .execute()
        
        data = response.data

        if not data:
            return jsonify({"labels": [], "power": [], "energy": [], "values": []})

        if len(data) > 300:
            step = len(data) // 300
            data = data[::step]

        labels, power_vals, energy_vals = [], [], []
        prev_time = None

        for row in data:
            dt = parser.parse(row['Time'])
            labels.append(dt.strftime('%Y-%m-%d %H:%M'))
            
            power = float(row.get('Aggregate') or 0)
            power_vals.append(power)

            if prev_time:
                time_diff = (dt - prev_time).total_seconds()
                if time_diff > 3600: time_diff = 8.0 
            else:
                time_diff = 8.0
            
            prev_time = dt
            energy_kwh = (power / 1000.0) * (time_diff / 3600.0)
            energy_vals.append(energy_kwh)
        
        return jsonify({
            "labels": labels, 
            "values": energy_vals,
            "power": power_vals,
            "energy": energy_vals
        })
    except Exception as e:
        return jsonify({"labels": [], "power": [], "energy": [], "values": []}), 500

@website_bp.route('/report/<report_type>')
def get_report_by_type(report_type):
    try:
        latest_record = g.supabase.table("house_1").select("Time").order("Time", desc=True).limit(1).execute()
        if latest_record.data:
            base_date = parser.parse(latest_record.data[0]['Time'])
        else:
            base_date = datetime.now()

        start_time, label_fmt, mode = None, None, 'standard'

        if report_type == 'daily':
            start_time = base_date.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
            label_fmt = '%H:00'
        elif report_type == 'weekly':
            start_time = (base_date - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            label_fmt = '%a'
        elif report_type == 'monthly':
            start_time = (base_date - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            mode = 'monthly_weeks' 
        elif report_type == 'yearly':
            start_time = (base_date - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
            label_fmt = '%b'
            mode = 'yearly'
        else:
            return jsonify({"error": "Invalid type"}), 400

        response = g.supabase.table("house_1")\
            .select("Time, Aggregate")\
            .gte("Time", start_time)\
            .lte("Time", base_date.strftime("%Y-%m-%d %H:%M:%S"))\
            .order("Time")\
            .limit(5000)\
            .execute()
        
        rows = response.data
        aggregated_energy = defaultdict(float)
        aggregated_peak = defaultdict(float)
        keys_order = []
        start_dt = parser.parse(start_time)

        for row in rows:
            dt = parser.parse(row['Time'])
            power = float(row.get('Aggregate') or 0)
            energy = (power / 1000.0) * (8.0 / 3600.0)

            if mode == 'monthly_weeks':
                days_diff = (dt - start_dt).days
                week_num = min((days_diff // 7) + 1, 4)
                key = f"Week {week_num}"
            else:
                key = dt.strftime(label_fmt)

            if key not in aggregated_energy:
                keys_order.append(key)

            aggregated_energy[key] += energy
            if power > aggregated_peak[key]:
                aggregated_peak[key] = power

        values_energy = [round(aggregated_energy[k], 4) for k in keys_order]
        values_peak = [round(aggregated_peak[k], 2) for k in keys_order]
        costs = [calculate_cost(v) for v in values_energy]
        
        return jsonify({
            "labels": keys_order,
            "values_total": values_energy,
            "values_peak": values_peak,
            "total_consumption": round(sum(values_energy), 3),
            "total_cost": round(sum(costs), 2),
            "peak_consumption": round(max(values_peak) if values_peak else 0, 2)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@website_bp.route('/device_energy')
def device_energy():
    try:
        response = g.supabase.table("house_1").select("Appliance_Name, Aggregate").neq("Appliance_Name", "Idle").order("Time", desc=True).limit(1000).execute()
        
        device_totals = {}
        for row in response.data:
            name = row.get("Appliance_Name")
            power = float(row.get("Aggregate", 0))
            if name not in device_totals:
                device_totals[name] = 0
            device_totals[name] += (power / 1000.0) * (8.0 / 3600.0) 
            
        return jsonify({
            "device_names": list(device_totals.keys()),
            "device_energy": [round(val, 3) for val in device_totals.values()]
        })
    except Exception as e:
        return jsonify({"device_names": [], "device_energy": []})

@website_bp.route('/report/device_breakdown/<report_type>')
def device_breakdown(report_type):
    return jsonify({"devices": []})


# ==========================================
# COMMUNITY HUB ROUTES
# ==========================================

@website_bp.route('/community')
@login_required
def community():
    try:
        response = g.supabase.table("posts").select(
            "id, user_id, content, created_at, users(name, avatar_url), comments(id, user_id, content, created_at, users(name, avatar_url))"
        ).order("created_at", desc=True).execute()
        posts = response.data
    except Exception as e:
        posts = []
    return render_template('community.html', posts=posts)

@website_bp.route('/api/create_post', methods=['POST'])
@login_required
def create_post():
    try:
        content = request.json.get('content')
        user_id = session.get('user_id')
        if not content:
            return jsonify({"status": "error", "message": "Content cannot be empty"}), 400
            
        g.supabase.table("posts").insert({"user_id": user_id, "content": content}).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/edit_post', methods=['POST'])
@login_required
def edit_post():
    try:
        data = request.json
        post_id = data.get('post_id')
        new_content = data.get('content')
        user_id = session.get('user_id')

        post = g.supabase.table("posts").select("user_id").eq("id", post_id).execute()
        if not post.data or post.data[0]['user_id'] != user_id:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403

        g.supabase.table("posts").update({"content": new_content}).eq("id", post_id).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/delete_post', methods=['POST'])
@login_required
def delete_post():
    try:
        post_id = request.json.get('post_id')
        user_id = session.get('user_id')

        post = g.supabase.table("posts").select("user_id").eq("id", post_id).execute()
        if not post.data or post.data[0]['user_id'] != user_id:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403

        g.supabase.table("posts").delete().eq("id", post_id).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/add_comment', methods=['POST'])
@login_required
def add_comment():
    try:
        data = request.json
        post_id = data.get('post_id')
        content = data.get('content')
        user_id = session.get('user_id')
        user_name = session.get('user_name', 'Anonymous')

        if not post_id or not content:
            return jsonify({"status": "error", "message": "Missing data"}), 400

        comment_data = {
            "post_id": post_id,
            "user_id": user_id,
            "content": content
        }
        g.supabase.table("comments").insert(comment_data).execute()

        post_response = g.supabase.table("posts").select("user_id").eq("id", post_id).execute()
        
        if post_response.data:
            post_owner_id = post_response.data[0].get("user_id")
            
            if post_owner_id and post_owner_id != user_id:
                notification_message = f"{user_name} commented on your post."
                
                g.supabase.table("notifications").insert({
                    "user_id": post_owner_id,
                    "title": "New Comment",
                    "message": notification_message,
                    "type": "info"
                }).execute()

        return jsonify({"status": "success", "message": "Comment added successfully"})
    except Exception as e:
        print("Error adding comment:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/delete_comment', methods=['POST'])
@login_required
def delete_comment():
    try:
        comment_id = request.json.get('comment_id')
        user_id = session.get('user_id')

        comment = g.supabase.table("comments").select("user_id").eq("id", comment_id).execute()
        if not comment.data or comment.data[0]['user_id'] != user_id:
            return jsonify({"status": "error", "message": "Unauthorized"}), 403

        g.supabase.table("comments").delete().eq("id", comment_id).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/my_posts')
@login_required
def get_my_posts():
    try:
        user_id = session.get('user_id')
        response = g.supabase.table("posts").select(
            "id, content, created_at, users(name, avatar_url)"
        ).eq("user_id", user_id).order("created_at", desc=True).execute()
        
        return jsonify({"status": "success", "posts": response.data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================================
# PROFILE & ACCOUNT ROUTES
# ==========================================

@website_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@website_bp.route('/api/save_config', methods=['POST'])
@login_required
def save_config():
    data = request.json
    user_id = session.get('user_id')
    new_tariff = str(data.get('tariff'))
    
    try:
        user_res = g.supabase.table("users").select("tariff_type").eq("id", user_id).execute()
        old_tariff = str(user_res.data[0].get('tariff_type', '1'))

        g.supabase.table("users").update({"tariff_type": new_tariff}).eq("id", user_id).execute()
        
        settings_res = g.supabase.table("user_settings").select("*").eq("user_id", user_id).execute()
        
        for setting in settings_res.data:
            espid = setting.get('espid')
            initial_egp = float(setting.get('budget_egp', 0))
            
            if initial_egp > 0 and espid in g.esps:
                esp_settings = g.esps[espid]["settings"]
                consumed_kwh = float(esp_settings.get("consumed_since_budget", 0.0))
                
                spent_money = get_cost_by_tier(consumed_kwh, old_tariff)
                remaining_money = initial_egp - spent_money
                
                if remaining_money <= 0:
                    esp_settings["budget_kwh"] = consumed_kwh
                    esp_settings["budget_locked"] = True
                    esp_settings["flag_budget_100"] = True
                    g.esps[espid]["control"]["latest_command"] = 'off'
                else:
                    additional_kwh = get_kwh_from_money_by_tier(remaining_money, new_tariff)
                    new_total_kwh = consumed_kwh + additional_kwh
                    
                    esp_settings["budget_kwh"] = new_total_kwh
                    esp_settings["budget_locked"] = False
                    esp_settings["flag_budget_100"] = False

                esp_settings["flag_budget_50"] = False
                esp_settings["flag_budget_75"] = False
                
                g.supabase.table("user_settings").update({
                    "budget_kwh": esp_settings["budget_kwh"]
                }).eq("user_id", user_id).eq("espid", espid).execute()

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/user_stats')
@login_required
def get_user_stats():
    user_id = session.get('user_id')
    
    res = g.supabase.table("user_readings").select("energy_consumption").eq("user_id", user_id).execute()
    total_energy = sum(row['energy_consumption'] for row in res.data)
    
    device_res = g.supabase.table("user_readings").select("device_name, power").eq("user_id", user_id).order("power", desc=True).limit(1).execute()
    top_device = device_res.data[0]['device_name'] if device_res.data else "None"

    return jsonify({
        "total_energy": round(total_energy, 2),
        "top_device": top_device
    })

@website_bp.route('/api/update_profile', methods=['POST'])
def update_profile():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"status": "error", "message": "User not logged in"}), 401

        data = request.json
        new_name = data.get('name')
        new_password = data.get('password')

        update_data = {}
        if new_name:
            update_data['name'] = new_name
            
        if new_password:
            update_data['password_hash'] = generate_password_hash(new_password)

        if update_data:
            response = g.supabase.table("users").update(update_data).eq("id", user_id).execute()
            
            if not response.data or len(response.data) == 0:
                return jsonify({
                    "status": "error", 
                    "message": "Update failed. Check RLS policies in Supabase."
                }), 400
            
            if new_name:
                session['user_name'] = new_name 

        return jsonify({"status": "success"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/update_avatar', methods=['POST'])
def update_avatar():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"status": "error", "message": "Not logged in"}), 401

        data = request.json
        if not data or 'avatar_url' not in data:
            return jsonify({"status": "error", "message": "No image provided"}), 400

        new_avatar_url = data['avatar_url']
        g.supabase.table("users").update({"avatar_url": new_avatar_url}).eq("id", user_id).execute()
        
        return jsonify({"status": "success"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@website_bp.route('/api/delete_account', methods=['DELETE'])
def delete_account():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        g.supabase.table("users").delete().eq("id", user_id).execute()
        session.clear()

        return jsonify({"status": "success", "message": "Account deleted successfully"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def calculate_cost(kwh):
    if kwh <= 50:
        return kwh * 0.68
    elif kwh <= 100:
        return (50 * 0.68) + ((kwh - 50) * 0.78)
    elif kwh <= 200:
        return kwh * 0.95
    elif kwh <= 350:
        return (200 * 0.95) + ((kwh - 200) * 1.55)
    elif kwh <= 650:
        return (200 * 0.95) + (150 * 1.55) + ((kwh - 350) * 1.95)
    elif kwh <= 1000:
        return kwh * 2.10
    else:
        return kwh * 2.23


# ==========================================
# STATIC PAGES & CONTACT ROUTES
# ==========================================

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
        
        g.supabase.table("contact_messages").insert({
            "name": data.get('name'),
            "email": data.get('email'),
            "subject": data.get('subject'),
            "message": data.get('message'),
            "timestamp": datetime.now().isoformat()
        }).execute()

        msg = Message(
            subject=f"New Contact Message: {data.get('subject')}",
            sender="noreply@sentra-system.com",
            recipients=["ahmdyouns44@gmail.com"] 
        )
        msg.body = f"New message from Sentra System:\n\nName: {data.get('name')}\nEmail: {data.get('email')}\n\nMessage:\n{data.get('message')}"
        g.mail.send(msg)

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500