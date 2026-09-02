import time
import logging
from typing import Dict, Any, List, Tuple, Optional

from app.ml.feature_engineering import extract_features
from app.ml.classifier import classify_thermal_event

logger = logging.getLogger(__name__)

# Max component score weights (Sum = 100)
WEIGHT_THERMAL = 0.25      # Max 25 points
WEIGHT_CONFIDENCE = 0.15   # Max 15 points
WEIGHT_PERSISTENCE = 0.25  # Max 25 points
WEIGHT_PROXIMITY = 0.20    # Max 20 points
WEIGHT_CLASSIFICATION = 0.15 # Max 15 points


def _normalize_thermal_intensity(frp: float, brightness: float) -> Tuple[float, float]:
    """
    Normalize FRP (0 - 50+ MW) and Brightness (300 - 360+ K) to a 0 - 100 scale.
    Returns (component_score_0_100, weight_contribution_0_25).
    """
    frp_norm = min(100.0, (frp / 50.0) * 100.0)
    bright_norm = min(100.0, max(0.0, ((brightness - 300.0) / 60.0) * 100.0))

    comp_score = round(0.70 * frp_norm + 0.30 * bright_norm, 1)
    contribution = round(WEIGHT_THERMAL * comp_score, 1)
    return comp_score, min(25.0, contribution)


def _normalize_confidence(confidence_score: float) -> Tuple[float, float]:
    """
    Normalize satellite confidence score (0.0 - 1.0) to a 0 - 100 scale.
    Returns (component_score_0_100, weight_contribution_0_15).
    """
    comp_score = round(confidence_score * 100.0, 1)
    contribution = round(WEIGHT_CONFIDENCE * comp_score, 1)
    return comp_score, min(15.0, contribution)


def _normalize_persistence(persistence_score: float) -> Tuple[float, float]:
    """
    Normalize persistence score (0 - 100) to weight contribution.
    Returns (component_score_0_100, weight_contribution_0_25).
    """
    comp_score = round(float(persistence_score), 1)
    contribution = round(WEIGHT_PERSISTENCE * comp_score, 1)
    return comp_score, min(25.0, contribution)


def _normalize_industrial_proximity(industrial_distance_km: float) -> Tuple[float, float]:
    """
    Map Haversine industrial distance in kilometers to 0 - 100 proximity score:
    - 0.0 - 0.5 km  -> 100.0 (Very High Proximity)
    - 0.5 - 1.0 km  -> 85.0  (High Proximity)
    - 1.0 - 2.0 km  -> 65.0  (Moderate Proximity)
    - 2.0 - 5.0 km  -> 35.0  (Low Proximity)
    - > 5.0 km      -> 10.0  (Minimal Proximity)
    Returns (component_score_0_100, weight_contribution_0_20).
    """
    dist = float(industrial_distance_km)
    if dist <= 0.5:
        comp_score = 100.0
    elif dist <= 1.0:
        comp_score = 85.0
    elif dist <= 2.0:
        comp_score = 65.0
    elif dist <= 5.0:
        comp_score = 35.0
    else:
        comp_score = 10.0

    contribution = round(WEIGHT_PROXIMITY * comp_score, 1)
    return comp_score, min(20.0, contribution)


def _normalize_classification(classification: str) -> Tuple[float, float]:
    """
    Map AI classification class to 0 - 100 contribution score:
    - INDUSTRIAL_FIRE_CANDIDATE -> 100.0
    - PERSISTENT_THERMAL_SOURCE  -> 85.0
    - GAS_FLARE_CANDIDATE        -> 75.0
    - WILDFIRE_CANDIDATE         -> 70.0
    - AGRICULTURAL_BURNING_CANDIDATE -> 45.0
    - UNCERTAIN                  -> 20.0
    Returns (component_score_0_100, weight_contribution_0_15).
    """
    mapping = {
        "INDUSTRIAL_FIRE_CANDIDATE": 100.0,
        "PERSISTENT_THERMAL_SOURCE": 85.0,
        "GAS_FLARE_CANDIDATE": 75.0,
        "WILDFIRE_CANDIDATE": 70.0,
        "AGRICULTURAL_BURNING_CANDIDATE": 45.0,
        "UNCERTAIN": 20.0
    }
    comp_score = mapping.get(classification, 20.0)
    contribution = round(WEIGHT_CLASSIFICATION * comp_score, 1)
    return comp_score, min(15.0, contribution)


def _determine_risk_level(total_score: int) -> str:
    """Map total risk score (0 - 100) to prototype risk priority level."""
    if total_score >= 75:
        return "CRITICAL"
    elif total_score >= 50:
        return "HIGH"
    elif total_score >= 25:
        return "MODERATE"
    else:
        return "LOW"


def _generate_priority_reasons(
    fd: Dict[str, Any],
    classification: str,
    contrib_thermal: float,
    contrib_proximity: float
) -> List[str]:
    """Generate human-readable priority reasons based strictly on empirical feature values."""
    reasons = []

    frp = fd["frp"]
    if frp >= 40.0:
        reasons.append(f"High Fire Radiative Power (FRP: {frp} MW)")
    elif frp >= 15.0:
        reasons.append(f"Moderate Fire Radiative Power (FRP: {frp} MW)")

    conf = fd["confidence_score"]
    if conf >= 0.8:
        reasons.append("High satellite detection confidence")
    elif conf >= 0.5:
        reasons.append("Nominal satellite detection confidence")

    dist = fd["industrial_distance_km"]
    if dist <= 0.5:
        reasons.append(f"Industrial facility within immediate proximity ({dist} km)")
    elif dist <= 2.0:
        reasons.append(f"Located near industrial infrastructure ({dist} km)")

    score = fd["persistence_score"]
    if score >= 60:
        reasons.append(f"High spatial-temporal persistence score ({score} / 100)")
    elif score >= 30:
        reasons.append(f"Moderate persistence score ({score} / 100)")

    if classification == "INDUSTRIAL_FIRE_CANDIDATE":
        reasons.append("AI classified event as Industrial Fire Candidate")
    elif classification == "PERSISTENT_THERMAL_SOURCE":
        reasons.append("AI classified event as Persistent Thermal Source")
    elif classification == "GAS_FLARE_CANDIDATE":
        reasons.append("AI classified event as Gas Flare Candidate")

    if not reasons:
        reasons.append("Low priority thermal anomaly detected")

    return reasons


def calculate_risk_score(
    spot_or_cluster: Dict[str, Any],
    osm_context: Optional[Dict[str, Any]] = None,
    ai_classification: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate an explainable Thermal Event Risk Priority Score (0 - 100).
    Converts FIRMS, OSM, Persistence, and AI Classification features into 5 weighted components.
    """
    now = time.time()
    
    # 1. Feature Extraction
    feature_dict, _ = extract_features(spot_or_cluster, osm_context)

    # 2. Get AI Classification if not provided
    if not ai_classification:
        ai_classification = classify_thermal_event(spot_or_cluster, osm_context)

    classification = ai_classification.get("classification", "UNCERTAIN")
    model_source = ai_classification.get("model_source", "PROTOTYPE_RULE_ENGINE")

    # 3. Calculate 5 Component Scores & Weight Contributions
    score_thermal, contrib_thermal = _normalize_thermal_intensity(feature_dict["frp"], feature_dict["brightness"])
    score_conf, contrib_conf = _normalize_confidence(feature_dict["confidence_score"])
    score_pers, contrib_pers = _normalize_persistence(feature_dict["persistence_score"])
    score_prox, contrib_prox = _normalize_industrial_proximity(feature_dict["industrial_distance_km"])
    score_ai, contrib_ai = _normalize_classification(classification)

    # 4. Calculate Total Bounded Risk Score (0 - 100)
    total_score = round(contrib_thermal + contrib_conf + contrib_pers + contrib_prox + contrib_ai)
    total_score = max(0, min(100, int(total_score)))

    risk_level = _determine_risk_level(total_score)
    reasons = _generate_priority_reasons(feature_dict, classification, contrib_thermal, contrib_prox)

    return {
        "risk_score": total_score,
        "risk_level": risk_level,
        "model_source": model_source,
        "classification": classification,
        "components": {
            "thermal_intensity": contrib_thermal,
            "satellite_confidence": contrib_conf,
            "persistence": contrib_pers,
            "industrial_proximity": contrib_prox,
            "classification_context": contrib_ai
        },
        "max_component_weights": {
            "thermal_intensity": 25,
            "satellite_confidence": 15,
            "persistence": 25,
            "industrial_proximity": 20,
            "classification_context": 15
        },
        "normalized_scores_100": {
            "thermal_intensity": score_thermal,
            "satellite_confidence": score_conf,
            "persistence": score_pers,
            "industrial_proximity": score_prox,
            "classification_context": score_ai
        },
        "reasons": reasons,
        "features": feature_dict,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))
    }
