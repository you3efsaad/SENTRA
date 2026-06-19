from datetime import datetime
from collections import deque

esps = {}
WINDOW_SIZE = 480

def init_esp_state(espid):
    if espid not in esps:
        esps[espid] = {
            "is_main": False, 
            "power_buffer": deque([0.0] * WINDOW_SIZE, maxlen=WINDOW_SIZE),
            "data": {
                "user_id": None,
                "voltage": 0,
                "current": 0,
                "power": 0,
                "energy": 0,
                "frequency": 0,
                "pf": 0,
                "total_dashboard_cost": 0.0,
                "ac_device_name": "Idle",
                "ai_device_name": "Idle",
                "ai_cluster_id": -1
            },
            "control": {
                "latest_command": "on",
                "current_limit": 10.0,
                "power_limit": 5000.0
            },
            "timer": {
                "end_time": None,
                "paused_remaining": None
            },
            "settings": {
                "budget_egp": 0.0,
                "budget_kwh": 0.0,
                "budget_days": 0,
                "consumed_since_budget": 0.0,
                "flag_budget_50": False,
                "flag_budget_75": False,
                "flag_budget_100": False,
                "flag_current_limit": False,
                "flag_power_limit": False,
                "flag_high_voltage": False,
                "flag_low_voltage": False,
                "budget_start_time": None,
                "user_segment": 1,
                "budget_locked": False
            },
            "last_update_time": datetime.now(),
            "last_db_insert_time": None
        }

supabase = None
ai_engine = None
mail = None