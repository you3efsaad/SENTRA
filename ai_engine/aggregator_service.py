import time
import schedule
import pandas as pd
from datetime import datetime, timedelta, timezone
from supabase import create_client

# Initialize connection to Supabase
SUPABASE_URL = "https://wtsfngscmtmywcklplhj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind0c2ZuZ3NjbXRteXdja2xwbGhqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjEzNDQ0MSwiZXhwIjoyMDg3NzEwNDQxfQ.wYesuGasSOKtuvDwXJdQBZPY4MkTqVsKwKOGmjBtCBA"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def aggregate_and_predict():
    print(f"\n{'='*50}\nStarted aggregating the past hour's data to process all users...")
    
    # 1. Define the exact last hour range in Egypt time (UTC + 3)
    now = datetime.now(timezone.utc)
    now_egypt = now + timedelta(hours=3)
    end_time = now_egypt.replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(hours=1)
    
    print(f"Sync time range: {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}")
    
    # 2. Fetch a list of all users with an active main measuring device in the system
    try:
        devices_res = supabase.table("safe_power_devices") \
            .select("user_id, espid") \
            .eq("is_main", True).execute()
            
        active_devices = devices_res.data
        if not active_devices:
            print("No active main devices currently in the system.")
            return
            
        print(f"Found {len(active_devices)} active devices. Starting synchronous processing...")
    except Exception as device_error:
        print(f"Error querying devices table: {device_error}")
        return

    # 3. Loop over each user to process them entirely separately
    for device in active_devices:
        current_user_id = device['user_id']
        main_esp_id = device['espid']
        
        print(f"\nProcessing data for user: {current_user_id} | Device: ESP-{main_esp_id}")

        # 4. Fetch data specific to the current user only for this hour
        response = supabase.table("user_readings") \
            .select("timestamp, power") \
            .eq("user_id", current_user_id) \
            .eq("espid", main_esp_id) \
            .gte("timestamp", start_time.isoformat()) \
            .lt("timestamp", end_time.isoformat()) \
            .execute()
            
        raw_data = response.data
        if not raw_data:
            print("No readings found for this hour! (Sensor disconnected)")
            print("Skipping readings upload, moving directly to prediction engine to fill the gap...")
        else:
            # 5. Convert data and calculate the hourly mean
            df_raw = pd.DataFrame(raw_data)
            hourly_aggregate_mean = float(df_raw['power'].mean())

            # Prepare the new row and link it to user_id to prevent table overlap
            hourly_row = {
                "Time": start_time.isoformat(), 
                "Unix": int(start_time.timestamp()),
                "Aggregate": hourly_aggregate_mean,
                "user_id": current_user_id, 
                "Appliance1": 0.0, "Appliance2": 0.0, "Appliance3": 0.0,
                "Appliance4": 0.0, "Appliance5": 0.0, "Appliance6": 0.0,
                "Appliance7": 0.0, "Appliance8": 0.0, "Appliance9": 0.0
            }

            # Upload to house_3 table
            try:
                supabase.table("house_3").upsert(hourly_row).execute()
                print(f"Reading uploaded successfully! Total customer consumption: {hourly_aggregate_mean:.2f} Watts")
            except Exception as e:
                print(f"Error uploading data to house_3 table: {e}")

        # -------------------------------------------------------------
        # 6. Launch periodic model update and retraining engine (runs automatically on the 1st of every month)
        # -------------------------------------------------------------
        print("Checking AI engine scheduling...")
        try:
            if now_egypt.day == 1 and now_egypt.hour == 0:
                print(f"[Start of Month] Beginning self-retraining and update cycle for user: {current_user_id}...")
                try:
                    import retrain_engine
                    retrain_engine.run_periodic_retraining(current_user_id)
                    print("Custom model weights updated and calibrated successfully!")
                except Exception as retrain_error:
                    print(f"Warning: Periodic training failed for user, continuing with available model: {retrain_error}")
            
            # 7. Launch hourly prediction code and pass IDs dynamically
            import predict_engine
            predict_engine.run_prediction_pipeline(current_user_id, main_esp_id)
            print("Automatic cycle completed successfully for this user!")
        except Exception as e:
            print(f"Error running prediction engine: {e}")
    
    # 8. Database cleanup (performed once for the entire system after the loop to save resources)
    print("\n[Cleanup] Cleaning up predictions table from very old predictions...")
    try:
        time_threshold = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        supabase.table("predictions").delete().lt("prediction_time", time_threshold).execute()
        print("Old records cleaned up successfully!")
    except Exception as clean_error:
        print(f"Warning: Failed to clean predictions table: {clean_error}")

if __name__ == "__main__":
    print("Starting the upgraded maestro in the background as (Admin Service)...")
    aggregate_and_predict()
    schedule.every().hour.at(":00").do(aggregate_and_predict)
    while True:
        schedule.run_pending()
        time.sleep(1)