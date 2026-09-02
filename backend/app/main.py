import os
# Prevent OpenBLAS multi-thread memory allocation errors on Windows
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import asyncio
from typing import Optional, List
from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.services.firms_service import fetch_firms_hotspots
from app.services.osm_service import fetch_hotspot_osm_context, DEFAULT_SEARCH_RADIUS_KM
from app.services.persistence_service import detect_persistent_clusters, DEFAULT_CLUSTER_RADIUS_KM
from app.ml.classifier import classify_thermal_event
from app.services.risk_service import calculate_risk_score
from app.services.alert_service import (
    evaluate_event_for_alert,
    get_all_alerts,
    get_alert_by_id,
    transition_alert_status,
    get_alert_stats
)

# Load environment variables from .env file if available
load_dotenv()

# Initialize FastAPI application
app = FastAPI(
    title="SIH 26162 Backend API",
    description="Backend API for Industrial Fire & Persistent Thermal Source Intelligence Platform",
    version="1.0.0"
)

# Configure CORS (Cross-Origin Resource Sharing)
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """Root Endpoint - Basic sanity check to confirm backend server is running."""
    return {
        "message": "SIH 26162 backend is running"
    }


@app.get("/api/health")
def health_check():
    """Health Check Endpoint - Used by frontend dashboard to verify API connectivity."""
    return {
        "status": "healthy",
        "service": "SIH 26162 Backend",
        "version": "1.0.0"
    }


@app.get("/api/hotspots")
async def get_hotspots(
    region: str = Query("india", description="Predefined region: 'india' or 'andhra_pradesh'"),
    bbox: Optional[str] = Query(None, description="Custom bounding box: min_lon,min_lat,max_lon,max_lat"),
    force_refresh: bool = Query(False, description="Bypass cache and force fresh request from NASA FIRMS")
):
    """
    Fetch active fire/thermal hotspots from NASA FIRMS.
    Returns standardized JSON array of thermal hotspot observations.
    """
    parsed_bbox: Optional[List[float]] = None
    if bbox:
        try:
            parts = [float(p.strip()) for p in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError("bbox must contain exactly 4 comma-separated numbers: min_lon,min_lat,max_lon,max_lat")
            parsed_bbox = parts
        except Exception as err:
            raise HTTPException(status_code=400, detail=f"Invalid bbox format: {str(err)}")

    try:
        data = await fetch_firms_hotspots(
            region=region,
            custom_bbox=parsed_bbox,
            force_refresh=force_refresh
        )
        return data
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to retrieve NASA FIRMS satellite data: {str(e)}"
        )


@app.get("/api/hotspots/context")
async def get_hotspot_context(
    lat: float = Query(..., description="Latitude of hotspot"),
    lon: float = Query(..., description="Longitude of hotspot"),
    radius_km: float = Query(DEFAULT_SEARCH_RADIUS_KM, description="Search radius in kilometers")
):
    """
    Fetch OpenStreetMap geographic & industrial context for a specific hotspot coordinate.
    Calculates Haversine geodesic distances to nearby facilities and returns context classification.
    """
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude coordinates")

    try:
        context_data = await fetch_hotspot_osm_context(lat=lat, lon=lon, radius_km=radius_km)
        return context_data
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to retrieve OpenStreetMap context: {str(e)}"
        )


@app.get("/api/persistent-hotspots")
async def get_persistent_hotspots(
    region: str = Query("india", description="Predefined region: 'india' or 'andhra_pradesh'"),
    bbox: Optional[str] = Query(None, description="Custom bounding box: min_lon,min_lat,max_lon,max_lat"),
    min_score: float = Query(0.0, description="Minimum persistence score threshold (0 - 100)"),
    cluster_radius_km: float = Query(DEFAULT_CLUSTER_RADIUS_KM, description="Spatial clustering radius in km")
):
    """
    Persistent Thermal Source Detection Endpoint.
    Groups NASA FIRMS observations into spatial-temporal clusters and calculates transparent persistence scores.
    """
    parsed_bbox: Optional[List[float]] = None
    if bbox:
        try:
            parts = [float(p.strip()) for p in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError("bbox must contain exactly 4 comma-separated numbers: min_lon,min_lat,max_lon,max_lat")
            parsed_bbox = parts
        except Exception as err:
            raise HTTPException(status_code=400, detail=f"Invalid bbox format: {str(err)}")

    try:
        clusters_data = await detect_persistent_clusters(
            region=region,
            custom_bbox=parsed_bbox,
            min_score=min_score,
            cluster_radius_km=cluster_radius_km
        )
        return clusters_data
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to perform persistent thermal cluster analysis: {str(e)}"
        )


@app.get("/api/hotspots/classify")
async def classify_hotspot_endpoint(
    lat: float = Query(..., description="Latitude of hotspot"),
    lon: float = Query(..., description="Longitude of hotspot"),
    frp: float = Query(0.0, description="Fire Radiative Power in MW"),
    brightness: float = Query(320.0, description="Brightness temperature in K"),
    confidence: str = Query("nominal", description="FIRMS confidence"),
    observation_count: int = Query(1, description="Observation count in cluster"),
    duration_hours: float = Query(0.0, description="Duration in hours"),
    spatial_radius_km: float = Query(0.0, description="Spatial radius in km"),
    persistence_score: float = Query(0.0, description="Persistence score 0 - 100")
):
    """
    Explainable AI Classification Endpoint.
    Evaluates FIRMS, OSM, and Persistence features to predict thermal event category.
    Returns prediction, confidence percentage, model source/status, supporting indicators, and feature map.
    """
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude coordinates")

    try:
        try:
            osm_context = await asyncio.wait_for(fetch_hotspot_osm_context(lat=lat, lon=lon, radius_km=5.0), timeout=5.0)
        except Exception:
            osm_context = None

        spot_dict = {
            "latitude": lat,
            "longitude": lon,
            "frp": frp,
            "brightness": brightness,
            "confidence": confidence,
            "observation_count": observation_count,
            "duration_hours": duration_hours,
            "spatial_radius_km": spatial_radius_km,
            "persistence_score": persistence_score,
            "industrial_context": osm_context
        }

        result = classify_thermal_event(spot_dict, osm_context=osm_context)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Classification error: {str(e)}"
        )


@app.get("/api/hotspots/risk")
async def get_hotspot_risk(
    lat: float = Query(..., description="Latitude of hotspot"),
    lon: float = Query(..., description="Longitude of hotspot"),
    frp: float = Query(0.0, description="Fire Radiative Power in MW"),
    brightness: float = Query(320.0, description="Brightness temperature in K"),
    confidence: str = Query("nominal", description="FIRMS confidence"),
    observation_count: int = Query(1, description="Observation count"),
    duration_hours: float = Query(0.0, description="Duration in hours"),
    spatial_radius_km: float = Query(0.0, description="Spatial radius in km"),
    persistence_score: float = Query(0.0, description="Persistence score 0 - 100")
):
    """
    Explainable Risk Priority Scoring Endpoint.
    Converts 5 weighted components into a 0 - 100 priority score and risk level (LOW, MODERATE, HIGH, CRITICAL).
    """
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude coordinates")

    try:
        try:
            osm_context = await asyncio.wait_for(fetch_hotspot_osm_context(lat=lat, lon=lon, radius_km=5.0), timeout=5.0)
        except Exception:
            osm_context = None

        spot_dict = {
            "latitude": lat,
            "longitude": lon,
            "frp": frp,
            "brightness": brightness,
            "confidence": confidence,
            "observation_count": observation_count,
            "duration_hours": duration_hours,
            "spatial_radius_km": spatial_radius_km,
            "persistence_score": persistence_score,
            "industrial_context": osm_context
        }

        ai_res = classify_thermal_event(spot_dict, osm_context=osm_context)
        risk_res = calculate_risk_score(spot_dict, osm_context=osm_context, ai_classification=ai_res)
        return risk_res
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Risk calculation error: {str(e)}"
        )


@app.get("/api/hotspots/priority-ranking")
async def get_priority_ranking(
    region: str = Query("india", description="Predefined region: 'india' or 'andhra_pradesh'"),
    limit: int = Query(10, description="Number of top priority items to return")
):
    """
    Highest Risk Thermal Events Leaderboard.
    Ranks spatial-temporal clusters by investigation priority score (0 - 100).
    """
    try:
        clusters_res = await detect_persistent_clusters(region=region, min_score=20.0)
        clusters_list = clusters_res.get("clusters", [])

        if len(clusters_list) < limit:
            clusters_res_all = await detect_persistent_clusters(region=region, min_score=0.0)
            clusters_list = clusters_res_all.get("clusters", [])

        sorted_candidates = sorted(
            clusters_list,
            key=lambda c: (c.get("persistence_score", 0), c.get("observation_count", 0)),
            reverse=True
        )[:limit * 2]

        ranked_items = []
        for cl in sorted_candidates:
            c_lat = cl["center_latitude"]
            c_lon = cl["center_longitude"]
            top_obs = cl["observations"][0] if cl["observations"] else {}

            spot_dict = {
                "latitude": c_lat,
                "longitude": c_lon,
                "frp": top_obs.get("frp", 0.0),
                "brightness": top_obs.get("brightness", 320.0),
                "confidence": top_obs.get("confidence", "nominal"),
                "observation_count": cl["observation_count"],
                "duration_hours": cl["duration_hours"],
                "spatial_radius_km": cl["spatial_radius_km"],
                "persistence_score": cl["persistence_score"],
                "industrial_context": cl.get("industrial_context")
            }

            ai_res = classify_thermal_event(spot_dict, osm_context=cl.get("industrial_context"))
            risk_res = calculate_risk_score(spot_dict, osm_context=cl.get("industrial_context"), ai_classification=ai_res)

            ind_ctx = cl.get("industrial_context") or {}
            facility_name = ind_ctx.get("nearby_facility") or "None"
            dist_km = ind_ctx.get("distance_km")

            ranked_items.append({
                "rank": 0,
                "cluster_id": cl["cluster_id"],
                "latitude": c_lat,
                "longitude": c_lon,
                "risk_score": risk_res["risk_score"],
                "risk_level": risk_res["risk_level"],
                "classification": ai_res["classification"],
                "industrial_facility": facility_name,
                "industrial_distance_km": dist_km,
                "persistence_score": cl["persistence_score"],
                "observation_count": cl["observation_count"],
                "duration_hours": cl["duration_hours"],
                "reasons": risk_res["reasons"]
            })

        ranked_items.sort(key=lambda x: x["risk_score"], reverse=True)

        final_top = ranked_items[:limit]
        for i, item in enumerate(final_top):
            item["rank"] = i + 1

        return {
            "region": region,
            "total_ranked": len(final_top),
            "priority_events": final_top
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Priority ranking error: {str(e)}"
        )


# =====================================================================
# PHASE 7: ALERT DETECTION & INCIDENT MANAGEMENT REST ENDPOINTS
# =====================================================================

@app.get("/api/alerts")
def list_alerts(
    status: Optional[str] = Query(None, description="Filter by alert status: NEW, ACKNOWLEDGED, INVESTIGATING, RESOLVED, DISMISSED"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: CRITICAL, HIGH, MODERATE, LOW"),
    limit: int = Query(50, description="Max alerts to return")
):
    """Retrieve stored alerts with optional status and risk level filtering."""
    alerts = get_all_alerts(status=status, risk_level=risk_level, limit=limit)
    return {
        "count": len(alerts),
        "alerts": alerts
    }


@app.get("/api/alerts/stats")
def get_dashboard_alert_stats():
    """Retrieve active alert dashboard statistics."""
    return get_alert_stats()


@app.get("/api/alerts/{alert_id}")
def get_single_alert(alert_id: str):
    """Fetch details of a single alert by alert_id."""
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found.")
    return alert


@app.post("/api/alerts/evaluate")
async def evaluate_region_alerts(
    region: str = Query("india", description="Predefined region to evaluate")
):
    """
    Auto-evaluate active persistent thermal clusters in region.
    Triggers new alerts for risk scores >= 50 and updates existing alerts via deduplication logic.
    """
    try:
        clusters_res = await detect_persistent_clusters(region=region, min_score=20.0)
        clusters_list = clusters_res.get("clusters", [])

        results = []
        for cl in clusters_list:
            c_lat = cl["center_latitude"]
            c_lon = cl["center_longitude"]
            top_obs = cl["observations"][0] if cl["observations"] else {}

            spot_dict = {
                "latitude": c_lat,
                "longitude": c_lon,
                "frp": top_obs.get("frp", 0.0),
                "brightness": top_obs.get("brightness", 320.0),
                "confidence": top_obs.get("confidence", "nominal"),
                "observation_count": cl["observation_count"],
                "duration_hours": cl["duration_hours"],
                "spatial_radius_km": cl["spatial_radius_km"],
                "persistence_score": cl["persistence_score"],
                "cluster_id": cl["cluster_id"],
                "industrial_context": cl.get("industrial_context")
            }

            ai_res = classify_thermal_event(spot_dict, osm_context=cl.get("industrial_context"))
            risk_res = calculate_risk_score(spot_dict, osm_context=cl.get("industrial_context"), ai_classification=ai_res)

            alert_record, action = evaluate_event_for_alert(
                spot_dict,
                osm_context=cl.get("industrial_context"),
                ai_classification=ai_res,
                risk_result=risk_res
            )

            if alert_record:
                results.append({
                    "alert_id": alert_record["alert_id"],
                    "action": action,
                    "risk_score": alert_record["risk_score"],
                    "risk_level": alert_record["risk_level"],
                    "status": alert_record["status"]
                })

        return {
            "evaluated_clusters": len(clusters_list),
            "alerts_affected": len(results),
            "evaluations": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert evaluation error: {str(e)}")


@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    user: str = Query("Operator", description="Operator name")
):
    """Transition alert status from NEW to ACKNOWLEDGED."""
    alert, error = transition_alert_status(alert_id, "ACKNOWLEDGED", user=user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return alert


@app.post("/api/alerts/{alert_id}/investigate")
def investigate_alert(
    alert_id: str,
    user: str = Query("Operator", description="Operator name")
):
    """Transition alert status from ACKNOWLEDGED to INVESTIGATING."""
    alert, error = transition_alert_status(alert_id, "INVESTIGATING", user=user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return alert


@app.post("/api/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    user: str = Query("Operator", description="Operator name"),
    notes: Optional[str] = Query(None, description="Resolution notes")
):
    """Transition alert status to RESOLVED."""
    alert, error = transition_alert_status(alert_id, "RESOLVED", user=user, notes=notes)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return alert


@app.post("/api/alerts/{alert_id}/dismiss")
def dismiss_alert(
    alert_id: str,
    user: str = Query("Operator", description="Operator name"),
    notes: Optional[str] = Query(None, description="Dismissal reason")
):
    """Transition alert status to DISMISSED."""
    alert, error = transition_alert_status(alert_id, "DISMISSED", user=user, notes=notes)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return alert
