import pickle
import os
from river import cluster
import time

class NILMEngine:
    def __init__(self, model_path='app/ai_engine/model_state.pkl'):
        self.model_path = model_path
        self.model = None
        self.cluster_names = {} 
        self.readings_count = 0  # عداد للقراءات
        self.last_save_time = time.time() # وقت آخر حفظ
        self.SAVE_INTERVAL = 60  # احفظ كل 60 ثانية (أو 60 قراءة)
        
        self.load_model() 

    def load_model(self):
        """تحميل الموديل والأسماء"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.cluster_names = data['labels']
                print(f"✅ AI Model Loaded.")
            except Exception as e:
                print(f"⚠️ Error loading model: {e}. Starting fresh.")
                self.create_new_model()
        else:
            self.create_new_model()

    def create_new_model(self):
        self.model = cluster.KMeans(n_clusters=14, halflife=0.5, sigma=10)
        self.cluster_names = {}

    def save_model(self):
        """حفظ الموديل على الهارد"""
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'labels': self.cluster_names
                }, f)
            print("💾 AI Model Checkpoint Saved.")
            self.last_save_time = time.time()
            self.readings_count = 0
        except Exception as e:
            print(f"❌ Error saving model: {e}")

    def process_reading(self, power, pf):
        """
        الدالة الرئيسية: تستقبل القراءة -> تتوقع -> تتعلم -> تحفظ (بذكاء)
        """
        if power < 5: return "Idle", -1 

        x = {'power': float(power), 'pf': float(pf)}

        # 1. التوقع
        cluster_id = self.model.predict_one(x)
        device_name = self.cluster_names.get(cluster_id, f"Unknown Device #{cluster_id}")

        # 2. التعلم (في الرامات - كل مرة)
        self.model.learn_one(x)
        self.readings_count += 1
        
        # 3. الحفظ الذكي (Smart Save)
        # نحفظ لو فات 60 قراءة (تقريباً دقيقة) أو فات 60 ثانية
        current_time = time.time()
        if self.readings_count >= self.SAVE_INTERVAL or (current_time - self.last_save_time) > self.SAVE_INTERVAL:
            self.save_model()

        return device_name, cluster_id

    def update_label(self, cluster_id, new_name):
        self.cluster_names[cluster_id] = new_name
        self.save_model() # التسمية لازم تتحفظ فوراً عشان المستخدم ميضايقش
        print(f"🏷️ Label Updated: Cluster {cluster_id} -> {new_name}")

    