import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

DB_PATH = os.path.join(DATA_DIR, "local.db")

# Klasörler yoksa oluştur
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
