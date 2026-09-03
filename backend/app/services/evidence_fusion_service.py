import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def fuse_thermal_evidence(
    spot_dict: Dict[str, Any],
    osm_context: Optional[Dict[str, Any]] = None,
    ai_classification: Optional[Dict[str, Any]] = None,
    risk_result: Optional[Dict[str, Any]] = None,
    satellite_evidence: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Multi-Modal Evidence Fusion Engine (Step 15).
    Combines:
      1. NASA FIRMS active fire satellite metrics
      2. OpenStreetMap industrial proximity & infrastructure context
      3. Spatial-temporal persistence scores & observation timeline
      4. Trained Satellite Optical Image Vision Model classification & confidence
    Produces a unified decision confidence score (0.0 - 1.0) and multi-modal evidence breakdown.
    """
    # Extract FIRMS metrics
    frp = float(spot_dict.get("frp", 0.0))
    brightness = float(spot_dict.get("brightness", 320.0))
    confidence_raw = str(spot_dict.get("confidence", "nominal")).lower()

    # Extract OSM Context
    osm_ctx = osm_context or spot_dict.get("industrial_context") or {}
    facility_name = osm_ctx.get("nearby_facility") or "None"
    ind_dist = osm_ctx.get("distance_km")
    is_industrial = ind_dist is not None and ind_dist <= 1.5

    # Extract Persistence
    persistence_score = float(spot_dict.get("persistence_score", 0.0))
    duration_hours = float(spot_dict.get("duration_hours", 0.0))
    obs_count = int(spot_dict.get("observation_count", 1))

    # Extract Base AI Classification & Risk Score
    base_ai_class = ai_classification.get("classification") if ai_classification else "AGRICULTURAL_BURNING_CANDIDATE"
    base_confidence = (ai_classification.get("confidence_percentage", 50) / 100.0) if ai_classification else 0.50
    risk_score = risk_result.get("risk_score") if risk_result else int(persistence_score * 0.6)
    risk_level = risk_result.get("risk_level") if risk_result else "MODERATE"

    # Extract Satellite Image Evidence
    sat = satellite_evidence or {}
    sat_available = sat.get("image_available", False)
    sat_class = sat.get("classification", "UNKNOWN")
    sat_conf = float(sat.get("confidence", 0.0))
    sat_model = sat.get("model", "ResNet18")
    sat_model_type = sat.get("model_type", "trained_cv_model")
    sat_evidence_text = sat.get("visual_evidence", "Satellite optical imagery unavailable.")

    # Multi-Modal Decision Fusion Rules with Configurable Weights
    fused_classification = base_ai_class
    confidence_weight_accum = base_confidence * 0.35

    # 1. FIRMS Weight (20%)
    firms_score = min(1.0, (frp / 40.0) * 0.5 + (1.0 if "high" in confidence_raw else 0.5) * 0.5)
    confidence_weight_accum += firms_score * 0.20

    # 2. OSM Context Weight (15%)
    osm_score = 1.0 if is_industrial else 0.2
    confidence_weight_accum += osm_score * 0.15

    # 3. Persistence Weight (15%)
    persistence_normalized = min(1.0, persistence_score / 100.0)
    confidence_weight_accum += persistence_normalized * 0.15

    # 4. Satellite Computer Vision Model Weight (15%)
    if sat_available and sat_class != "UNKNOWN":
        confidence_weight_accum += sat_conf * 0.15

        # Decision rule: Trained vision model informs classification without overriding strong contradictory evidence
        if sat_class in ["INDUSTRIAL_FIRE", "PERSISTENT_THERMAL_SOURCE"] and is_industrial:
            fused_classification = "INDUSTRIAL_FIRE_CANDIDATE"
        elif sat_class in ["NATURAL_FIRE", "WILDFIRE_CANDIDATE"] and not is_industrial:
            fused_classification = "WILDFIRE_CANDIDATE"
        elif sat_class == "NON_FIRE" and frp < 10.0 and not is_industrial:
            fused_classification = "AGRICULTURAL_BURNING_CANDIDATE"

    final_confidence = min(0.98, max(0.40, round(confidence_weight_accum, 2)))

    # Generate Human-Readable Multi-Modal Fusion Rationale Summary
    fusion_highlights = []
    if sat_available and sat_class != "UNKNOWN":
        model_desc = f"PyTorch Model ({sat_model})" if sat_model_type == "trained_cv_model" else f"Optical Classifier ({sat_model})"
        fusion_highlights.append(f"{model_desc} classifies satellite patch as {sat_class} ({int(sat_conf * 100)}% visual confidence).")
    else:
        fusion_highlights.append("Satellite optical imagery unverified or unavailable; multi-modal decision relies on thermal & geospatial features.")

    if is_industrial:
        fusion_highlights.append(f"Located {ind_dist:.2f} km from industrial facility ({facility_name}).")
    if persistence_score >= 50.0:
        fusion_highlights.append(f"High spatial-temporal persistence score ({persistence_score:.1f}/100 across {obs_count} satellite passes over {duration_hours:.1f} hours).")
    if frp >= 25.0:
        fusion_highlights.append(f"High Fire Radiative Power ({frp:.1f} MW).")

    fusion_summary = " ".join(fusion_highlights)

    return {
        "final_classification": fused_classification,
        "combined_confidence": final_confidence,
        "combined_confidence_percentage": int(final_confidence * 100),
        "combined_risk_score": risk_score,
        "risk_level": risk_level,
        "fusion_summary": fusion_summary,
        "evidence": {
            "firms": {
                "frp_mw": frp,
                "brightness_k": brightness,
                "confidence": confidence_raw,
                "summary": f"FRP {frp} MW, Brightness {brightness} K, Satellite confidence {confidence_raw}"
            },
            "osm": {
                "context": osm_ctx.get("context_classification", "RURAL_OR_AGRICULTURAL"),
                "nearby_facility": facility_name,
                "distance_km": ind_dist,
                "summary": f"Facility: {facility_name} ({ind_dist} km)" if ind_dist else "No nearby industrial facility within 5.0 km"
            },
            "persistence": {
                "persistence_score": persistence_score,
                "observation_count": obs_count,
                "duration_hours": duration_hours,
                "summary": f"Score {persistence_score}/100, {obs_count} passes over {duration_hours}h"
            },
            "satellite": {
                "image_available": sat_available,
                "classification": sat_class,
                "confidence": sat_conf,
                "model": sat_model,
                "model_type": sat_model_type,
                "source": sat.get("source", "Sentinel-2 L2A"),
                "captured_at": sat.get("captured_at"),
                "image_url": sat.get("image_url"),
                "visual_evidence": sat_evidence_text,
                "class_probabilities": sat.get("class_probabilities", {})
            }
        }
    }
