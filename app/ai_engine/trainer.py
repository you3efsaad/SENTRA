import pandas as pd
import os
from app.ai_engine.core import NILMEngine

def train_from_csv(files_dict):
    """
    تدريب الموديل على ملفات CSV حتى لو ناقصة بيانات (زي الباور فاكتور).
    """
    # تهيئة المحرك
    engine = NILMEngine() 
    
    print("🚀 Starting Pre-training (Smart Mode)...")

    for device_name, filepath in files_dict.items():
        if not os.path.exists(filepath):
            print(f"⚠️ File not found: {filepath}")
            continue

        print(f"   -> Training on {device_name}...")
        try:
            # 1. قراءة الملف
            # بنحاول نقرأ العناوين، لو فشل بنقرأ من غير هيدر
            try:
                df = pd.read_csv(filepath)
            except:
                df = pd.read_csv(filepath, header=None)

            # 2. توحيد أسماء العواميد (Normalization)
            # بنخلي كله lower case عشان نتجنب مشاكل Power vs power
            df.columns = [str(c).lower().strip() for c in df.columns]

            # لو ملقاش كلمة power، يدور على العمود الأول ويعتبره هو الباور
            if 'power' not in df.columns:
                # لو الملف مفيهوش هيدر، غالباً العمود 0 هو الباور
                if 0 in df.columns: df.rename(columns={0: 'power'}, inplace=True)
                # لو فيه عمود اسمه 'w' أو 'active'
                elif 'w' in df.columns: df.rename(columns={'w': 'power'}, inplace=True)
                elif 'active' in df.columns: df.rename(columns={'active': 'power'}, inplace=True)

            # 3. التحقق النهائي قبل البدء
            if 'power' not in df.columns:
                print(f"      ❌ Skipping {device_name}: Could not find 'power' column.")
                continue

            # تنظيف الداتا من القيم الصفرية
            df = df[df['power'] > 6] 
            
            count = 0
            for _, row in df.iterrows():
                # === هنا الحل الذكي لمشكلة الباور فاكتور ===
                # لو العمود موجود خده، لو مش موجود افترض إنه 0.95 (قيمة متوسطة للأجهزة المنزلية)
                if 'pf' in df.columns:
                    pf = row['pf']
                elif 'power_factor' in df.columns:
                    pf = row['power_factor']
                else:
                    pf = 0.95 # Default Value (افتراضي)

                # التأكد إن القيم أرقام مش نصوص
                try:
                    p_val = float(row['power'])
                    pf_val = float(pf)
                except:
                    continue # فوت السطر ده لو بايظ

                x = {'power': p_val, 'pf': pf_val}
                
                # 1. الموديل يتعلم
                engine.model.learn_one(x)
                
                # 2. نربط الكلاستر ده باسم الجهاز
                cluster_id = engine.model.predict_one(x)
                engine.cluster_names[cluster_id] = device_name
                count += 1
            
            print(f"      ✅ Processed {count} records for {device_name} (PF assumed 0.95 if missing)")

        except Exception as e:
            print(f"❌ Error processing {device_name}: {e}")

    # حفظ الموديل النهائي
    engine.save_model()
    print(f"💾 Training Complete. Model saved to {engine.model_path}")
    print(f"🧠 Learned Clusters Map: {engine.cluster_names}")
