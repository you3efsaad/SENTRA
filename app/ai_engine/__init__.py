# ... (Imports)
from app.ai_engine.core import NILMEngine
import app.globals as g

def create_app():
    # ... (code)
    
    # 1. تشغيل محرك الذكاء الاصطناعي
    # هو هيحاول يحمل الموديل المحفوظ (model_state.pkl) لوحده
    g.ai_engine = NILMEngine()
    print("🤖 AI Engine Initialized & Ready.")

    # ... (باقي الكود والـ blueprints)