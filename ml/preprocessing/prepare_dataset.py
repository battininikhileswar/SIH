import os
import csv

# Create directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "datasets")
DATASET_CSV_PATH = os.path.join(DATASET_DIR, "thermal_events_dataset.csv")

os.makedirs(DATASET_DIR, exist_ok=True)

# Sample CSV dataset headers and labeled prototype data
HEADERS = [
    "brightness",
    "confidence_score",
    "frp",
    "industrial_distance_km",
    "is_industrial_zone",
    "observation_count",
    "duration_hours",
    "spatial_radius_km",
    "persistence_score",
    "label"
]

SAMPLE_ROWS = [
    # INDUSTRIAL_FIRE_CANDIDATE
    [345.2, 0.9, 52.4, 0.42, 1, 8, 14.5, 0.65, 94.0, "INDUSTRIAL_FIRE_CANDIDATE"],
    [338.0, 0.9, 45.0, 0.35, 1, 6, 12.0, 0.50, 88.0, "INDUSTRIAL_FIRE_CANDIDATE"],
    [350.5, 0.95, 68.1, 0.80, 1, 10, 18.2, 0.72, 98.0, "INDUSTRIAL_FIRE_CANDIDATE"],
    # PERSISTENT_THERMAL_SOURCE
    [325.4, 0.8, 18.2, 0.53, 1, 7, 12.4, 0.79, 85.0, "PERSISTENT_THERMAL_SOURCE"],
    [328.1, 0.85, 22.0, 1.20, 1, 5, 10.1, 0.45, 76.0, "PERSISTENT_THERMAL_SOURCE"],
    [322.0, 0.75, 14.5, 0.20, 1, 6, 11.5, 0.30, 82.0, "PERSISTENT_THERMAL_SOURCE"],
    # GAS_FLARE_CANDIDATE
    [318.5, 0.7, 12.0, 0.25, 1, 4, 8.0, 0.20, 58.0, "GAS_FLARE_CANDIDATE"],
    [320.1, 0.8, 15.4, 0.40, 1, 5, 9.2, 0.25, 64.0, "GAS_FLARE_CANDIDATE"],
    # AGRICULTURAL_BURNING_CANDIDATE
    [332.0, 0.9, 35.0, 8.50, 0, 1, 0.0, 0.0, 15.0, "AGRICULTURAL_BURNING_CANDIDATE"],
    [329.5, 0.85, 28.4, 12.0, 0, 1, 0.0, 0.0, 15.0, "AGRICULTURAL_BURNING_CANDIDATE"],
    [335.8, 0.9, 42.1, 6.20, 0, 2, 2.5, 0.40, 28.0, "AGRICULTURAL_BURNING_CANDIDATE"],
    # WILDFIRE_CANDIDATE
    [340.2, 0.95, 62.0, 15.0, 0, 4, 18.0, 2.50, 68.0, "WILDFIRE_CANDIDATE"],
    [348.5, 0.95, 85.2, 10.4, 0, 6, 22.0, 3.80, 78.0, "WILDFIRE_CANDIDATE"],
    # UNCERTAIN
    [312.0, 0.3, 4.2, 4.50, 0, 1, 0.0, 0.0, 10.0, "UNCERTAIN"],
    [314.5, 0.5, 6.0, 3.20, 0, 1, 0.0, 0.0, 12.0, "UNCERTAIN"]
]

def generate_sample_dataset():
    print(f"Creating ML training dataset template at: {DATASET_CSV_PATH}")
    with open(DATASET_CSV_PATH, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerows(SAMPLE_ROWS)
    print(f"Successfully wrote {len(SAMPLE_ROWS)} sample dataset rows.")

if __name__ == "__main__":
    generate_sample_dataset()
