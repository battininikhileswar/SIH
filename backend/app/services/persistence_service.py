import os
import math
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from app.services.firms_service import fetch_firms_hotspots
from app.services.osm_service import fetch_hotspot_osm_context, haversine_distance_km

logger = logging.getLogger(__name__)

# Default spatial clustering threshold in kilometers
DEFAULT_CLUSTER_RADIUS_KM = float(os.getenv("SPATIAL_CLUSTER_THRESHOLD_KM", "1.0"))


def _parse_utc_timestamp(acquired_at_str: str) -> Optional[datetime]:
    """Parse 'YYYY-MM-DD HH:MM UTC' string into datetime object."""
    try:
        clean_str = acquired_at_str.replace(" UTC", "").strip()
        return datetime.strptime(clean_str, "%Y-%m-%d %H:%M")
    except Exception:
        return None


def _calculate_persistence_score(
    obs_count: int,
    duration_hours: float,
    spatial_radius_km: float
) -> Tuple[int, str]:
    """
    Calculate a transparent, deterministic persistence score (0 - 100).
    Formula:
    - Observation Factor (40%): min(100, obs_count * 15)
    - Temporal Duration Factor (40%): min(100, (duration_hours / 12.0) * 100)
    - Spatial Consistency Factor (20%): max(0, 100 - (spatial_radius_km * 50))
    
    Returns:
    (score_integer, classification_label)
    """
    score_obs = min(100.0, float(obs_count) * 15.0)
    score_duration = min(100.0, (duration_hours / 12.0) * 100.0)
    score_spatial = max(0.0, 100.0 - (spatial_radius_km * 50.0))

    total_score = round(0.40 * score_obs + 0.40 * score_duration + 0.20 * score_spatial)
    total_score = max(0, min(100, total_score))

    if total_score >= 81:
        classification = "HIGHLY PERSISTENT"
    elif total_score >= 61:
        classification = "PERSISTENT"
    elif total_score >= 31:
        classification = "SUSPICIOUS"
    else:
        classification = "TEMPORARY"

    return total_score, classification


async def detect_persistent_clusters(
    region: str = "india",
    custom_bbox: Optional[List[float]] = None,
    min_score: float = 0.0,
    cluster_radius_km: float = DEFAULT_CLUSTER_RADIUS_KM,
    fetch_context_for_top: int = 5
) -> Dict[str, Any]:
    """
    Process real NASA FIRMS observations to group thermal hotspots into spatial-temporal clusters.
    Calculates first/last detected times, duration, spatial radius, persistence score, and industrial context.
    """
    now = time.time()
    
    # 1. Fetch real active fire hotspots from NASA FIRMS service
    firms_response = await fetch_firms_hotspots(region=region, custom_bbox=custom_bbox)
    raw_hotspots = firms_response.get("hotspots", [])

    if not raw_hotspots:
        return {
            "source": "NASA FIRMS Persistence Engine",
            "region": region,
            "total_clusters": 0,
            "persistent_cluster_count": 0,
            "spatial_threshold_km": cluster_radius_km,
            "clusters": [],
            "status": "ok",
            "message": "Zero thermal hotspots detected in selected region for cluster analysis.",
            "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))
        }

    # 2. Perform Spatial Clustering using Haversine Geodesic Distance
    clusters_raw: List[Dict[str, Any]] = []

    for spot in raw_hotspots:
        lat, lon = spot["latitude"], spot["longitude"]
        assigned = False

        for cl in clusters_raw:
            c_lat, c_lon = cl["center_lat"], cl["center_lon"]
            dist = haversine_distance_km(lat, lon, c_lat, c_lon)

            if dist <= cluster_radius_km:
                cl["observations"].append(spot)
                # Recalculate centroid (mean latitude & longitude)
                n = len(cl["observations"])
                cl["center_lat"] = round(sum(o["latitude"] for o in cl["observations"]) / n, 5)
                cl["center_lon"] = round(sum(o["longitude"] for o in cl["observations"]) / n, 5)
                assigned = True
                break

        if not assigned:
            clusters_raw.append({
                "center_lat": lat,
                "center_lon": lon,
                "observations": [spot]
            })

    # 3. Temporal Analysis & Persistence Scoring
    processed_clusters: List[Dict[str, Any]] = []

    for cl in clusters_raw:
        obs_list = cl["observations"]
        
        parsed_obs = []
        for o in obs_list:
            dt = _parse_utc_timestamp(o.get("acquired_at", ""))
            parsed_obs.append((dt, o))

        parsed_obs.sort(key=lambda x: x[0] if x[0] else datetime.min)
        sorted_obs = [item[1] for item in parsed_obs]

        first_obs = sorted_obs[0]
        last_obs = sorted_obs[-1]

        first_dt = parsed_obs[0][0]
        last_dt = parsed_obs[-1][0]

        if first_dt and last_dt:
            duration_seconds = max(0.0, (last_dt - first_dt).total_seconds())
            duration_hours = round(duration_seconds / 3600.0, 2)
        else:
            duration_hours = 0.0

        c_lat, c_lon = cl["center_lat"], cl["center_lon"]
        max_dist = max(haversine_distance_km(c_lat, c_lon, o["latitude"], o["longitude"]) for o in sorted_obs)
        spatial_radius_km = round(max_dist, 2)

        obs_count = len(sorted_obs)
        score, classification = _calculate_persistence_score(obs_count, duration_hours, spatial_radius_km)

        if score < min_score:
            continue

        cluster_id = f"cluster_{round(c_lat, 3)}_{round(c_lon, 3)}"

        processed_clusters.append({
            "cluster_id": cluster_id,
            "center_latitude": c_lat,
            "center_longitude": c_lon,
            "observation_count": obs_count,
            "first_detected": first_obs.get("acquired_at", "N/A"),
            "last_detected": last_obs.get("acquired_at", "N/A"),
            "duration_hours": duration_hours,
            "spatial_radius_km": spatial_radius_km,
            "persistence_score": score,
            "classification": classification,
            "observations": sorted_obs,
            "industrial_context": None,
            "has_sufficient_history": obs_count >= 2
        })

    # Sort clusters by persistence score descending
    processed_clusters.sort(key=lambda x: x["persistence_score"], reverse=True)

    # 4. On-demand OSM context enrichment for top N clusters to maintain high performance
    for cl in processed_clusters[:fetch_context_for_top]:
        c_lat, c_lon = cl["center_latitude"], cl["center_longitude"]
        osm_context = await fetch_hotspot_osm_context(c_lat, c_lon, radius_km=5.0)
        
        if osm_context and osm_context.get("nearby_features"):
            closest_facility = osm_context["nearby_features"][0]
            cl["industrial_context"] = {
                "context_classification": osm_context.get("context_classification", "UNKNOWN"),
                "nearby_facility": closest_facility.get("name"),
                "facility_type": closest_facility.get("type"),
                "facility_category": closest_facility.get("category"),
                "distance_km": closest_facility.get("distance_km")
            }
        else:
            cl["industrial_context"] = {
                "context_classification": osm_context.get("context_classification", "UNKNOWN"),
                "nearby_facility": None,
                "facility_type": None,
                "facility_category": None,
                "distance_km": None
            }

    persistent_count = sum(1 for c in processed_clusters if c["classification"] in ["PERSISTENT", "HIGHLY PERSISTENT"])

    return {
        "source": "NASA FIRMS Persistence Engine",
        "region": region,
        "total_clusters": len(processed_clusters),
        "persistent_cluster_count": persistent_count,
        "spatial_threshold_km": cluster_radius_km,
        "clusters": processed_clusters,
        "status": "ok",
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))
    }
