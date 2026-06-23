import os
import joblib
import pandas as pd
import numpy as np
import torch
from supabase import create_client, Client
from darts import TimeSeries
from darts.models import TFTModel

# Set up connection to Supabase
SUPABASE_URL = "https://wtsfngscmtmywcklplhj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind0c2ZuZ3NjbXRteXdja2xwbGhqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjEzNDQ0MSwiZXhwIjoyMDg3NzEwNDQxfQ.wYesuGasSOKtuvDwXJdQBZPY4MkTqVsKwKOGmjBtCBA"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_periodic_retraining(current_user_id):
    print(f"\n[Self-Correction] Starting periodic update cycle for user: {current_user_id}...")
    
    # --- Bypass PyTorch security restrictions ---
    original_torch_load = torch.load
    def patched_torch_load(*args, **kwargs):
        kwargs['weights_only'] = False
        checkpoint = original_torch_load(*args, **kwargs)
        if isinstance(checkpoint, dict) and "hyper_parameters" in checkpoint:
            checkpoint["hyper_parameters"].pop("skip_interpolation", None)
        return checkpoint
    torch.load = patched_torch_load
    # ----------------------------------

    global_model_path = "tft_specialized_house3.pkl"
    global_scaler_path = "scaler3.gz"
    
    user_model_path = f"tft_{current_user_id}.pkl"
    user_scaler_path = f"scaler_{current_user_id}.gz"
    
    # Check and determine the model's origin to start Continual Learning
    if os.path.exists(user_model_path) and os.path.exists(user_scaler_path):
        print("Loading the user's previous custom model to update its advanced weights...")
        model = TFTModel.load(user_model_path)
        scaler = joblib.load(user_scaler_path)
    elif os.path.exists(global_model_path) and os.path.exists(global_scaler_path):
        print("First-time customization! Loading the global model to start fine-tuning it based on current house data...")
        model = TFTModel.load(global_model_path)
        scaler = joblib.load(global_scaler_path)
    else:
        print("Base model not found in the current runtime server database!")
        return

    # Fetch the latest stable historical data period (last 30 days = 720 hourly readings) completely isolated for the current user
    print(f"Fetching the last 720 hourly readings from the house_3 table for user {current_user_id}...")
    response = supabase.table("house_3") \
        .select("*") \
        .eq("user_id", current_user_id) \
        .order("Time", desc=True) \
        .limit(720).execute()
        
    df = pd.DataFrame(response.data)
    
    if df.empty or len(df) < 168:
        print("Available real data for this user is insufficient for independent individual training (less than a week)!")
        return

    df = df.sort_values(by="Time").reset_index(drop=True)
    df["Time"] = pd.to_datetime(df["Time"]).dt.tz_localize(None)

    print("Preparing data and recalibrating scale values (Adaptive Scaling)...")
    df['is_weekend'] = (df["Time"].dt.dayofweek >= 5).astype(int)
    
    # Refit and update the Scaler values to adapt to seasonal changes for the current user
    scaler.fit(df[["Aggregate", "Appliance1", "Appliance2", "Appliance3", "Appliance4", "Appliance5", "Appliance6", "Appliance7", "Appliance8", "Appliance9"]])
    joblib.dump(scaler, user_scaler_path)
    print("Scaler file updated, calibrated, and newly adapted version saved successfully!")
    
    scaled_features = scaler.transform(df[["Aggregate", "Appliance1", "Appliance2", "Appliance3", "Appliance4", "Appliance5", "Appliance6", "Appliance7", "Appliance8", "Appliance9"]])
    df["Aggregate_scaled"] = scaled_features[:, 0]
    
    # Code protection: Completely exclude the text identifier user_id from the mathematical Features to prevent program crash in Darts
    features = [col for col in df.columns if col not in ["Time", "Unix", "Aggregate", "Aggregate_scaled", "user_id"]]

    target_series = TimeSeries.from_dataframe(df, time_col="Time", value_cols="Aggregate_scaled", freq='h')
    covariates = TimeSeries.from_dataframe(df, time_col="Time", value_cols=features, freq='h')

    static_df = pd.DataFrame({"id": [3]})
    target_series = target_series.with_static_covariates(static_df)
    covariates = covariates.with_static_covariates(static_df)

    print("Starting rapid Fine-Tuning process to update smart weights (3 epochs only)...")
    model.trainer_params = {
        "accelerator": "auto",
        "max_epochs": 3,
        "enable_checkpointing": False,
        "logger": False 
    }

    # Set the model to learn from the new specific pattern of this house
    model.fit(
        series=target_series,
        future_covariates=covariates,
        verbose=True
    )

    # Save the customized individual model with the user_id permanently on the runtime server
    model.save(user_model_path)
    print(f"[Success] Individual custom model for the user saved successfully in file: {user_model_path}")

if __name__ == "__main__":
    test_user = "7889e6d4-9136-4d14-9a47-d29c66d8334c"
    run_periodic_retraining(test_user)