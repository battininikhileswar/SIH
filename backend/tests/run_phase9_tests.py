import os
import sys
import unittest

# Ensure backend directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from app.main import get_satellite_model_status, get_satellite_model_metrics, predict_satellite_model
from app.config import SATELLITE_DATASET_DIR, SATELLITE_MODEL_DIR, SATELLITE_METRICS_DIR
from app.ml.dataset import SatellitePatchDataset, CLASS_NAME_TO_ID
from app.ml.model import build_satellite_model, NUM_CLASSES, CLASS_NAMES
from app.ml.inference import get_inference_engine
from app.ml.gradcam import generate_gradcam_explanation
from app.services.satellite_classifier import get_satellite_classifier, BaseSatelliteImageClassifier
from app.services.evidence_fusion_service import fuse_thermal_evidence


class TestPhase9SatelliteML(unittest.TestCase):

    def test_01_satellite_dataset_loading(self):
        """Verify SatellitePatchDataset loads processed patches and metadata."""
        dataset = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR, split="train")
        self.assertGreater(len(dataset), 0, "Train split should contain samples")

        img_tensor, label_id, meta = dataset[0]
        self.assertEqual(img_tensor.shape, (3, 256, 256), "Image tensor should be 3x256x256")
        self.assertIn(label_id, [0, 1, 2, 3], "Label ID must be between 0 and 3")
        self.assertIn(meta["label"], CLASS_NAMES, "Label name must be one of the defined class names")
        self.assertIn("split", meta, "Split field must exist in metadata")
        print("  [PASS] test_01_satellite_dataset_loading passed")

    def test_02_geographic_split_no_leakage(self):
        """Verify zero spatial data leakage across train and test splits."""
        from data.satellite.build_dataset import haversine_distance_km

        train_ds = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR, split="train")
        test_ds = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR, split="test")

        train_coords = [(s["latitude"], s["longitude"]) for s in train_ds.samples]
        test_coords = [(s["latitude"], s["longitude"]) for s in test_ds.samples]

        self.assertGreater(len(train_coords), 0)
        self.assertGreater(len(test_coords), 0)

        for t_lat, t_lon in train_coords:
            for te_lat, te_lon in test_coords:
                dist = haversine_distance_km(t_lat, t_lon, te_lat, te_lon)
                self.assertGreaterEqual(dist, 0.05, f"Spatial leakage between train ({t_lat}, {t_lon}) and test ({te_lat}, {te_lon})")
        print("  [PASS] test_02_geographic_split_no_leakage passed")

    def test_03_satellite_vision_model_forward(self):
        """Verify SatelliteVisionModel forward pass produces correct 4-class output."""
        import torch

        model = build_satellite_model(architecture="resnet18", num_classes=NUM_CLASSES, pretrained=False)
        dummy_input = torch.randn(2, 3, 256, 256)

        logits = model(dummy_input)
        self.assertEqual(logits.shape, (2, NUM_CLASSES))

        probs = model.predict_proba(dummy_input)
        self.assertEqual(probs.shape, (2, NUM_CLASSES))

        row_sums = probs.sum(dim=1).detach().numpy()
        for s in row_sums:
            self.assertAlmostEqual(float(s), 1.0, places=4)
        print("  [PASS] test_03_satellite_vision_model_forward passed")

    def test_04_inference_engine(self):
        """Verify SatelliteInferenceEngine prediction output structure."""
        engine = get_inference_engine()
        self.assertIsNotNone(engine)

        dataset = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR)
        self.assertGreater(len(dataset), 0)
        first_sample = dataset.samples[0]
        img_path = first_sample["resolved_image_path"]

        result = engine.predict_patch(img_path)
        self.assertIn("classification", result)
        self.assertIn(result["classification"], CLASS_NAMES + ["UNKNOWN"])
        self.assertIn("confidence", result)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        self.assertIn("class_probabilities", result)
        print("  [PASS] test_04_inference_engine passed")

    def test_05_gradcam_explanation_generation(self):
        """Verify Grad-CAM heatmap explanation generator."""
        dataset = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR)
        img_path = dataset.samples[0]["resolved_image_path"]

        cam_res = generate_gradcam_explanation(img_path)
        self.assertTrue(cam_res["success"])
        self.assertIsNotNone(cam_res["heatmap_path"])
        self.assertTrue(os.path.exists(cam_res["heatmap_path"]))
        self.assertIn("highlighted_region", cam_res)
        print("  [PASS] test_05_gradcam_explanation_generation passed")

    def test_06_trained_classifier_adapter(self):
        """Verify TrainedSatelliteVisionClassifier adheres to BaseSatelliteImageClassifier."""
        classifier = get_satellite_classifier()
        self.assertIsInstance(classifier, BaseSatelliteImageClassifier)

        dataset = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR)
        img_path = dataset.samples[0]["resolved_image_path"]

        res = classifier.classify_image(img_path)
        self.assertIn("classification", res)
        self.assertIn("confidence", res)
        self.assertIn("visual_evidence", res)
        self.assertIn("model", res)
        print("  [PASS] test_06_trained_classifier_adapter passed")

    def test_07_evidence_fusion_with_satellite_cv(self):
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

        self.assertEqual(fused["final_classification"], "INDUSTRIAL_FIRE_CANDIDATE")
        self.assertGreaterEqual(fused["combined_confidence"], 0.70)
        self.assertIn("Petrochemical Refinery", fused["fusion_summary"])
        self.assertEqual(fused["evidence"]["satellite"]["classification"], "INDUSTRIAL_FIRE")
        self.assertEqual(fused["evidence"]["satellite"]["model_type"], "trained_cv_model")
        print("  [PASS] test_07_evidence_fusion_with_satellite_cv passed")

    def test_08_api_satellite_model_status(self):
        """Test GET /api/satellite/model/status endpoint function."""
        data = get_satellite_model_status()
        self.assertIn("available", data)
        self.assertIn("model", data)
        self.assertIn("classes", data)
        self.assertEqual(len(data["classes"]), 4)
        print("  [PASS] test_08_api_satellite_model_status passed")

    def test_09_api_satellite_model_metrics(self):
        """Test GET /api/satellite/model/metrics endpoint function."""
        data = get_satellite_model_metrics()
        self.assertTrue("accuracy" in data or "evaluated" in data)
        if "accuracy" in data:
            self.assertGreaterEqual(data["accuracy"], 0.0)
            self.assertLessEqual(data["accuracy"], 1.0)
            self.assertIn("confusion_matrix", data)
            self.assertIn("per_class_metrics", data)
        print("  [PASS] test_09_api_satellite_model_metrics passed")

    def test_10_api_satellite_model_predict(self):
        """Test POST /api/satellite/model/predict endpoint function."""
        dataset = SatellitePatchDataset(dataset_dir=SATELLITE_DATASET_DIR)
        img_path = dataset.samples[0]["resolved_image_path"]

        data = predict_satellite_model(image_path=img_path)
        self.assertIn("classification", data)
        self.assertIn("confidence", data)
        self.assertIn("visual_evidence", data)
        print("  [PASS] test_10_api_satellite_model_predict passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
