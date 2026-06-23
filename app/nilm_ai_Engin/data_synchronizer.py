import logging
import pandas as pd
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("SENTRA_Core")

class DataSynchronizer:
    def __init__(self, db_client):
        self.db = db_client
        self.training_days = 7
        self.evaluation_days = 3

    def get_plug_status_and_phase(self, user_id, device_name):
        response = self.db.table('safe_power_devices').select('*').eq('user_id', user_id).eq('device_name', device_name).eq('is_main', False).execute()
        
        if not response.data:
            return {"phase": "NO_PLUG", "espid": None}

        plug_espid = response.data[0]['espid']

        first_reading = self.db.table('user_readings').select('timestamp').eq('espid', plug_espid).order('timestamp', desc=False).limit(1).execute()
        
        if not first_reading.data:
            return {"phase": "NO_PLUG", "espid": plug_espid}

        start_time_str = first_reading.data[0]['timestamp']
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        current_time = datetime.now(timezone.utc)
        
        days_elapsed = (current_time - start_time).days

        if days_elapsed < self.training_days:
            return {"phase": "TRAINING_COLLECTION", "espid": plug_espid, "days_left": self.training_days - days_elapsed}
        
        elif days_elapsed == self.training_days:
            return {"phase": "READY_FOR_TRAINING", "espid": plug_espid}
            
        elif self.training_days < days_elapsed <= (self.training_days + self.evaluation_days):
            return {"phase": "EVALUATION", "espid": plug_espid}
            
        else:
            return {"phase": "COMPLETED", "espid": plug_espid}

    def fetch_and_match_data(self, user_id, plug_espid, start_date, end_date):
        logger.info("[SYNC] Fetching Main Meter ID for user %s...", user_id)
        main_device = self.db.table('safe_power_devices').select('espid').eq('user_id', user_id).eq('is_main', True).execute()
        
        if not main_device.data:
            logger.error("[SYNC] No main meter found for user %s!", user_id)
            return None
            
        main_espid = main_device.data[0]['espid']
        logger.debug("[SYNC] Main Meter ESPID: %s", main_espid)

        logger.info("[SYNC] Downloading Main readings & Plug readings...")
        main_readings = self.db.table('user_readings').select('timestamp, power').eq('user_id', user_id).eq('espid', main_espid).gte('timestamp', start_date).lte('timestamp', end_date).limit(50000).execute()
        
        plug_readings = self.db.table('user_readings').select('timestamp, power').eq('user_id', user_id).eq('espid', plug_espid).gte('timestamp', start_date).lte('timestamp', end_date).limit(50000).execute()
        logger.info("[SYNC] Found %d Main readings, and %d Plug readings.", len(main_readings.data), len(plug_readings.data))

        if not main_readings.data or not plug_readings.data:
            logger.warning("[SYNC] Missing data! Cannot merge.")
            return None

        import pandas as pd
        df_main = pd.DataFrame(main_readings.data)
        df_main['timestamp'] = pd.to_datetime(df_main['timestamp'])
        df_main = df_main.rename(columns={'power': 'aggregate_power'}).sort_values('timestamp')

        df_plug = pd.DataFrame(plug_readings.data)
        df_plug['timestamp'] = pd.to_datetime(df_plug['timestamp'])
        df_plug = df_plug.rename(columns={'power': 'ground_truth_power'}).sort_values('timestamp')

        logger.debug("[SYNC] Merging data using merge_asof...")
        matched_df = pd.merge_asof(
            df_main, 
            df_plug, 
            on='timestamp', 
            direction='nearest',
            tolerance=pd.Timedelta(seconds=5)
        ).dropna()
        
        logger.info("[SYNC] Merge complete! Result rows: %d", len(matched_df))
        return matched_df