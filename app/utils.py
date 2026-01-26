from datetime import datetime
import app.globals as g

def save_hourly_snapshot():
    """حفظ القراءات في Supabase"""
    try:
        # التأكد إن الـ supabase شغال وإن فيه قراءات تستحق الحفظ
        if g.supabase and (g.latest_data.get('power', 0) > 0 or g.latest_data.get('energy', 0) > 0):
            data = {
                "Timestamp": datetime.now().isoformat(),
                "Voltage(V)": float(g.latest_data.get('voltage', 0)),
                "Current(A)": float(g.latest_data.get('current', 0)),
                "Power(W)": float(g.latest_data.get('power', 0)),
                "Energy Consumption(kWh)": float(g.latest_data.get('energy', 0)),
                "Frequency(Hz)": float(g.latest_data.get('frequency', 0)),
                "Power Factor": float(g.latest_data.get('pf', 0))
            }
            g.supabase.table("energy_usage_hourly").insert(data).execute()
            print(f"[💾] Snapshot saved.")
    except Exception as e:
        print(f"[❌] Error saving snapshot: {e}")

def monitor_background_logic():
    """مراقبة التايمر وفصل الجهاز تلقائياً"""
    try:
        # 1. التايمر
        if g.timer_end_time:
            now = datetime.now()
            if now >= g.timer_end_time:
                print("[⏰] Timer finished. Switching OFF.")
                g.latest_command = 'off'
                g.timer_end_time = None
                if g.timer_paused_remaining:
                    g.timer_paused_remaining = None

        # 2. كشف انقطاع الاتصال (Disconnect)
        # لو فات 15 ثانية من غير تحديث، صفر القراءات
        if (datetime.now() - g.last_update_time).total_seconds() > 15:
             for key in ['voltage', 'current', 'power', 'frequency', 'pf']:
                 g.latest_data[key] = 0
                 
    except Exception as e:
        print(f"[⚠️] Background Logic Error: {e}")