import os
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import SATELLITE_DATASET_DIR, SATELLITE_MODEL_DIR, SATELLITE_METRICS_DIR
from app.ml.dataset import SatellitePatchDataset, CLASS_NAME_TO_ID
from app.ml.model import build_satellite_model, NUM_CLASSES, CLASS_NAMES
from app.ml.inference import get_inference_engine
from app.ml.gradcam import generate_gradcam_explanation
from app.services.satellite_classifier import get_satellite_classifier, BaseSatelliteImageClassifier
from app.services.evidence_fusion_service import fuse_thermal_evidence

client = TestClient(app)


def test_satellite_dataset_loading():
    """Verify SatellitePatchDataset loads processed patches and metadata."""
    dataset = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR, split="train")
    assert len(dataset) > 0, "Train split should contain samples"

    img_tensor, label_id, meta = dataset[0]
    assert img_tensor.shape == (3, 256, 256), "Image tensor should be 3x256x256"
    assert label_id in [0, 1, 2, 3], "Label ID must be between 0 and 3"
    assert meta["label"] in CLASS_NAMES, "Label name must be one of the defined class names"
    assert "split" in meta, "Split field must exist in metadata"


def test_geographic_split_no_leakage():
    """Verify zero spatial data leakage across train and test splits."""
    from data.satellite.build_dataset import haversine_distance_km

    train_ds = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR, split="train")
    test_ds = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR, split="test")

    train_coords = [(s["latitude"], s["longitude"]) for s in train_ds.samples]
    test_coords = [(s["latitude"], s["longitude"]) for s in test_ds.samples]

    assert len(train_coords) > 0
    assert len(test_coords) > 0

    # Ensure no train-test pair is within 0.05 km (50m) of identical coordinates
    for t_lat, t_lon in train_coords:
        for te_lat, te_lon in test_coords:
            dist = haversine_distance_km(t_lat, t_lon, te_lat, te_lon)
            assert dist >= 0.05, f"Spatial leakage detected between train ({t_lat}, {t_lon}) and test ({te_lat}, {te_lon}): {dist} km"


def test_satellite_vision_model_forward():
    """Verify SatelliteVisionModel forward pass produces correct 4-class output."""
    import torch

    model = build_satellite_model(architecture="resnet18", num_classes=NUM_CLASSES, pretrained=False)
    dummy_input = torch.randn(2, 3, 256, 256)

    logits = model(dummy_input)
    assert logits.shape == (2, NUM_CLASSES), f"Logits shape should be (2, 4), got {logits.shape}"

    probs = model.predict_proba(dummy_input)
    assert probs.shape == (2, NUM_CLASSES)
    # Check probability sum close to 1.0
    row_sums = probs.sum(dim=1).detach().numpy()
    for s in row_sums:
        assert abs(s - 1.0) < 1e-4, f"Softmax probabilities must sum to 1.0, got {s}"


def test_inference_engine():
    """Verify SatelliteInferenceEngine prediction output structure."""
    engine = get_inference_engine()
    assert engine is not None

    # Test with existing patch from dataset
    dataset = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR)
    assert len(dataset) > 0
    first_sample = dataset.samples[0]
    img_path = first_sample["resolved_image_path"]

    result = engine.predict_patch(img_path)
    assert "classification" in result
    assert result["classification"] in CLASS_NAMES + ["UNKNOWN"]
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert "class_probabilities" in result
    assert isinstance(result["class_probabilities"], dict)


def test_gradcam_explanation_generation(tmp_path):
    """Verify Grad-CAM heatmap explanation generator."""
    dataset = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR)
    img_path = dataset.samples[0]["resolved_image_path"]

    out_file = str(tmp_path / "test_heatmap.png")
    cam_res = generate_gradcam_explanation(img_path, output_path=out_file)

    assert cam_res["success"] is True
    assert os.path.exists(out_file), "Heatmap overlay file should be created"
    assert "highlighted_region" in cam_res


def test_trained_classifier_adapter():
    """Verify TrainedSatelliteVisionClassifier adheres to BaseSatelliteImageClassifier."""
    classifier = get_satellite_classifier()
    assert isinstance(classifier, BaseSatelliteImageClassifier)

    dataset = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR)
    img_path = dataset.samples[0]["resolved_image_path"]

    res = classifier.classify_image(img_path)
    assert "classification" in res
    assert "confidence" in res
    assert "visual_evidence" in res
    assert "model" in res


def test_evidence_fusion_with_satellite_cv():
    """Verify multi-modal evidence fusion combines FIRMS + OSM + Persistence + Satellite CV."""
    spot = {
        "latitude": 21.1045,
        "longitude": 72.6402,
        "frp": 35.0,
        "brightness": 335.0,
        "confidence": "high",
        "persistence_score": 75.0,
        "duration_hours": 18.0,
        "observation_count": 6
    }
    osm_ctx = {
        "context_classification": "HEAVY_INDUSTRIAL_ZONE",
        "nearby_facility": "Petrochemical Refinery Complex",
        "distance_km": 0.45
    }
    sat_evidence = {
        "image_available": True,
        "classification": "INDUSTRIAL_FIRE",
        "confidence": 0.88,
        "model": "resnet18-v1.0",
        "model_type": "trained_cv_model",
        "source": "Sentinel-2 L2A",
        "visual_evidence": "Optical patch confirms strong thermal emission localized at industrial storage unit."
    }

    fused = fuse_thermal_evidence(spot_dict=spot, osm_context=osm_ctx, satellite_evidence=sat_evidence)

    assert fused["final_classification"] == "INDUSTRIAL_FIRE_CANDIDATE"
    assert fused["combined_confidence"] >= 0.70
    assert "Petrochemical Refinery" in fused["fusion_summary"]
    assert fused["evidence"]["satellite"]["classification"] == "INDUSTRIAL_FIRE"
    assert fused["evidence"]["satellite"]["model_type"] == "trained_cv_model"


def test_api_satellite_model_status():
    """Test GET /api/satellite/model/status endpoint."""
    resp = client.get("/api/satellite/model/status")
    assert resp.status_code == 200
    data = resp.json()

    assert "available" in data
    assert "model" in data
    assert "classes" in data
    assert len(data["classes"]) == 4
    assert "NON_FIRE" in data["classes"]
    assert "INDUSTRIAL_FIRE" in data["classes"]


def test_api_satellite_model_metrics():
    """Test GET /api/satellite/model/metrics endpoint."""
    resp = client.get("/api/satellite/model/metrics")
    assert resp.status_code == 200
    data = resp.json()

    assert "accuracy" in data or "evaluated" in data
    if "accuracy" in data:
        assert 0.0 <= data["accuracy"] <= 1.0
        assert "confusion_matrix" in data
        assert "per_class_metrics" in data


def test_api_satellite_model_predict():
    """Test POST /api/satellite/model/predict endpoint."""
    dataset = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR)
    img_path = dataset.samples[0]["resolved_image_path"]

    resp = client.post("/api/satellite/model/predict", json=img_path)
    assert resp.status_code == 200
    data = resp.json()

    assert "classification" in data
    assert "confidence" in data
    assert "visual_evidence" in data
