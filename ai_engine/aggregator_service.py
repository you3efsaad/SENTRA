import os
import time
import schedule
import pandas as pd
from datetime import datetime, timedelta, timezone
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Fetch credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Safety check to ensure the variables were loaded correctly
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials! Please check your .env file.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def aggregate_and_predict():
    print(f"\n{'='*50}\n⏳ Started aggregating data for the past hour...")
    
    now = datetime.now(timezone.utc)
    end_time = now.replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(hours=1)
    
    print(f"📅 Fetching minute readings from the raw table between: {start_time.strftime('%H:%M')} and {end_time.strftime('%H:%M')}")
    
    response = supabase.table("user_readings") \
        .select("timestamp, power") \
        .gte("timestamp", start_time.isoformat()) \
        .lt("timestamp", end_time.isoformat()) \
        .execute()
        
    raw_data = response.data
    if not raw_data:
        print("⚠️ No readings found for this hour! (Table is empty)")
        return

    df_raw = pd.DataFrame(raw_data)
    
    hourly_aggregate_mean = float(df_raw['power'].mean())

    hourly_row = {
        "Time": start_time.isoformat(), 
        "Unix": int(start_time.timestamp()),
        "Aggregate": hourly_aggregate_mean, # We place the average consumption of the whole house here
        "Appliance1": 0.0, 
        "Appliance2": 0.0, 
        "Appliance3": 0.0,
        "Appliance4": 0.0, 
        "Appliance5": 0.0, 
        "Appliance6": 0.0,
        "Appliance7": 0.0, 
        "Appliance8": 0.0, 
        "Appliance9": 0.0
    }

    try:
        supabase.table("house_3").insert(hourly_row).execute()
        print(f"✅ Reading uploaded successfully! Total house consumption (Aggregate): {hourly_aggregate_mean:.2f} Watts")
    except Exception as e:
        print(f"❌ Error uploading data to house_3 table: {e}")
        return

    # -------------------------------------------------------------
    print("🔮 Launching the smart prediction and analysis engine...")
    try:
        now_check = datetime.now()
        if now_check.day == 1 and now_check.hour == 0:
            print("⚙️ [Start of the month] Starting the automatic model retraining and self-improvement cycle...")
            try:
                import retrain_engine
                retrain_engine.run_periodic_retraining()
                print("✅ Model weights updated and errors corrected successfully!")
            except Exception as retrain_error:
                print(f"⚠️ Warning: Periodic update failed, but prediction will continue: {retrain_error}")
                
        import predict_engine
        predict_engine.run_prediction_pipeline()
        print("🚀 Automatic cycle completed successfully!")
    except Exception as e:
        print(f"❌ An error occurred while running the prediction engine: {e}")
    
    print("🧹 [Cleanup] Cleaning up the predictions table from old forecasts...")
    try:
        time_threshold = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        supabase.table("predictions").delete().lt("prediction_time", time_threshold).execute()
        print("✅ Cleanup completed successfully!")
    except Exception as clean_error:
        print(f"⚠️ Warning: Failed to clean up the predictions table: {clean_error}")

if __name__ == "__main__":
    print("🚀 Starting the maestro in the background...")
    
    aggregate_and_predict()
    
    schedule.every().hour.at(":00").do(aggregate_and_predict)
    
    while True:
        schedule.run_pending()
        time.sleep(1)