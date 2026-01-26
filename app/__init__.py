# app/__init__.py
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from supabase import create_client
import os
from dotenv import load_dotenv
import app.globals as g
from app.utils import save_hourly_snapshot, monitor_background_logic

def create_app():
    app = Flask(__name__)
    
    # 1. إعداد البيئة
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if url and key:
        g.supabase = create_client(url, key)
        print("✅ Supabase Connected")
    else:
        print("❌ Supabase Credentials Missing")

    # 2. تسجيل الـ Blueprints (الراوتات)
    from app.routes.api import api_bp
    from app.routes.website import website_bp
    
    app.register_blueprint(api_bp)
    app.register_blueprint(website_bp)

    # 3. تشغيل المهام الخلفية (Scheduler)
    scheduler = BackgroundScheduler()
    # حفظ داتا كل ساعة
    scheduler.add_job(func=save_hourly_snapshot, trigger="interval", minutes=60)
    # مراقبة التايمر والاتصال كل 2 ثانية
    scheduler.add_job(func=monitor_background_logic, trigger="interval", seconds=2)
    scheduler.start()

    return app