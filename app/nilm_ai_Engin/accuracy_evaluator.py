import torch
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error

from .GRU_BERT_model import GRUBERT 
from .threshold import Threshold

class ModelArgs:
    def __init__(self, window_size):
        self.window_size = window_size
        self.drop_out = 0.1
        self.output_size = 1

class AccuracyEvaluator:
    def __init__(self, model_path, window_size=480):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.window_size = window_size
        
        args = ModelArgs(window_size=self.window_size)
        self.model = GRUBERT(args).to(self.device)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()

    def create_causal_windows(self, sequence):
        windows = []
        for i in range(self.window_size - 1, len(sequence)):
            window = sequence[i - self.window_size + 1 : i + 1]
            windows.append(window)
        return np.array(windows)

    def evaluate(self, matched_df):
        aggregate = matched_df['aggregate_power'].values
        ground_truth = matched_df['ground_truth_power'].values

        # FIX 1: Protect against small data arrays
        if len(aggregate) < self.window_size:
            pad_len = self.window_size - len(aggregate)
            aggregate = np.pad(aggregate, (pad_len, 0), 'constant')
            ground_truth = np.pad(ground_truth, (pad_len, 0), 'constant')

        X = self.create_causal_windows(aggregate)
        
        # FIX 2: Standardize type to Double
        X = torch.tensor(X, dtype=torch.float64).to(self.device)
        
        y_true_power = ground_truth[self.window_size - 1:]

        predictions = []
        with torch.no_grad():
            batch_size = 128
            for i in range(0, len(X), batch_size):
                batch_X = X[i:i + batch_size]
                preds = self.model(batch_X)
                
                preds_last_point = preds[:, -1, :]
                predictions.extend(preds_last_point.cpu().numpy().flatten())
                
        y_pred_power = np.array(predictions)
        y_pred_power = np.maximum(y_pred_power, 0.0) 

        if len(y_pred_power) == 0:
            y_pred_power = np.zeros_like(y_true_power)

        # FIX 3: Protect clustering from zero-matrices
        if np.max(y_true_power) < 1.0 and np.max(y_pred_power) < 1.0:
            y_true_state = np.zeros_like(y_true_power)
            y_pred_state = np.zeros_like(y_pred_power)
        else:
            thresh_manager = Threshold(appliances=["App"], method="mp", num_status=2)
            safe_y_true = y_true_power if np.max(y_true_power) > 0 else y_true_power + 1e-5
            thresh_manager.update_appliance_threshold(safe_y_true, "App")

            y_true_reshaped = y_true_power.reshape(-1, 1)
            y_pred_reshaped = y_pred_power.reshape(-1, 1)

            if np.max(y_pred_reshaped) < 1.0:
                y_pred_state = np.zeros_like(y_pred_power).flatten()
            else:
                y_pred_state = thresh_manager.power_to_status(y_pred_reshaped).flatten()
                
            y_true_state = thresh_manager.power_to_status(y_true_reshaped).flatten()

        on_off_accuracy = accuracy_score(y_true_state, y_pred_state)
        f1 = f1_score(y_true_state, y_pred_state, zero_division=0)
        mae = mean_absolute_error(y_true_power, y_pred_power)
        
        total_true_energy = np.sum(y_true_power)
        total_pred_energy = np.sum(y_pred_power)
        sae = abs(total_pred_energy - total_true_energy) / (total_true_energy + 1e-9)

        return {
            "on_off_accuracy_percent": round(on_off_accuracy * 100, 2),
            "f1_score": round(f1, 4),
            "mean_absolute_error": round(mae, 2),
            "signal_aggregate_error": round(sae, 4)
        }