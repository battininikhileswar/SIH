import os
import json
import time
import logging
from typing import List, Dict, Any, Tuple, Optional

from app.config import (
    ALERT_CRITICAL_THRESHOLD,
    ALERT_HIGH_THRESHOLD,
    ALERT_DEDUP_RADIUS_KM,
    ALERT_COOLDOWN_HOURS,
    ALERTS_STORAGE_PATH,
)
from app.services.osm_service import haversine_distance_km
from app.services.risk_service import calculate_risk_score

logger = logging.getLogger(__name__)

# Valid state machine transitions
ALLOWED_TRANSITIONS = {
    "NEW": ["ACKNOWLEDGED", "DISMISSED"],
    "ACKNOWLEDGED": ["INVESTIGATING", "RESOLVED", "DISMISSED"],
    "INVESTIGATING": ["RESOLVED", "DISMISSED"],
    "RESOLVED": [],
    "DISMISSED": []
}


def _load_alerts_db() -> List[Dict[str, Any]]:
    """Load stored alerts from persistent JSON file storage."""
    if not os.path.exists(ALERTS_STORAGE_PATH):
        return []
    try:
        with open(ALERTS_STORAGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading alerts storage: {e}")
        return []


def _save_alerts_db(alerts: List[Dict[str, Any]]) -> bool:
    """Save alerts array to persistent JSON file storage."""
    try:
        os.makedirs(os.path.dirname(ALERTS_STORAGE_PATH), exist_ok=True)
        with open(ALERTS_STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(alerts, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error writing alerts storage: {e}")
        return False


def _generate_alert_id(alerts: List[Dict[str, Any]]) -> str:
    """Generate unique human-readable alert ID: ALT-YYYYMMDD-XXXX."""
    date_str = time.strftime("%Y%m%d", time.gmtime())
    count = len(alerts) + 1
    return f"ALT-{date_str}-{count:04d}"


def evaluate_event_for_alert(
    spot_or_cluster: Dict[str, Any],
    osm_context: Optional[Dict[str, Any]] = None,
    ai_classification: Optional[Dict[str, Any]] = None,
    risk_result: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Evaluate a thermal event/cluster against risk score thresholds.
    Triggers an alert if risk_score >= ALERT_HIGH_THRESHOLD (50).
    Applies spatial-temporal deduplication to update existing unresolved alerts within 1.0 km / 12 hrs.
    Returns (alert_record, status_action: 'created', 'updated', or 'ignored').
    """
    # 1. Calculate Risk Priority Score if not provided
    if not risk_result:
        risk_result = calculate_risk_score(spot_or_cluster, osm_context, ai_classification)

    risk_score = risk_result["risk_score"]
    risk_level = risk_result["risk_level"]

    # Threshold Check: Risk score must meet or exceed ALERT_HIGH_THRESHOLD (50)
    if risk_score < ALERT_HIGH_THRESHOLD:
        return None, "ignored_below_threshold"

    lat = float(spot_or_cluster.get("center_latitude") or spot_or_cluster.get("latitude") or 0.0)
    lon = float(spot_or_cluster.get("center_longitude") or spot_or_cluster.get("longitude") or 0.0)
    cluster_id = spot_or_cluster.get("cluster_id") or f"spot_{round(lat, 4)}_{round(lon, 4)}"

    now_ts = time.time()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now_ts))

    alerts = _load_alerts_db()

    # 2. Deduplication Check: Look for unresolved alert within deduplication radius and cooldown window
    matching_alert_idx = None
    for idx, alt in enumerate(alerts):
        # Only deduplicate unresolved alerts (NEW, ACKNOWLEDGED, INVESTIGATING)
        if alt["status"] in ["NEW", "ACKNOWLEDGED", "INVESTIGATING"]:
            alt_lat = alt["latitude"]
            alt_lon = alt["longitude"]
            dist_km = haversine_distance_km(lat, lon, alt_lat, alt_lon)

            # Check spatial radius (1.0 km) and cluster ID match
            if dist_km <= ALERT_DEDUP_RADIUS_KM or alt.get("cluster_id") == cluster_id:
                # Check cooldown window
                created_ts = alt.get("timestamp_epoch", 0.0)
                elapsed_hours = (now_ts - created_ts) / 3600.0
                if elapsed_hours <= ALERT_COOLDOWN_HOURS:
                    matching_alert_idx = idx
                    break

    # 3. If matching unresolved alert exists -> UPDATE existing alert
    if matching_alert_idx is not None:
        target_alert = alerts[matching_alert_idx]
        target_alert["risk_score"] = risk_score
        target_alert["risk_level"] = risk_level
        target_alert["classification"] = risk_result.get("classification", "UNCERTAIN")
        target_alert["persistence_score"] = spot_or_cluster.get("persistence_score", 0.0)
        target_alert["observation_count"] = spot_or_cluster.get("observation_count", 1)
        target_alert["duration_hours"] = spot_or_cluster.get("duration_hours", 0.0)
        target_alert["evidence"] = risk_result.get("reasons", [])
        target_alert["updated_at"] = now_str
        target_alert["features"] = risk_result.get("features", {})

        _save_alerts_db(alerts)
        logger.info(f"Updated existing alert {target_alert['alert_id']} with latest risk score {risk_score}")
        return target_alert, "updated"

    # 4. If no matching unresolved alert exists -> CREATE new alert
    ind_ctx = osm_context or spot_or_cluster.get("industrial_context") or {}
    facility_name = ind_ctx.get("nearby_facility") if isinstance(ind_ctx, dict) else None
    industrial_dist = ind_ctx.get("distance_km") if isinstance(ind_ctx, dict) else None

    new_alert = {
        "alert_id": _generate_alert_id(alerts),
        "cluster_id": cluster_id,
        "latitude": lat,
        "longitude": lon,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "classification": risk_result.get("classification", "UNCERTAIN"),
        "model_source": risk_result.get("model_source", "PROTOTYPE_RULE_ENGINE"),
        "persistence_score": spot_or_cluster.get("persistence_score", 0.0),
        "observation_count": spot_or_cluster.get("observation_count", 1),
        "duration_hours": spot_or_cluster.get("duration_hours", 0.0),
        "industrial_distance_km": industrial_dist,
        "facility_name": facility_name,
        "status": "NEW",
        "evidence": risk_result.get("reasons", []),
        "features": risk_result.get("features", {}),
        "created_at": now_str,
        "updated_at": now_str,
        "timestamp_epoch": now_ts,
        "acknowledged_at": None,
        "acknowledged_by": None,
        "resolved_at": None,
        "resolved_by": None,
        "resolution_notes": None
    }

    alerts.append(new_alert)
    _save_alerts_db(alerts)
    logger.info(f"Created new alert {new_alert['alert_id']} with risk score {risk_score}")
    return new_alert, "created"


def get_all_alerts(
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Retrieve stored alerts with optional filtering and priority sorting."""
    alerts = _load_alerts_db()

    filtered = []
    for a in alerts:
        if status and a["status"].upper() != status.upper():
            continue
        if risk_level and a["risk_level"].upper() != risk_level.upper():
            continue
        filtered.append(a)

    # Sort priority: CRITICAL first, then HIGH, then highest risk score first
    level_order = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
    filtered.sort(key=lambda x: (level_order.get(x["risk_level"], 0), x["risk_score"]), reverse=True)

    return filtered[:limit]


def get_alert_by_id(alert_id: str) -> Optional[Dict[str, Any]]:
    """Fetch single alert record by alert_id."""
    alerts = _load_alerts_db()
    for a in alerts:
        if a["alert_id"].upper() == alert_id.upper():
            return a
    return None


def transition_alert_status(
    alert_id: str,
    new_status: str,
    user: Optional[str] = "Operator",
    notes: Optional[str] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Transition alert status adhering strictly to state machine rules.
    Returns (updated_alert_dict, error_message_if_any).
    """
    alerts = _load_alerts_db()
    target_idx = None
    for idx, a in enumerate(alerts):
        if a["alert_id"].upper() == alert_id.upper():
            target_idx = idx
            break

    if target_idx is None:
        return None, f"Alert with ID {alert_id} not found."

    alert = alerts[target_idx]
    current_status = alert["status"]
    target_status = new_status.upper()

    allowed = ALLOWED_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        return None, f"Invalid state transition from {current_status} to {target_status}. Allowed transitions: {allowed}"

    now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    alert["status"] = target_status
    alert["updated_at"] = now_str

    if target_status == "ACKNOWLEDGED":
        alert["acknowledged_at"] = now_str
        alert["acknowledged_by"] = user or "Operator"
    elif target_status in ["RESOLVED", "DISMISSED"]:
        alert["resolved_at"] = now_str
        alert["resolved_by"] = user or "Operator"
        alert["resolution_notes"] = notes or f"Marked as {target_status} by {user}"

    alerts[target_idx] = alert
    _save_alerts_db(alerts)
    return alert, None


def get_alert_stats() -> Dict[str, Any]:
    """Calculate dashboard summary statistics from stored alert records."""
    alerts = _load_alerts_db()
    now_date_str = time.strftime("%Y-%m-%d", time.gmtime())

    total = len(alerts)
    active = 0
    critical = 0
    high = 0
    acknowledged = 0
    investigating = 0
    resolved_today = 0

    for a in alerts:
        st = a["status"]
        lvl = a["risk_level"]

        if st in ["NEW", "ACKNOWLEDGED", "INVESTIGATING"]:
            active += 1
            if lvl == "CRITICAL":
                critical += 1
            elif lvl == "HIGH":
                high += 1

        if st == "ACKNOWLEDGED":
            acknowledged += 1
        elif st == "INVESTIGATING":
            investigating += 1
        elif st in ["RESOLVED", "DISMISSED"]:
            res_time = a.get("resolved_at") or ""
            if res_time.startswith(now_date_str):
                resolved_today += 1

    return {
        "total_alerts": total,
        "active_alerts": active,
        "critical_alerts": critical,
        "high_alerts": high,
        "acknowledged_alerts": acknowledged,
        "investigating_alerts": investigating,
        "resolved_today": resolved_today,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }
