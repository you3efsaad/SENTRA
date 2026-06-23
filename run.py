import os
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from app import create_app
from app.globals import supabase
from app.nilm_ai_Engin.engine_manager import NILMEngineManager
import subprocess


app = create_app()
def run_nilm_engine_job():
    """
    Background job that runs periodically to process active smart plugs,
    evaluate accuracy, and trigger fine-tuning.
    """
    print("[NILM Engine] Starting scheduled processing cycle...")
    try:
        manager = NILMEngineManager(supabase)
        manager.process_active_plugs()
        print("[NILM Engine] Processing cycle completed successfully.")
    except Exception as e:
        print(f"[NILM Engine] Error during processing: {str(e)}")
# Initialize the Background Scheduler
scheduler = BackgroundScheduler(daemon=True)
# Add job to run every day at 3:00 AM, or every hour (e.g., hours=1)
# For testing purposes, you can set minutes=5
scheduler.add_job(run_nilm_engine_job, 'interval', hours=24) 
scheduler.start()
app.secret_key = "any_random_secret_string_here" 

if __name__ == "__main__":
    try:
        subprocess.Popen(["python", "ai_engine/aggregator_service.py"])
        use_reloader = os.environ.get("FLASK_ENV") == "development"
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()





