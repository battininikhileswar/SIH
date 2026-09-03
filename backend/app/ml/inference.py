import os
import json
import logging
from typing import Dict, Any, Optional, Tuple
from PIL import Image

import torch
import torchvision.transforms as transforms

from app.config import SATELLITE_MODEL_DIR, SATELLITE_IMAGE_SIZE
from app.ml.model import build_satellite_model, NUM_CLASSES, CLASS_NAMES

logger = logging.getLogger(__name__)


class SatelliteInferenceEngine:
    """
    Production PyTorch Inference Engine for Satellite Optical Patch Classification.
    Loads trained weights from models/satellite_classifier/best_model.pth.
    """

    def __init__(self, model_dir: str = SATELLITE_MODEL_DIR):
        self.model_dir = model_dir
        self.weights_path = os.path.join(model_dir, "best_model.pth")
        self.meta_path = os.path.join(model_dir, "metadata.json")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.is_loaded = False
        self.architecture = "resnet18"
        self.version = "1.0"
        self.model = None

        self.transform = transforms.Compose([
            transforms.Resize((SATELLITE_IMAGE_SIZE, SATELLITE_IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        self._load_model()

    def _load_model(self):
        if not os.path.exists(self.weights_path):
            logger.info(f"Model weights file not found at {self.weights_path}. Model status: UNLOADED.")
            self.is_loaded = False
            return

        if os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    self.architecture = meta.get("model", "resnet18")
                    self.version = meta.get("model_version", "1.0")
            except Exception:
                pass

        try:
            self.model = build_satellite_model(architecture=self.architecture, num_classes=NUM_CLASSES, pretrained=False)
            self.model.load_state_dict(torch.load(self.weights_path, map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
            self.is_loaded = True
            logger.info(f"Successfully loaded trained PyTorch vision model '{self.architecture}' from {self.weights_path}")
        except Exception as e:
            logger.error(f"Error loading PyTorch model from {self.weights_path}: {e}")
            self.is_loaded = False

    def predict_patch(self, image_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run vision model inference on a satellite patch image file.
        Returns prediction, confidence percentage, class probability breakdown, and evidence description.
        """
        if not self.is_loaded or self.model is None:
            return {
                "classification": "UNKNOWN",
                "confidence": 0.0,
                "visual_evidence": "Trained PyTorch vision model is not loaded or missing weights checkpoint.",
                "model": self.architecture,
                "model_version": self.version,
                "model_type": "trained_cv_model",
                "image_available": False,
                "class_probabilities": {}
            }

        if not image_path or not os.path.exists(image_path):
            return {
                "classification": "UNKNOWN",
                "confidence": 0.0,
                "visual_evidence": f"Satellite patch image file unavailable: {image_path}",
                "model": self.architecture,
                "model_version": self.version,
                "model_type": "trained_cv_model",
                "image_available": False,
                "class_probabilities": {}
            }

        try:
            with Image.open(image_path) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                tensor = self.transform(img).unsqueeze(0).to(self.device)

            with torch.no_grad():
                outputs = self.model(tensor)
                probs = torch.softmax(outputs, dim=1).squeeze(0).cpu().numpy()

            predicted_id = int(torch.argmax(outputs, dim=1).item())
            predicted_class = CLASS_NAMES[predicted_id]
            confidence = round(float(probs[predicted_id]), 4)

            prob_dict = {CLASS_NAMES[i]: round(float(probs[i]), 4) for i in range(len(CLASS_NAMES))}

            evidence_text = f"PyTorch Vision Model ({self.architecture}) predicts optical patch event class '{predicted_class.replace('_', ' ')}' with {int(confidence * 100)}% confidence."

            return {
                "classification": predicted_class,
                "confidence": confidence,
                "visual_evidence": evidence_text,
                "model": f"{self.architecture}-v{self.version}",
                "model_version": self.version,
                "model_type": "trained_cv_model",
                "image_available": True,
                "class_probabilities": prob_dict
            }
        except Exception as ex:
            logger.error(f"Inference error on image {image_path}: {ex}")
            return {
                "classification": "UNKNOWN",
                "confidence": 0.0,
                "visual_evidence": f"Inference error: {str(ex)}",
                "model": self.architecture,
                "model_version": self.version,
                "model_type": "trained_cv_model",
                "image_available": True,
                "class_probabilities": {}
            }


# Singleton engine instance
_engine_instance: Optional[SatelliteInferenceEngine] = None


def get_inference_engine() -> SatelliteInferenceEngine:
    """Factory function returning configured SatelliteInferenceEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SatelliteInferenceEngine()
    return _engine_instance
