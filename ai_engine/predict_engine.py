import os
import pandas as pd
import joblib 
import holidays 
from datetime import timedelta
from supabase import create_client, Client
from darts.models import TFTModel
from darts import TimeSeries
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_prediction_pipeline():
    current_esp_id = 12253
    current_user_id = "2c273fd1-6d71-46ee-95d6-dd3d77bb8779"
    
    print("🔄 Initializing environment and bypassing security/version constraints...")
    
    import torch
    original_torch_load = torch.load
    
    def patched_torch_load(*args, **kwargs):
        kwargs['weights_only'] = False
        checkpoint = original_torch_load(*args, **kwargs)
        
        if isinstance(checkpoint, dict) and "hyper_parameters" in checkpoint:
            checkpoint["hyper_parameters"].pop("skip_interpolation", None)
            
        return checkpoint
        
    torch.load = patched_torch_load
    # -------------------------------------------------------------------------
    
    print("🧠 Loading Model and Scaler...")
    model = TFTModel.load("tft_specialized_house3.pkl")
    scaler = joblib.load("scaler3.gz")
    
    country_holidays = holidays.Egypt()

    print(f"📅 Fetching historical data for device {current_esp_id} from table house_3...")
    response = supabase.table("house_3").select("*").order("Time", desc=True).limit(168).execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        print("❌ No historical data found in the table!")
        return
        
    df = df.sort_values(by="Time").reset_index(drop=True)
    df["Time"] = pd.to_datetime(df["Time"])
  

    print("📊 Processing data and extracting time variables (Preprocessing)...")
    scaled_features = scaler.transform(df[["Aggregate", "Appliance1", "Appliance2", "Appliance3", "Appliance4", "Appliance5", "Appliance6", "Appliance7", "Appliance8", "Appliance9"]])
    df["Aggregate_scaled"] = scaled_features[:, 0]

    target_series = TimeSeries.from_dataframe(df, time_col="Time", value_cols="Aggregate_scaled")

    static_df = pd.DataFrame({"id": [3]})
    target_series = target_series.with_static_covariates(static_df)
    
    print("🔮 Extracting Future Covariates and running the prediction model (24 hours)...")
    predictions_scaled = model.predict(n=24, series=target_series)
    
    pred_df_scaled = pd.DataFrame(predictions_scaled.values(), columns=["Aggregate_scaled"], index=predictions_scaled.time_index).reset_index()


    import numpy as np
    
    dummy_array = np.zeros((len(pred_df_scaled), 10))
    dummy_array[:, 0] = pred_df_scaled["Aggregate_scaled"]
    unscaled_features = scaler.inverse_transform(dummy_array)
    pred_df_scaled["Aggregate_real"] = unscaled_features[:, 0]
    # ------------------------------------------------------------------------

    historical_mean = df["Aggregate"].mean()
    historical_std = df["Aggregate"].std()
    dynamic_threshold = historical_mean + (2 * historical_std)
    print(f"📉 Calculated dynamic threshold for abnormal consumption: {dynamic_threshold:.2f}")

    predictions_to_insert = []
    has_anomaly = False
    max_predicted_value = 0.0
    anomaly_hours = []

    for index, row in pred_df_scaled.iterrows():
        predicted_val_real = float(row["Aggregate_real"])
        is_alert_triggered = bool(predicted_val_real > dynamic_threshold)
        
        if is_alert_triggered:
            has_anomaly = True
            if predicted_val_real > max_predicted_value:
                max_predicted_value = predicted_val_real
            
            hour_str = row["Time"].strftime('%I:00 %p') # It outputs like this: 05:00 PM
            if hour_str not in anomaly_hours:
                anomaly_hours.append(hour_str)
        
        predictions_to_insert.append({
            "prediction_time": str(row["Time"]),
            "predicted_value": predicted_val_real,
            "is_alert": is_alert_triggered,
            # "espid": current_esp_id
        })
    
    print("🚀 Saving new predictions to the predictions table...")
    supabase.table("predictions").insert(predictions_to_insert).execute()
    print("✅ Successfully saved the 24 predictions!")

    if has_anomaly:
        print("🚨 Detected a reading exceeding the threshold! Sending notification to the notifications table...")
        
        hours_text = ", ".join(anomaly_hours)
        
        alert_message = (f"Alert: Expected abnormal consumption detected exceeding the threshold ({dynamic_threshold:.2f}). "
                         f"Maximum expected peak is {max_predicted_value:.2f}. "
                         f"Expected hours of increase: [{hours_text}]. Please optimize consumption.")
        
        warning_notification = {
            "user_id": current_user_id,
            "title": "ESP - ABNORMAL USAGE ALERT",
            "message": alert_message,
            "type": "info",
            "is_read": False,
            "espid": current_esp_id
        }
        supabase.table("notifications").insert(warning_notification).execute()
        print("🔔 Advanced warning notification logged successfully!")
    else:
        print("🟢 Expected consumption is within normal limits, no warnings.")

if __name__ == "__main__":
    run_prediction_pipeline()