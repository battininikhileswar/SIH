from typing import Dict, Any, Tuple, List, Optional
import numpy as np

# Ordered list of tabular feature names for model input
FEATURE_NAMES = [
    "brightness",
    "confidence_score",
    "frp",
    "industrial_distance_km",
    "is_industrial_zone",
    "observation_count",
    "duration_hours",
    "spatial_radius_km",
    "persistence_score"
]


def _normalize_confidence(confidence_val: Any) -> float:
    """Normalize confidence string ('high', 'nominal', 'low') or numeric score to [0.0, 1.0]."""
    if isinstance(confidence_val, (int, float)):
        return min(1.0, max(0.0, float(confidence_val) / 100.0 if confidence_val > 1.0 else float(confidence_val)))
    
    conf_str = str(confidence_val).lower().strip()
    if conf_str in ["high", "h"]:
        return 0.9
    elif conf_str in ["nominal", "n", "medium", "m"]:
        return 0.6
    elif conf_str in ["low", "l"]:
        return 0.3
    return 0.5


def extract_features(
    spot_or_cluster: Dict[str, Any],
    osm_context: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], List[float]]:
    """
    Extract a normalized tabular feature dictionary and vector from satellite observations,
    OSM proximity context, and temporal persistence metrics.
    """
    # 1. FIRMS Satellite Features
    brightness = float(spot_or_cluster.get("brightness") or spot_or_cluster.get("bright_ti4") or 320.0)
    raw_confidence = spot_or_cluster.get("confidence", "nominal")
    confidence_score = _normalize_confidence(raw_confidence)
    frp = float(spot_or_cluster.get("frp") or 0.0)

    # 2. Persistence Metrics
    obs_count = int(spot_or_cluster.get("observation_count", 1))
    duration_hours = float(spot_or_cluster.get("duration_hours", 0.0))
    spatial_radius_km = float(spot_or_cluster.get("spatial_radius_km", 0.0))
    persistence_score = float(spot_or_cluster.get("persistence_score", 0.0))

    # 3. OpenStreetMap Proximity Features
    industrial_distance_km = 10.0  # Default 10km if no nearby facility
    is_industrial_zone = 0

    # Extract OSM context if provided in spot_or_cluster or passed explicitly
    ctx = osm_context or spot_or_cluster.get("industrial_context")
    if ctx:
        if isinstance(ctx, dict):
            ctx_class = ctx.get("context_classification", "").upper()
            if ctx_class == "INDUSTRIAL":
                is_industrial_zone = 1
            
            dist = ctx.get("distance_km")
            if dist is not None:
                industrial_distance_km = float(dist)

    # Construct named feature dictionary
    feature_dict = {
        "brightness": round(brightness, 2),
        "confidence_score": round(confidence_score, 2),
        "frp": round(frp, 2),
        "industrial_distance_km": round(industrial_distance_km, 2),
        "is_industrial_zone": is_industrial_zone,
        "observation_count": obs_count,
        "duration_hours": round(duration_hours, 2),
        "spatial_radius_km": round(spatial_radius_km, 2),
        "persistence_score": round(persistence_score, 2)
    }

    # Construct feature vector matching model expectation
    feature_vector = [feature_dict[name] for name in FEATURE_NAMES]

    return feature_dict, feature_vector
