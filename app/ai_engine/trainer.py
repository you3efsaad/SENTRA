import pandas as pd
import os
from app.ai_engine.core import NILMEngine

def train_from_csv(files_dict):
    """
    files_dict: قاموس فيه اسم الجهاز ومسار الملف
    Example: {'AC': 'CSV/AC.csv'}
    """
    # تهيئة المحرك (سيقوم بالتحميل أو الإنشاء)
    engine = NILMEngine() 
    
    print("🚀 Starting Pre-training from CSV files...")

    for device_name, filepath in files_dict.items():
        if not os.path.exists(filepath):
            print(f"⚠️ File not found: {filepath}")
            continue

        print(f"   -> Training on {device_name}...")
        try:
            # محاولة قراءة مرنة (بهيدر أو بدون)
            try:
                df = pd.read_csv(filepath)
                if 'power' not in df.columns:
                    df = pd.read_csv(filepath, header=None)
                    df.rename(columns={0: 'power', 1: 'pf'}, inplace=True) # عدل الأرقام حسب شكل ملفك
            except:
                print(f"      Skipping {filepath} (Format Error)")
                continue

            # تنظيف الداتا
            if 'power' in df.columns:
                df = df[df['power'] > 10] # تجاهل القيم الصغيرة
                
                count = 0
                for _, row in df.iterrows():
                    pf = row['pf'] if 'pf' in df.columns else 0.9
                    x = {'power': float(row['power']), 'pf': float(pf)}
                    
                    # 1. تعلم
                    engine.model.learn_one(x)
                    
                    # 2. سجل الاسم للكلاستر ده
                    cluster_id = engine.model.predict_one(x)
                    engine.cluster_names[cluster_id] = device_name
                    count += 1
                
                print(f"      Processed {count} records for {device_name}")

        except Exception as e:
            print(f"❌ Error processing {device_name}: {e}")

    # حفظ الموديل النهائي بعد التدريب
    engine.save_model()
    print(f"✅ Training Complete. Model saved to {engine.model_path}")
    print(f"🧠 Learned Clusters: {engine.cluster_names}")