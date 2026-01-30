import requests
import time
import random

# رابط السيرفر المحلي (تأكد إن السيرفر شغال)
SERVER_URL = "http://127.0.0.1:5000/data"

def send_reading(power, pf, device_name_hint):
    """
    دالة بتبعت قراءة للسيرفر كأنها جاية من ESP32
    """
    # حساب التيار تقريباً بناء على الباور (P = V * I * PF)
    voltage = 220 + random.uniform(-2, 2) # فولت 220 مع شوية تذبذب طبيعي
    current = power / (voltage * pf) if power > 0 else 0
    
    payload = {
        "voltage": round(voltage, 1),
        "current": round(current, 2),
        "power": round(power + random.uniform(-5, 5), 1), # بنضيف تذبذب بسيط للواقعية
        "energy_consumption": 150.5, # رقم تراكمي وهمي
        "frequency": 50.0,
        "pf": pf
    }

    try:
        response = requests.post(SERVER_URL, json=payload)
        if response.status_code == 200:
            print(f"📡 Sent: {power}W ({device_name_hint}) -> Server: OK")
        else:
            print(f"⚠️ Server Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("💡 تلميح: هل شغلت ملف run.py؟")

# ==========================================
# سيناريو العرض (The Story Scenario)
# ==========================================
print("🚀 Starting Virtual ESP32 Simulator...")
print("1. Idle Mode (No devices)")
print("2. Kettle Mode (High Power)")
print("3. AC Mode (Medium Power + Inductive)")

while True:
    print("\n--- Choose Scenario ---")
    print(" [1] وضع الخمول (Idle)")
    print(" [2] تشغيل الكاتل (Kettle - 1500W)")
    print(" [3] تشغيل تكييف (AC - 2000W)")
    print(" [4] تشغيل غسالة (Washing - 300W)")
    choice = input("👉 Select Mode (1-4): ")

    duration = 10 # عدد الثواني اللي هيفضل يبعت فيها الداتا دي
    
    target_power = 0
    target_pf = 1.0
    hint = "Idle"

    if choice == '1':
        target_power = 2
        target_pf = 0.8
        hint = "Idle"
    elif choice == '2':
        target_power = 1500
        target_pf = 0.99 # الكاتل مقاومة صرفة تقريباً
        hint = "Kettle"
    elif choice == '3':
        target_power = 2200
        target_pf = 0.85 # التكييف فيه موتور فالباور فاكتور أقل
        hint = "AC"
    elif choice == '4':
        target_power = 300
        target_pf = 0.75
        hint = "Washing Machine"
    else:
        print("❌ اختيار غير صحيح")
        continue

    print(f"\n🔄 Running {hint} scenario for {duration} seconds...")
    
    # حلقة إرسال مستمرة لمدة معينة
    for _ in range(duration):
        send_reading(target_power, target_pf, hint)
        time.sleep(1) # استنى ثانية بين كل قراءة (زي الحقيقي)
