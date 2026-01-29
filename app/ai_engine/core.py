import os
import pickle
from river import cluster
from river import stream
import time

class NILMEngine:
    def __init__(self, model_path='model_state.pkl'):
        # 1. تحديد مكان المجلد الحالي اللي فيه ملف core.py
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. دمج المسار عشان نضمن إننا بنشاور على الملف صح
        # النتيجة هتكون: .../app/ai_engine/model_state.pkl
        self.model_path = os.path.join(base_dir, model_path)
        
        self.model = None
        self.cluster_names = {} 
        self.readings_count = 0  
        self.last_save_time = time.time() 
        
        # إعدادات الموديل (KMeans)
        # n_clusters=5: بنفترض وجود 5 أنواع أجهزة مبدئياً
        # sigma=40: مدى حساسية الكلاستر
        self.kmeans_params = {
            'n_clusters': 13,
            'halflife': 0.4,
            'sigma': 40,
            'mu': 0.1
        }
        
        
        self.load_model()

    def create_new_model(self):
        print("✨ Creating new AI Model...")
        self.model = cluster.KMeans(**self.kmeans_params)
        self.cluster_names = {}

    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data.get("model")
                    self.cluster_names = data.get("names", {})
                print(f"✅ AI Brain Loaded. Known devices: {self.cluster_names}")
            except Exception as e:
                print(f"⚠️ Model file corrupt ({e}). Starting fresh.")
                self.create_new_model()
        else:
            self.create_new_model()

    def save_model(self):
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    "model": self.model,
                    "names": self.cluster_names
                }, f)
            print("💾 AI Memory Saved.")
        except Exception as e:
            print(f"❌ Save failed: {e}")

    def update_label(self, cluster_id, name):
        """تحديث اسم الكلاستر وحفظه"""
        self.cluster_names[int(cluster_id)] = name
        self.save_model()

    # =========================================================
    # 🔍 المنطقة اللي أنت عايز تفهمها (The Logic)
    # =========================================================
    def predict_debug(self, x):
        """
        دالة التوقع مع طباعة التفاصيل الداخلية
        """
        # 1. طباعة القراءة اللي داخلة
        print(f"\n👀 [AI EYE] Seeing: Power={x['power']}W, PF={x['pf']}")
        
        # 2. لو الموديل لسه فاضي (مفيهوش مراكز)
        if not self.model.centers:
            print("   -> Brain is empty. Assigning first cluster.")
            return self.model.predict_one(x)

        # 3. حساب المسافات يدوياً عشان نوريك هو بيفكر إزاي
        print("   🧠 [Thinking Process]: comparing with known patterns...")
        
        closest_dist = float('inf')
        chosen_id = -1
        
        # بنلف على كل المراكز اللي الموديل اتعلمها
        for cid, center in self.model.centers.items():
            # حساب الفرق (المسافة) بين القراءة وبين مركز الكلاستر
            # بنركز على الباور أكتر لأن الفرق فيه كبير
            dist_power = abs(x['power'] - center['power'])
            
            # بنجيب اسم الجهاز لو معروف
            name = self.cluster_names.get(cid, "Unknown")
            
            print(f"      🔹 Cluster #{cid} ({name}): Center={center['power']:.1f}W | Distance={dist_power:.1f}")
            
            if dist_power < closest_dist:
                closest_dist = dist_power
                chosen_id = cid

        # 4. القرار النهائي
        print(f"   ✅ [Decision]: Closest match is Cluster #{chosen_id} (Diff: {closest_dist:.1f})")
        
        # بنرجع التوقع الحقيقي من المكتبة (للتأكد)
        return self.model.predict_one(x)

    def process_reading(self, power, pf):
        """
        الدالة الرئيسية اللي بتستقبل القراءة وتتعلم منها
        """
        x = {'power': float(power), 'pf': float(pf)}
        
        # 1. التوقع (مع الشرح)
        cluster_id = self.predict_debug(x)
        
        # 2. التعلم (تحديث مكان المركز)
        self.model.learn_one(x)
        
        # 3. إرجاع النتيجة
        device_name = self.cluster_names.get(cluster_id, f"Unknown Device #{cluster_id}")
        
        # بنحفظ كل فترة (مثلاً كل 10 قراءات) أو ممكن نسيبها للحفظ اليدوي
        # self.save_model() 
        
        return device_name, cluster_id
