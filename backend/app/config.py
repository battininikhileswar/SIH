import os

# Centralized Alert Configuration Parameters
ALERT_CRITICAL_THRESHOLD = float(os.getenv("ALERT_CRITICAL_THRESHOLD", "75.0"))
ALERT_HIGH_THRESHOLD = float(os.getenv("ALERT_HIGH_THRESHOLD", "50.0"))
ALERT_DEDUP_RADIUS_KM = float(os.getenv("ALERT_DEDUP_RADIUS_KM", "1.0"))
ALERT_COOLDOWN_HOURS = float(os.getenv("ALERT_COOLDOWN_HOURS", "12.0"))

# Persistent File Storage Path (data/processed/alerts.json)
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # backend/app
BACKEND_DIR = os.path.dirname(BASE_DIR)              # backend
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)           # root SIH-26162
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
ALERTS_STORAGE_PATH = os.path.join(DATA_DIR, "alerts.json")
