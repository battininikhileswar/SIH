from typing import Dict, Any, List, Tuple
import numpy as np

from app.ml.feature_engineering import extract_features
from app.ml.model_manager import load_model

PROTOTYPE_VERSION = "prototype-1.0"

# Target prototype classification categories
CATEGORIES = [
    "INDUSTRIAL_FIRE_CANDIDATE",
    "PERSISTENT_THERMAL_SOURCE",
    "AGRICULTURAL_BURNING_CANDIDATE",
    "WILDFIRE_CANDIDATE",
    "GAS_FLARE_CANDIDATE",
    "UNCERTAIN"
]


def _generate_supporting_indicators(fd: Dict[str, Any], classification: str) -> List[str]:
    """
    Generate human-readable supporting indicators explaining why the classifier
    produced the given prediction (Explainable AI).
    """
    indicators: List[str] = []

    # FRP Indicator
    frp = fd["frp"]
    if frp >= 40.0:
        indicators.append(f"High Fire Radiative Power (FRP: {frp} MW)")
    elif frp >= 15.0:
        indicators.append(f"Moderate Fire Radiative Power (FRP: {frp} MW)")
    else:
        indicators.append(f"Low Fire Radiative Power (FRP: {frp} MW)")

    # Satellite Confidence Indicator
    conf = fd["confidence_score"]
    if conf >= 0.8:
        indicators.append("High satellite detection confidence score")
    elif conf >= 0.5:
        indicators.append("Nominal satellite detection confidence score")

    # Industrial Proximity Indicator
    dist = fd["industrial_distance_km"]
    is_ind = fd["is_industrial_zone"]
    if is_ind == 1 or dist <= 1.0:
        indicators.append(f"Industrial facility mapped within {dist} km")
    elif dist <= 3.0:
        indicators.append(f"Located near industrial zone ({dist} km)")
    else:
        indicators.append(f"No industrial facilities within immediate vicinity ({dist} km)")

    # Persistence & Temporal Indicators
    score = fd["persistence_score"]
    obs = fd["observation_count"]
    dur = fd["duration_hours"]

    if score >= 60:
        indicators.append(f"High Persistence Score ({score} / 100)")
    elif score >= 30:
        indicators.append(f"Moderate Persistence Score ({score} / 100)")

    if obs > 1:
        indicators.append(f"Detected across {obs} satellite observations")
    
    if dur > 2.0:
        indicators.append(f"Sustained thermal activity over {dur} hours")

    return indicators


def _prototype_rule_engine_predict(fd: Dict[str, Any]) -> Tuple[str, int]:
    """
    Prototype Rule Engine Fallback when no trained ML model artifact is present.
    Deterministic, transparent classification based on spatial-temporal rules.
    """
    frp = fd["frp"]
    dist = fd["industrial_distance_km"]
    is_ind = fd["is_industrial_zone"]
    score = fd["persistence_score"]
    obs = fd["observation_count"]
    dur = fd["duration_hours"]

    # Rule 1: High FRP + Close Industrial Proximity + High Persistence -> INDUSTRIAL_FIRE_CANDIDATE
    if frp >= 40.0 and (dist <= 1.0 or is_ind == 1) and score >= 60:
        return ("INDUSTRIAL_FIRE_CANDIDATE", 87)

    # Rule 2: High Persistence Score or Recurring Detections -> PERSISTENT_THERMAL_SOURCE
    if score >= 60 or (dist <= 2.0 and obs >= 3):
        return ("PERSISTENT_THERMAL_SOURCE", 85)

    # Rule 3: Moderate FRP + Close Industrial Proximity -> GAS_FLARE_CANDIDATE
    if dist <= 1.5 and frp < 30.0 and score >= 30:
        return ("GAS_FLARE_CANDIDATE", 78)

    # Rule 4: High FRP + Non-Industrial Zone + Single/Short Duration -> AGRICULTURAL_BURNING_CANDIDATE
    if is_ind == 0 and dist > 3.0 and frp >= 20.0 and dur <= 4.0:
        return ("AGRICULTURAL_BURNING_CANDIDATE", 75)

    # Rule 5: Non-Industrial + Multi-Hour Sustained Thermal Activity -> WILDFIRE_CANDIDATE
    if is_ind == 0 and dist > 3.0 and dur > 4.0:
        return ("WILDFIRE_CANDIDATE", 72)

    # Fallback Rule: UNCERTAIN
    return ("UNCERTAIN", 50)


def classify_thermal_event(
    spot_or_cluster: Dict[str, Any],
    osm_context: Any = None
) -> Dict[str, Any]:
    """
    Execute AI classification for a thermal hotspot or cluster.
    Uses trained scikit-learn model if binary is present, or transparent PROTOTYPE_RULE_ENGINE fallback.
    Returns prediction, confidence percentage, supporting indicators, and raw feature dictionary.
    """
    feature_dict, feature_vector = extract_features(spot_or_cluster, osm_context)
    model, model_status = load_model()

    if model_status == "trained" and model is not None:
        try:
            X = np.array([feature_vector])
            prediction = str(model.predict(X)[0])
            
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(X)[0]
                confidence_pct = int(round(float(np.max(probs)) * 100))
            else:
                confidence_pct = 80
            
            model_source = "ML_MODEL"
        except Exception:
            prediction, confidence_pct = _prototype_rule_engine_predict(feature_dict)
            model_source = "PROTOTYPE_RULE_ENGINE"
    else:
        prediction, confidence_pct = _prototype_rule_engine_predict(feature_dict)
        model_source = "PROTOTYPE_RULE_ENGINE"

    supporting_indicators = _generate_supporting_indicators(feature_dict, prediction)

    return {
        "classification": prediction,
        "confidence_percentage": confidence_pct,
        "model_source": model_source,
        "model_status": model_status,
        "model_version": PROTOTYPE_VERSION,
        "supporting_indicators": supporting_indicators,
        "features": feature_dict
    }
