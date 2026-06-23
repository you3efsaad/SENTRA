import logging
import os
import torch
import numpy as np
from .GRU_BERT_model import GRUBERT

logger = logging.getLogger("SENTRA_Core")

class ModelArgs:
    def __init__(self, cutoff):
        self.window_size = 480
        self.drop_out = 0.1
        self.output_size = 1
        self.cutoff = cutoff

class RealTimeNILM:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.window_size = 480
        
        self.uk_dale_mean = 418.623901
        self.uk_dale_std = 504.039630
        
        self.configs = {
            'fridge': {'cutoff': 400.0, 'threshold': 40.0},
            'kettle': {'cutoff': 2850.0, 'threshold': 1000.0},
            'washing_machine': {'cutoff': 2300.0, 'threshold': 50.0}
        }
        self.models_cache = {}

    def get_model(self, user_id, device_name):
        cache_key = f"{user_id}_{device_name}"
        
        if cache_key in self.models_cache:
            return self.models_cache[cache_key]

        if device_name not in self.configs:
            return None

        cutoff = self.configs[device_name]['cutoff']
        args = ModelArgs(cutoff=cutoff)
        model = GRUBERT(args).to(self.device)
        
        user_model_path = f"app/nilm_ai_Engin/user_models/{user_id}_{device_name}.pth"
        global_model_path = f"app/nilm_ai_Engin/global_models/{device_name}.pth"
        
        if os.path.exists(user_model_path):
            model.load_state_dict(torch.load(user_model_path, map_location=self.device))
        else:
            if os.path.exists(global_model_path):
                model.load_state_dict(torch.load(global_model_path, map_location=self.device))
            else:
                logger = logging.getLogger("SENTRA")
                logger.error(f"AI: No model for {device_name}. Aborted.")
                return None
            
        model.eval()
        self.models_cache[cache_key] = model
        return model

    def predict(self, user_id, device_name, aggregate_window):
        if len(aggregate_window) < self.window_size:
            aggregate_window = np.pad(aggregate_window, (self.window_size - len(aggregate_window), 0), 'constant')
        else:
            aggregate_window = aggregate_window[-self.window_size:]

        if device_name.lower() == 'kettle':
            latest_power = float(aggregate_window[-1])
            if latest_power > 1000.0:
                kettle_power = latest_power * 0.98
                return round(kettle_power, 2), 1

        x_norm = (np.array(aggregate_window) - self.uk_dale_mean) / (self.uk_dale_std + 1e-6)
        x_tensor = torch.tensor(x_norm, dtype=torch.float32).unsqueeze(0).to(self.device)

        model = self.get_model(user_id, device_name)
        if not model:
            return 0.0, 0
            
        with torch.no_grad():
            logits = model(x_tensor)
            logits_last_point = logits[:, -1, :]
            
        cutoff = self.configs[device_name]['cutoff']
        threshold = self.configs[device_name]['threshold']
        
        pred_power = (logits_last_point.item() * cutoff)
        
        if pred_power < 5: 
            pred_power = 0.0
        pred_power = min(pred_power, cutoff)
        
        pred_status = 1 if pred_power >= threshold else 0

        return round(pred_power, 2), pred_status