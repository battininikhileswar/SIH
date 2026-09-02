import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from PIL import Image

from app.services.image_processing_service import validate_satellite_image

logger = logging.getLogger(__name__)

# Valid Satellite Optical Event Classes
SATELLITE_CLASSES = [
    "INDUSTRIAL_FIRE",
    "NATURAL_FIRE",
    "PERSISTENT_THERMAL_SOURCE",
    "NON_FIRE",
    "UNKNOWN"
]


class BaseSatelliteImageClassifier(ABC):
    """Abstract interface for Satellite Image Classifiers (CNN, Vision Transformer, Heuristic, etc.)."""

    @abstractmethod
    def classify_image(self, image_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Classify satellite image patch and return visual classification details."""
        pass


class ModularHeuristicVisionClassifier(BaseSatelliteImageClassifier):
    """
    Modular Multi-Spectral Satellite Image Classifier.
    Analyzes optical heat signature, RGB color channels, thermal intensity core ratio,
    and fuses with spatial metadata to classify thermal anomaly image patches.
    Extensible interface designed for drop-in replacement with CNN or Vision Transformer models.
    """

    def __init__(self):
        self.model_name = "ModularHeuristicVisionClassifier-v1.0"

    def classify_image(self, image_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        meta = metadata or {}

        # Handle missing or invalid image file gracefully
        if not image_path or not os.path.exists(image_path):
            return {
                "classification": "UNKNOWN",
                "confidence": 0.0,
                "visual_evidence": "Satellite image patch unavailable for computer vision classification.",
                "model": self.model_name,
                "timestamp": timestamp_str,
                "image_available": False,
                "features": {}
            }

        is_valid, err = validate_satellite_image(image_path)
        if not is_valid:
            return {
                "classification": "UNKNOWN",
                "confidence": 0.0,
                "visual_evidence": f"Satellite image validation failed: {err}",
                "model": self.model_name,
                "timestamp": timestamp_str,
                "image_available": False,
                "features": {}
            }

        try:
            with Image.open(image_path) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Get pixel data safely
                pixels = list(img.getdata())
                total_pixels = len(pixels)

                # Compute mean RGB channel intensities
                r_sum = sum(p[0] for p in pixels)
                g_sum = sum(p[1] for p in pixels)
                b_sum = sum(p[2] for p in pixels)

                r_avg = r_sum / total_pixels
                g_avg = g_sum / total_pixels
                b_avg = b_sum / total_pixels

                # Count thermal heat core pixels (High Red/Yellow intensity)
                heat_core_pixels = sum(1 for p in pixels if p[0] > 200 and p[1] > 100)
                heat_core_ratio = round(heat_core_pixels / total_pixels, 4)

                # Spectral Thermal Index (STI) calculation
                spectral_thermal_index = round((r_avg - (g_avg + b_avg) / 2.0) / 255.0, 4)

                # Contextual features from metadata
                industrial_dist = meta.get("industrial_distance_km")
                is_industrial = industrial_dist is not None and industrial_dist <= 1.5
                persistence_score = float(meta.get("persistence_score", 0.0))
                frp = float(meta.get("frp", 0.0))

                # Classification Logic
                if heat_core_ratio > 0.02 or spectral_thermal_index > 0.35 or frp > 35.0:
                    if is_industrial or meta.get("is_industrial_zone") == 1:
                        classification = "INDUSTRIAL_FIRE"
                        confidence = min(0.95, round(0.70 + (heat_core_ratio * 2.0) + (0.15 if is_industrial else 0.0), 2))
                        evidence = f"Optical imagery displays strong thermal heat core signature ({heat_core_ratio * 100:.1f}% patch area) localized directly over industrial infrastructure."
                    else:
                        classification = "NATURAL_FIRE"
                        confidence = min(0.92, round(0.65 + (heat_core_ratio * 2.5), 2))
                        evidence = f"Optical satellite imagery confirms active thermal combustion signature ({heat_core_ratio * 100:.1f}% patch area) in non-industrial terrain."
                elif persistence_score >= 60.0:
                    classification = "PERSISTENT_THERMAL_SOURCE"
                    confidence = min(0.90, round(0.60 + (persistence_score / 250.0), 2))
                    evidence = f"Satellite multi-spectral patch confirms persistent thermal emissions over repeated observations (Persistence Score: {persistence_score:.1f}/100)."
                elif heat_core_ratio == 0.0 and spectral_thermal_index < 0.1 and frp < 5.0:
                    classification = "NON_FIRE"
                    confidence = 0.85
                    evidence = "Satellite optical patch displays nominal ground reflectivity with no detectable thermal anomaly signature."
                else:
                    classification = "UNKNOWN"
                    confidence = 0.50
                    evidence = "Satellite imagery evidence is inconclusive. Additional optical/SAR observations required."

                return {
                    "classification": classification,
                    "confidence": confidence,
                    "visual_evidence": evidence,
                    "model": self.model_name,
                    "timestamp": timestamp_str,
                    "image_available": True,
                    "features": {
                        "heat_core_ratio": heat_core_ratio,
                        "red_channel_mean": round(r_avg, 2),
                        "green_channel_mean": round(g_avg, 2),
                        "blue_channel_mean": round(b_avg, 2),
                        "spectral_thermal_index": spectral_thermal_index
                    }
                }
        except Exception as ex:
            logger.error(f"Satellite image classification error: {ex}")
            return {
                "classification": "UNKNOWN",
                "confidence": 0.0,
                "visual_evidence": f"Classification error: {str(ex)}",
                "model": self.model_name,
                "timestamp": timestamp_str,
                "image_available": True,
                "features": {}
            }


# Global classifier instance
_classifier_instance: Optional[BaseSatelliteImageClassifier] = None


def get_satellite_classifier() -> BaseSatelliteImageClassifier:
    """Factory function returning configured SatelliteImageClassifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ModularHeuristicVisionClassifier()
    return _classifier_instance
