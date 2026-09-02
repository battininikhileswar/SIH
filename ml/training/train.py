import os
import sys
import csv
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "datasets", "thermal_events_dataset.csv")

PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from app.ml.model_manager import save_model

def train_model():
    print("==================================================", flush=True)
    print("   SIH 26162 TABULAR ML MODEL TRAINING PIPELINE   ", flush=True)
    print("==================================================", flush=True)

    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found at {DATASET_PATH}. Please run prepare_dataset.py first.", flush=True)
        return

    # Load dataset CSV
    features = []
    labels = []

    with open(DATASET_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            feat_vec = [
                float(row["brightness"]),
                float(row["confidence_score"]),
                float(row["frp"]),
                float(row["industrial_distance_km"]),
                int(row["is_industrial_zone"]),
                int(row["observation_count"]),
                float(row["duration_hours"]),
                float(row["spatial_radius_km"]),
                float(row["persistence_score"])
            ]
            features.append(feat_vec)
            labels.append(row["label"])

    X = np.array(features)
    y = np.array(labels)

    print(f"Loaded {len(X)} labeled feature samples across {len(set(y))} categories.", flush=True)

    # Train RandomForestClassifier
    clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    clf.fit(X, y)

    # Evaluate on training data
    y_pred = clf.predict(X)
    acc = accuracy_score(y, y_pred)
    print(f"\nModel Training Accuracy: {acc * 100:.2f}%", flush=True)
    print("\nClassification Report:\n", classification_report(y, y_pred, zero_division=0), flush=True)

    # Save trained model binary to backend/app/ml/models/classifier.pkl
    saved_path = save_model(clf)
    print(f"Model saved successfully to: {saved_path}", flush=True)

if __name__ == "__main__":
    train_model()
