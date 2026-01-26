from datetime import datetime

# 1. متغيرات الهاردوير والقراءات
latest_data = {
    "voltage": 0,
    "current": 0,
    "power": 0,
    "energy": 0,
    "frequency": 0,
    "pf": 0
}

# 2. متغيرات التحكم
latest_command = "off"
power_limit = 150

# 3. متغيرات التايمر (دول اللي كانوا ناقصين وعاملين المشكلة)
timer_end_time = None
timer_paused_remaining = None  # <-- ده كان ناقص

# 4. متغيرات النظام
last_update_time = datetime.now()  # <-- ده كان ناقص

# 5. كائن قاعدة البيانات
supabase = None