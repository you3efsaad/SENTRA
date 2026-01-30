from app.ai_engine.trainer import train_from_csv

# عرف ملفاتك هنا
files = {
    'Air Conditioner': 'app/CSV_Files/Aircon.csv',
    'Battery Charger': 'app/CSV_Files/battery_charger.csv',
    'Coffee Machine': 'app/CSV_Files/coffee_machine.csv',
    'Dishwasher': 'app/CSV_Files/dishwasher.csv',
    'Fridge': 'app/CSV_Files/fridge.csv',
    'Iron': 'app/CSV_Files/iron.csv',
    'Kettle': 'app/CSV_Files/kettle.csv',
    'Laptop': 'app/CSV_Files/Laptop_Charge.csv',
    'Microwave': 'app/CSV_Files/microwave.csv',
    'Office Fan': 'app/CSV_Files/office_fan.csv',
    'Toaster': 'app/CSV_Files/toaster.csv',
    'TV': 'app/CSV_Files/tv.csv',
    'Washing Machine': 'app/CSV_Files/washing_machine.csv',
    'Light': 'app/CSV_Files/LightBulb.csv',
}

if __name__ == "__main__":
    train_from_csv(files)