import os
import joblib
import pandas as pd
import numpy as np
import torch
from supabase import create_client, Client
from darts import TimeSeries
from darts.models import TFTModel
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_periodic_retraining():
    print("🔄 [Self-Correction] Starting periodic retraining and model improvement cycle...")
    
    original_torch_load = torch.load
    def patched_torch_load(*args, **kwargs):
        kwargs['weights_only'] = False
        checkpoint = original_torch_load(*args, **kwargs)
        if isinstance(checkpoint, dict) and "hyper_parameters" in checkpoint:
            checkpoint["hyper_parameters"].pop("skip_interpolation", None)
        return checkpoint
    torch.load = patched_torch_load
    # ----------------------------------

    model_path = "tft_specialized_house3.pkl"
    scaler_path = "scaler3.gz"
    
    if not os.path.exists(model_path):
        print(f"❌ Model not found at: {model_path}")
        return

    model = TFTModel.load(model_path)
    scaler = joblib.load(scaler_path)
    print("🧠 Current model and Scaler loaded successfully...")

    print("📅 Fetching the last 720 hourly readings from house_3 table to retrain the model...")
    response = supabase.table("house_3").select("*").order("Time", desc=True).limit(720).execute()
    df = pd.DataFrame(response.data)
    
    if df.empty or len(df) < 168:
        print("❌ Insufficient data available to perform periodic retraining!")
        return

    df = df.sort_values(by="Time").reset_index(drop=True)
    df["Time"] = pd.to_datetime(df["Time"])

    print("📊 Preparing and preprocessing new data...")
    df['is_weekend'] = (df["Time"].dt.dayofweek >= 5).astype(int)
    
    scaler.fit(df[["Aggregate", "Appliance1", "Appliance2", "Appliance3", "Appliance4", "Appliance5", "Appliance6", "Appliance7", "Appliance8", "Appliance9"]])
    joblib.dump(scaler, scaler_path)
    print("✅ Scaler file updated, calibrated, and changes saved successfully!")
    
    scaled_features = scaler.transform(df[["Aggregate", "Appliance1", "Appliance2", "Appliance3", "Appliance4", "Appliance5", "Appliance6", "Appliance7", "Appliance8", "Appliance9"]])
    df["Aggregate_scaled"] = scaled_features[:, 0]
    
    features = [col for col in df.columns if col not in ["Time", "Unix", "Aggregate", "Aggregate_scaled"]]

    target_series = TimeSeries.from_dataframe(df, time_col="Time", value_cols="Aggregate_scaled", freq='h')
    covariates = TimeSeries.from_dataframe(df, time_col="Time", value_cols=features, freq='h')

    static_df = pd.DataFrame({"id": [3]})
    target_series = target_series.with_static_covariates(static_df)
    covariates = covariates.with_static_covariates(static_df)

    print("🏋️ Tuning the model to learn and adjust weights based on recent errors...")
    model.trainer_params = {
        "accelerator": "auto",
        "max_epochs": 3,  
        "enable_checkpointing": False,
        "logger": False 
    }

    model.fit(
        series=target_series,
        future_covariates=covariates,
        verbose=True
    )

    model.save(model_path)
    print(f"🎯 [Success] Model updated successfully with the latest weights in file: {model_path}")

if __name__ == "__main__":
    run_periodic_retraining()