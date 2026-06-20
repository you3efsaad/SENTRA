from app import create_app
import subprocess


app = create_app()
app.secret_key = "any_random_secret_string_here" 

if __name__ == "__main__":
    subprocess.Popen(["python", "ai_engine/aggregator_service.py"])
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)