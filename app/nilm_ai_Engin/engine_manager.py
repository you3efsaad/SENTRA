import logging
import os
from datetime import datetime, timedelta, timezone

from .data_synchronizer import DataSynchronizer
from .accuracy_evaluator import AccuracyEvaluator
from .fine_tuner import FineTuner

logger = logging.getLogger("SENTRA_Core")

class NILMEngineManager:
    def __init__(self, db_client):
        self.db = db_client
        self.synchronizer = DataSynchronizer(db_client)
        self.fine_tuner = FineTuner()
        
        self.target_accuracy_percent = 85.0 

    def send_notification(self, user_id, title, message, type='info', espid=None):
        notification_data = {
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": type,
            "is_read": False,
            "espid": espid
        }
        self.db.table('notifications').insert(notification_data).execute()

    def process_active_plugs(self):
        logger.info("[MANAGER] Scanning 'safe_power_devices' for is_main=False...")
        response = self.db.table('safe_power_devices').select('*').eq('is_main', False).execute()
        
        if not response.data:
            logger.warning("[MANAGER] No active sub-devices found in DB! Exiting.")
            return

        logger.info("[MANAGER] Found %d sub-devices.", len(response.data))

        for plug in response.data:
            user_id = plug.get('user_id')
            plug_espid = plug.get('espid')
            device_name = plug.get('device_name')
            
            logger.info("[MANAGER] Processing Device: %s (ESP: %s)", device_name, plug_espid)
            
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=7)
            
            logger.debug("[MANAGER] Requesting sync from %s to %s", start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            matched_df = self.synchronizer.fetch_and_match_data(
                user_id, plug_espid, start_date.isoformat(), end_date.isoformat()
            )

            if matched_df is None:
                logger.warning("[MANAGER] Sync returned None for %s. Skipping to next device.", device_name)
                continue
                
            if matched_df.empty:
                logger.warning("[MANAGER] Sync returned EMPTY DataFrame for %s. Skipping to next device.", device_name)
                continue

            logger.info("[MANAGER] Matched %d rows! Triggering fine-tuner...", len(matched_df))
            
            try:
                logger.info("[MANAGER] Initiating Fine-Tuning for %s...", device_name)
                train_result = self.fine_tuner.train(user_id, device_name, matched_df)
                
                if train_result.get("status") == "error":
                    logger.error("[MANAGER] Training Failed: %s", train_result.get('message'))
                    continue
                    
                user_model_path = train_result["model_path"]
                global_model_path = os.path.join(self.fine_tuner.global_models_dir, f"{device_name.lower()}.pth")

                logger.info("[MANAGER] Evaluating GLOBAL model vs FINE-TUNED model...")
                
                evaluator_global = AccuracyEvaluator(model_path=global_model_path)
                metrics_global = evaluator_global.evaluate(matched_df)
                acc_before = metrics_global["on_off_accuracy_percent"]

                evaluator_user = AccuracyEvaluator(model_path=user_model_path)
                metrics_user = evaluator_user.evaluate(matched_df)
                acc_after = metrics_user["on_off_accuracy_percent"]
                
                logger.info("Accuracy BEFORE (Global Model): %.1f%%", acc_before)
                logger.info("Accuracy AFTER (Custom Model): %.1f%%", acc_after)

                if acc_after >= self.target_accuracy_percent:
                    msg = f"AI Training Complete! {device_name} accuracy improved from {acc_before:.1f}% to {acc_after:.1f}%. The model is fully customized for your home."
                    self.send_notification(user_id, "Smart Node Unplug Ready", msg, type="success", espid=plug_espid)
                    self.db.table('safe_power_devices').update({"phase": "COMPLETED"}).eq('espid', plug_espid).execute()
                    logger.info("[MANAGER] Success! Phase updated to COMPLETED.")
                else:
                    msg = f"Training done, but {device_name} accuracy is {acc_after:.1f}% (Global was {acc_before:.1f}%). Please keep the smart node connected for more data."
                    self.send_notification(user_id, "Training Needs More Data", msg, type="warning", espid=plug_espid)
                    
            except Exception as e:
                logger.error("[MANAGER] Pipeline Error for %s: %s", device_name, str(e))