import os
import logging
import sys
import app.globals as g
from dotenv import load_dotenv
from flask import Flask, request
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from supabase import create_client
from app.utils import save_hourly_snapshot, monitor_background_logic

formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("SENTRA")
logger.setLevel(logging.INFO)

if logger.hasHandlers():
    logger.handlers.clear()
    
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

werkzeug_log = logging.getLogger('werkzeug')
werkzeug_log.setLevel(logging.ERROR)

def create_app():
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False

    load_dotenv()
    
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'ahmdyouns44@gmail.com'
    app.config['MAIL_PASSWORD'] = 'kwyq wybm ycsr vjxb'
    
    g.mail = Mail(app)

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if url and key:
        g.supabase = create_client(url, key)
        logger.info("DB: Supabase Connected")
    else:
        logger.error("DB: Credentials Missing")

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=save_hourly_snapshot, trigger="interval", minutes=60)
    scheduler.add_job(
        func=monitor_background_logic, 
        trigger="interval", 
        seconds=8, 
        max_instances=3, 
        misfire_grace_time=5
    )
    
    scheduler.start()

    from app.routes.api import api_bp
    from app.routes.website import website_bp
    
    app.register_blueprint(api_bp)
    app.register_blueprint(website_bp)

    @app.after_request
    def log_short_request(response):
        logger.info(f"WEB: {request.method} {request.path} [{response.status_code}]")
        return response

    return app