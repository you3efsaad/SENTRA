import logging
import os
import torch
import numpy as np
from torch.utils.data import DataLoader

from .GRU_BERT_model import GRUBERT
from .threshold import Threshold
from .clustering import HierarchicalClustering
from .fine_tuning_dynamcthreshold import ConfigArgs, BERTDataset, NILMDataset, train_finetune

logger = logging.getLogger("SENTRA_Core")

class FineTuner:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.global_models_dir = 'app/nilm_ai_Engin/global_models'
        self.user_models_dir = 'app/nilm_ai_Engin/user_models'
        os.makedirs(self.user_models_dir, exist_ok=True)
        
        self.UK_DALE_MEAN = 418.623901
        self.UK_DALE_STD = 504.039630

        self.APP_CONFIGS = {
            'kettle': {'cutoff': 2850.0, 'min_on': 2, 'min_off': 0},
            'microwave': {'cutoff': 1300.0, 'min_on': 2, 'min_off': 1},
            'fridge': {'cutoff': 400.0, 'min_on': 10, 'min_off': 12},
            'washing machine': {'cutoff': 2300.0, 'min_on': 30, 'min_off': 120}
        }

    def train(self, user_id, device_name, matched_df):
        logger.info("[FINE-TUNER] Booting up user's dynamic threshold engine for %s...", device_name)
        
        device_key = device_name.lower()
        if device_key not in self.APP_CONFIGS:
            device_key = 'fridge'
            
        target_config = self.APP_CONFIGS[device_key]
        
        args = ConfigArgs(
            cutoff=target_config['cutoff'], 
            min_on=target_config['min_on'], 
            min_off=target_config['min_off']
        )
        args.window_size = 480
        args.batch_size = 16
        
        x_raw = matched_df['aggregate_power'].values.astype(np.float64)
        y_raw = matched_df['ground_truth_power'].values.astype(np.float64)
        
        logger.debug("[FINE-TUNER] Calculating dynamic thresholds using %s method...", args.threshold_method)
        try:
            if args.threshold_method in ['vs', 'mp']:
                thresh_manager = Threshold(appliances=[device_name], method=args.threshold_method, num_status=args.n_clusters)
                thresh_manager.update_appliance_threshold(y_raw, device_name)
                
            elif args.threshold_method == 'custom':
                logger.debug("[FINE-TUNER] Using Hierarchical Clustering...")
                hc_model = HierarchicalClustering(distance="average", n_cluster=args.n_clusters)
                hc_model.perform_clustering(y_raw)
                hc_model.compute_thresholds_and_centroids(centroid="median")
                
                thresh_manager = Threshold(appliances=[device_name], method="custom")
                thresh_manager.set_thresholds_and_centroids(
                    np.expand_dims(hc_model.thresh, axis=0),
                    np.expand_dims(hc_model.centroids, axis=0)
                )
                
            args.threshold = thresh_manager.thresholds[0][1]
            logger.info("[FINE-TUNER] Dynamic Threshold locked at: %.2f W", args.threshold)
            
        except Exception as e:
            logger.warning("[FINE-TUNER] Threshold calculation failed (%s), using default cutoff/10.", str(e))
            args.threshold = target_config['cutoff'] / 10.0
            
        y_reshaped = y_raw.reshape(-1, 1)
        try:
            status_array = thresh_manager.power_to_status(y_reshaped).flatten().astype(np.float64)
        except:
            status_array = np.where(y_raw > args.threshold, 1.0, 0.0).astype(np.float64)
        
        x_norm = (x_raw - self.UK_DALE_MEAN) / (self.UK_DALE_STD + 1e-6)
        
        val_end = int((1 - args.val_size) * len(x_norm))
        train_dataset = BERTDataset(x_norm[:val_end], y_raw[:val_end], status_array[:val_end], args.window_size, args.window_stride)
        val_dataset = NILMDataset(x_norm[val_end:], y_raw[val_end:], status_array[val_end:], args.window_size, args.window_size)
        
        train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, pin_memory=True)
        val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, pin_memory=True)

        global_model_path = os.path.join(self.global_models_dir, f"{device_key}.pth")
        user_model_filename = f"{user_id}_{device_name}.pth"
        save_path = os.path.join(self.user_models_dir, user_model_filename)
        
        torch.set_default_dtype(torch.float64)
        model = GRUBERT(args).to(self.device)
        
        try:
            model.load_state_dict(torch.load(global_model_path, map_location=self.device))
            logger.info("[FINE-TUNER] Global weights loaded from %s", global_model_path)
        except Exception as e:
            logger.warning("[FINE-TUNER] Failed to load global weights (%s). Initializing randomly.", str(e))

        logger.info("[FINE-TUNER] Launching train_finetune loop...")
        
        train_finetune(model, train_loader, val_loader, self.device, args, save_path=save_path, epochs=10)
        
        return {"status": "success", "model_path": save_path}