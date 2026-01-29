from app.ai_engine.trainer import train_from_csv

# عرف ملفاتك هنا
files = {
    'Air Conditioner': 'CSV_Files/Aircon.csv',
    'Washing Machine': 'CSV_Files/WashingMachine.csv',
    # ضيف باقي الملفات لما تجيلك
}

if __name__ == "__main__":
    train_from_csv(files)