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

# Phase 8 Satellite Image Intelligence Parameters
SATELLITE_PROVIDER = os.getenv("SATELLITE_PROVIDER", "sentinel-2")
SATELLITE_API_KEY = os.getenv("SATELLITE_API_KEY", "")
SATELLITE_IMAGE_SIZE = int(os.getenv("SATELLITE_IMAGE_SIZE", "256"))
SATELLITE_PATCH_RADIUS_KM = float(os.getenv("SATELLITE_PATCH_RADIUS_KM", "1.0"))
SATELLITE_CACHE_DIR = os.path.join(PROJECT_ROOT, os.getenv("SATELLITE_CACHE_DIR", "data/satellite/cache"))
SATELLITE_DATASET_DIR = os.path.join(PROJECT_ROOT, os.getenv("SATELLITE_DATASET_DIR", "data/satellite"))
