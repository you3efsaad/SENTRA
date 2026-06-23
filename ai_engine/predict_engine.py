import os
import joblib
import holidays
import pandas as pd
import numpy as np
import torch
from datetime import timedelta, datetime, timezone
from supabase import create_client, Client
from darts.models import TFTModel
from darts import TimeSeries

# Set up connection to Supabase
SUPABASE_URL = "https://wtsfngscmtmywcklplhj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind0c2ZuZ3NjbXRteXdja2xwbGhqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjEzNDQ0MSwiZXhwIjoyMDg3NzEwNDQxfQ.wYesuGasSOKtuvDwXJdQBZPY4MkTqVsKwKOGmjBtCBA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_prediction_pipeline(current_user_id, current_esp_id):
    print("Initializing environment and bypassing security and version restrictions...")
    print(f"Running prediction for current user | Device: ESP-{current_esp_id}")
    
    # --- Disable new security restrictions in PyTorch 2.6 ---
    original_torch_load = torch.load
    def patched_torch_load(*args, **kwargs):
        kwargs['weights_only'] = False
        checkpoint = original_torch_load(*args, **kwargs)
        if isinstance(checkpoint, dict) and "hyper_parameters" in checkpoint:
            checkpoint["hyper_parameters"].pop("skip_interpolation", None)
        return checkpoint
    torch.load = patched_torch_load
    # -------------------------------------------------------------------------
    
    # [Core Modification]: Define load paths dynamically based on the current user_id
    global_model_path = "tft_specialized_house3.pkl"
    global_scaler_path = "scaler3.gz"
    
    user_model_path = f"tft_{current_user_id}.pkl"
    user_scaler_path = f"scaler_{current_user_id}.gz"
    
    # Auto-check: If the user has a custom optimized model, load it; otherwise, temporarily fallback to the global model
    if os.path.exists(user_model_path) and os.path.exists(user_scaler_path):
        print(f"[Personalized Mode] Loading the unique custom model for user: {current_user_id}")
        model = TFTModel.load(user_model_path)
        scaler = joblib.load(user_scaler_path)
    else:
        print("[Global Baseline Mode] New user, loading the unified global system model...")
        model = TFTModel.load(global_model_path)
        scaler = joblib.load(global_scaler_path)
    
    country_holidays = holidays.Egypt()

    print(f"Fetching historical data for device {current_esp_id} from house_3 table...")
    response = supabase.table("house_3") \
        .select("*") \
        .eq("user_id", current_user_id) \
        .order("Time", desc=True) \
        .limit(168).execute()
        
    df = pd.DataFrame(response.data)
    if df.empty:
        print(f"Error: No historical data found in the table for user {current_user_id}!")
        return
        
    df = df.sort_values(by="Time").reset_index(drop=True)
    df["Time"] = pd.to_datetime(df["Time"]).dt.tz_localize(None)
    
    # =========================================================================
    # Handle time gaps and link to the current real-time in memory (RAM)
    # =========================================================================
    now_egypt = datetime.now(timezone.utc) + timedelta(hours=3)
    current_hour = now_egypt.replace(minute=0, second=0, microsecond=0, tzinfo=None)
    
    start_time = df["Time"].min()
    full_time_range = pd.date_range(start=start_time, end=current_hour, freq='h')
    
    df = df.set_index("Time")
    df = df.reindex(full_time_range) 
    df.index.name = "Time"
    
    # Linear interpolation for small gaps, and seasonal interpolation (repeating yesterday's pattern) for deep sensor gaps
    df = df.interpolate(method='linear', limit=2)
    df = df.fillna(df.shift(24))
    df = df.bfill().ffill().reset_index()
    
    # Ensure exactly 168 hours are passed to Darts to protect matrix dimensions
    df = df.tail(168).reset_index(drop=True)
    # =========================================================================

    print("Processing data and extracting time covariates (Preprocessing)...")
    scaled_features = scaler.transform(df[["Aggregate", "Appliance1", "Appliance2", "Appliance3", "Appliance4", "Appliance5", "Appliance6", "Appliance7", "Appliance8", "Appliance9"]])
    df["Aggregate_scaled"] = scaled_features[:, 0]

    target_series = TimeSeries.from_dataframe(df, time_col="Time", value_cols="Aggregate_scaled", fill_missing_dates=True, freq='h')

    static_df = pd.DataFrame({"id": [3]})
    last_time = df["Time"].max()
    
    all_dates = pd.date_range(start=df["Time"].min(), end=last_time + pd.Timedelta(hours=24), freq='h')
    
    cov_df = pd.DataFrame({"Time": all_dates})
    cov_df["day"] = cov_df["Time"].dt.dayofweek
    cov_df["week"] = cov_df["Time"].dt.isocalendar().week.astype(int)
    cov_df["month"] = cov_df["Time"].dt.month
    cov_df["is_holiday"] = cov_df["Time"].apply(lambda x: 1 if x in country_holidays else 0)

    for i in range(1, 11):
        cov_df[f"extra_{i}"] = 0
    
    feature_cols = ["day", "week", "month", "is_holiday"] + [f"extra_{i}" for i in range(1, 11)]
    future_covariates = TimeSeries.from_dataframe(cov_df, time_col="Time", value_cols=feature_cols, fill_missing_dates=True, freq='h')

    target_series = target_series.with_static_covariates(static_df)
    future_covariates = future_covariates.with_static_covariates(static_df)
    
    print("Predicting using the full time range (past + future)...")
    predictions_scaled = model.predict(n=24, series=target_series, future_covariates=future_covariates)
    
    pred_df_scaled = pd.DataFrame({
        "Time": predictions_scaled.time_index,
        "Aggregate_scaled": predictions_scaled.values().flatten()
    })

    future_times = [last_time + timedelta(hours=i) for i in range(1, 25)]
    pred_df_scaled["Time"] = future_times 

    # Inverse transform and revert numbers to their normal values in Watts
    dummy_array = np.zeros((len(pred_df_scaled), 10))
    dummy_array[:, 0] = pred_df_scaled["Aggregate_scaled"]
    unscaled_features = scaler.inverse_transform(dummy_array)
    pred_df_scaled["Aggregate_real"] = unscaled_features[:, 0]

    # Calculate dynamic threshold for early warnings
    historical_mean = df["Aggregate"].mean()
    historical_std = df["Aggregate"].std()
    dynamic_threshold = historical_mean + (2 * historical_std)
    print(f"Calculated dynamic threshold for abnormal consumption: {dynamic_threshold:.2f}")

    predictions_to_insert = []
    has_anomaly = False
    max_predicted_value = 0.0
    anomaly_hours = []

    for index, row in pred_df_scaled.iterrows():
        if pd.isna(row["Aggregate_real"]):
            continue 
        
        predicted_val_real = float(row["Aggregate_real"])
        is_alert_triggered = bool(predicted_val_real > dynamic_threshold)
        
        if is_alert_triggered:
            has_anomaly = True
            if predicted_val_real > max_predicted_value:
                max_predicted_value = predicted_val_real
            
            hour_str = row["Time"].strftime('%I:00 %p') 
            if hour_str not in anomaly_hours:
                anomaly_hours.append(hour_str)
        
        # Save prediction stamped with the unique user_id to ensure complete data isolation
        predictions_to_insert.append({
            "prediction_time": str(row["Time"]),
            "predicted_value": predicted_val_real,
            "is_alert": is_alert_triggered,
            "user_id": current_user_id
        })
    
    if predictions_to_insert:
        print(f"Saving {len(predictions_to_insert)} new predictions into the predictions table...")
        supabase.table("predictions").insert(predictions_to_insert).execute()
        print("Predictions saved successfully!")
    else:
        print("Warning: No predictions were saved because the list is empty!")

    if has_anomaly:
        print("Alert: Reading exceeds the threshold! Sending notification to notifications table...")
        hours_text = ", ".join(anomaly_hours)
        alert_message = (f"Alert: Expected abnormal consumption detected exceeding the threshold ({dynamic_threshold:.2f}). "
                         f"Maximum predicted peak is {max_predicted_value:.2f}. "
                         f"Hours expected to increase: [{hours_text}]. Please rationalize consumption.")
        
        warning_notification = {
            "user_id": current_user_id,
            "title": "ESP - ABNORMAL USAGE ALERT",
            "message": alert_message,
            "type": "info",
            "is_read": False,
            "espid": current_esp_id
        }
        supabase.table("notifications").insert(warning_notification).execute()
        print("Upgraded warning notification logged successfully!")
    else:
        print("Expected consumption is within normal limits, no warnings.")

if __name__ == "__main__":
    test_user = "7889e6d4-9136-4d14-9a47-d29c66d8334c"
    test_esp = 12253
    run_prediction_pipeline(test_user, test_esp)