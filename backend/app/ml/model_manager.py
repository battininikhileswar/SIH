import os
import logging
from typing import Tuple, Optional, Any
import joblib

logger = logging.getLogger(__name__)

# Absolute path to trained model binary
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_FILE_PATH = os.path.join(MODEL_DIR, "classifier.pkl")

# Cached model reference in memory
_cached_model: Optional[Any] = None
_model_status: str = "uninitialized"


def load_model() -> Tuple[Optional[Any], str]:
    """
    Safely load trained scikit-learn model artifact.
    Returns (model_object, status_string).
    Status strings: 'trained' or 'not_trained'.
    Never crashes backend if model file is missing.
    """
    global _cached_model, _model_status

    if _cached_model is not None:
        return _cached_model, _model_status

    if os.path.exists(MODEL_FILE_PATH):
        try:
            logger.info(f"Loading trained ML model artifact from: {MODEL_FILE_PATH}")
            _cached_model = joblib.load(MODEL_FILE_PATH)
            _model_status = "trained"
            return _cached_model, _model_status
        except Exception as e:
            logger.error(f"Failed to load trained model binary: {e}")
            _cached_model = None
            _model_status = "not_trained"
            return None, _model_status

    logger.info(f"No trained ML model found at {MODEL_FILE_PATH}. Using prototype rule engine fallback.")
    _cached_model = None
    _model_status = "not_trained"
    return None, _model_status


def save_model(model_obj: Any, filepath: Optional[str] = None) -> str:
    """Save trained model object to disk using joblib."""
    target_path = filepath or MODEL_FILE_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    joblib.dump(model_obj, target_path)
    logger.info(f"Successfully saved trained ML model to {target_path}")
    return target_path
