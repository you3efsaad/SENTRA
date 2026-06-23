# import pandas as pd
# from supabase import create_client, Client
# import time
# from datetime import datetime
# import random

# SUPABASE_URL = "https://wtsfngscmtmywcklplhj.supabase.co"
# SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind0c2ZuZ3NjbXRteXdja2xwbGhqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjEzNDQ0MSwiZXhwIjoyMDg3NzEwNDQxfQ.wYesuGasSOKtuvDwXJdQBZPY4MkTqVsKwKOGmjBtCBA"

# supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# USER_ID = "7889e6d4-9136-4d14-9a47-d29c66d8334c"
# MAIN_ESP_ID = 68393

# print("Loading data from CLEAN_House2.csv...")
# file_path = "House_2.csv" 
# df = pd.read_csv(file_path)

# df = df.head(5000) 

# print("\n" + "="*70)
# print("Starting Real-Time Sensor Simulation (NILM Testing Mode)")
# print("Interval: 6 seconds between readings")
# print("="*70 + "\n")

# for index, row in df.iterrows():
#     current_time = datetime.now().isoformat()
    
#     record = {
#         "user_id": USER_ID,
#         "espid": MAIN_ESP_ID,
#         "timestamp": current_time,
#         "device_name": "TOTAL (MAIN)",
#         "voltage": round(random.uniform(220.0, 240.0), 1),
#         "current": round(row['Aggregate'] / 230.0, 2), 
#         "power": row['Aggregate'],
#         "energy_consumption": row['Aggregate'] / 1000.0,
#         "frequency": 50.0,
#         "pf": 0.90
#     }
    
#     try:
#         supabase.table("user_readings").insert(record).execute()
#         print(f"[{current_time}] Uploaded -> Power: {row['Aggregate']} W | Index: {index}")
#     except Exception as e:
#         print(f"Error uploading record at index {index}: {e}")
    
#     time.sleep(6)
import pandas as pd
from supabase import create_client, Client
import time
from datetime import datetime, timedelta

SUPABASE_URL = "https://wtsfngscmtmywcklplhj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind0c2ZuZ3NjbXRteXdja2xwbGhqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjEzNDQ0MSwiZXhwIjoyMDg3NzEwNDQxfQ.wYesuGasSOKtuvDwXJdQBZPY4MkTqVsKwKOGmjBtCBA"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

USER_ID = "7889e6d4-9136-4d14-9a47-d29c66d8334c"
MAIN_ESP_ID = 68393

print("Loading data from CLEAN_House2.csv...")
file_path = "House_2.csv" 
df = pd.read_csv(file_path)

spike_indices = df[df['Aggregate'] > 2400].index

if len(spike_indices) > 0:
    target_idx = spike_indices[0]
else:
    target_idx = 500 

history_start = max(0, target_idx - 480)
history_df = df.iloc[history_start:target_idx]
future_df = df.iloc[target_idx:target_idx + 40]

print("\n" + "="*70)
print(f"Targeting high power event at index: {target_idx}")
print("1. Injecting 480 continuous historical points to fix the AI window...")
records = []
base_time = datetime.now() - timedelta(minutes=10)

for i, row in history_df.iterrows():
    base_time += timedelta(seconds=1)
    records.append({
        "user_id": USER_ID,
        "espid": MAIN_ESP_ID,
        "timestamp": base_time.isoformat(),
        "device_name": "TOTAL (MAIN)",
        "voltage": 230.0,
        "current": round(row['Aggregate'] / 230.0, 2),
        "power": row['Aggregate'],
        "energy_consumption": row['Aggregate'] / 1000.0,
        "frequency": 50.0,
        "pf": 0.90
    })

# رفع البيانات ببطء لتجنب انقطاع الاتصال
batch_size = 50
for i in range(0, len(records), batch_size):
    try:
        supabase.table("user_readings").insert(records[i:i+batch_size]).execute()
        print(f"Uploaded history batch {i//batch_size + 1}/{(len(records)//batch_size)+1}...")
        time.sleep(1) # راحة للسيرفر
    except Exception as e:
        print(f"Error in batch {i//batch_size + 1}: {e}")

print("AI Window is now clean and continuous!")
print("2. Starting Real-time Spike Simulation (Kettle/Washing Machine)...")
print("="*70 + "\n")

for index, row in future_df.iterrows():
    current_time = datetime.now().isoformat()
    record = {
        "user_id": USER_ID,
        "espid": MAIN_ESP_ID,
        "timestamp": current_time,
        "device_name": "TOTAL (MAIN)",
        "voltage": 220.0,
        "current": round(row['Aggregate'] / 230.0, 2),
        "power": row['Aggregate'],
        "energy_consumption": row['Aggregate'] / 1000.0,
        "frequency": 50.0,
        "pf": 0.90
    }
    
    try:
        supabase.table("user_readings").insert(record).execute()
        print(f"[{current_time}] Uploaded Spike -> Power: {row['Aggregate']} W")
    except Exception as e:
        print(f"Error uploading spike at index {index}: {e}")
        
    time.sleep(3)