import os
import math
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
import httpx

logger = logging.getLogger(__name__)

# Default search radius in kilometers (configurable via environment variable)
DEFAULT_SEARCH_RADIUS_KM = float(os.getenv("OSM_SEARCH_RADIUS_KM", "5.0"))

# User-Agent header required by OpenStreetMap usage policies
USER_AGENT = "SIH-26162-FireIntelligence/1.0 (contact: github.com/sih26162)"

# In-memory context cache: (round_lat, round_lon, radius_km) -> {"timestamp": float, "data": dict}
_context_cache: Dict[Tuple[float, float, float], Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes cache TTL for OSM data


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula. Returns distance in kilometers rounded to 2 decimals.
    """
    R = 6371.0088  # Mean Earth radius in km

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


def _categorize_osm_type(type_str: str, category_str: str, name_str: str) -> Tuple[str, str]:
    """
    Map OSM category/type tags to internal categories: 'industrial', 'power', 'urban', 'road'.
    """
    combined = f"{type_str} {category_str} {name_str}".lower()

    if any(k in combined for k in ["industrial", "factory", "refinery", "works", "chemical", "warehouse", "manufacturing", "steel", "oil", "gas", "storage_tank"]):
        category = "industrial_facility"
        if "refinery" in combined:
            category = "refinery"
        elif "chemical" in combo_str if (combo_str := combined) and "chemical" in combo_str else False:
            category = "chemical_plant"
        elif "warehouse" in combined:
            category = "warehouse"
        return ("industrial", category)

    if any(k in combined for k in ["power", "substation", "generator", "electric"]):
        return ("power", "power_plant")

    if any(k in combined for k in ["suburb", "residential", "town", "city", "village", "neighbourhood", "housing"]):
        return ("urban", "residential_area")

    if any(k in combined for k in ["highway", "road", "motorway", "trunk", "primary"]):
        return ("road", "major_road")

    return ("industrial", "industrial_site")


def _classify_context(features: List[Dict[str, Any]], reverse_info: Optional[Dict[str, Any]] = None) -> str:
    """
    Rule-based context classification:
    - INDUSTRIAL: If nearby industrial or power generation features exist.
    - URBAN: If nearby residential or urban features exist (and no industrial).
    - RURAL_OR_AGRICULTURAL: If only roads, rural land, or general suburb info exists.
    - UNKNOWN: If no OSM information is available.
    """
    if not features and not reverse_info:
        return "UNKNOWN"

    types = {f["type"] for f in features}

    if "industrial" in types or "power" in types:
        return "INDUSTRIAL"

    if reverse_info:
        display = str(reverse_info.get("display_name", "")).lower()
        if any(k in display for k in ["industrial", "factory", "refinery", "steel", "port", "power"]):
            return "INDUSTRIAL"

    if "urban" in types:
        return "URBAN"

    if reverse_info:
        addr = reverse_info.get("address", {})
        if any(k in addr for k in ["suburb", "town", "city", "neighbourhood"]):
            return "URBAN"

    if "road" in types or features:
        return "RURAL_OR_AGRICULTURAL"

    return "UNKNOWN"


async def fetch_hotspot_osm_context(
    lat: float,
    lon: float,
    radius_km: float = DEFAULT_SEARCH_RADIUS_KM
) -> Dict[str, Any]:
    """
    Query OpenStreetMap API (Nominatim & Overpass) for nearby industrial facilities and geographic context
    around a given hotspot coordinate (lat, lon).
    Calculates Haversine geodesic distances and assigns rule-based context classification.
    """
    cache_key = (round(lat, 3), round(lon, 3), round(radius_km, 1))
    now = time.time()

    # Check cache
    if cache_key in _context_cache:
        entry = _context_cache[cache_key]
        if now - entry["timestamp"] < CACHE_TTL_SECONDS:
            logger.info(f"Returning cached OSM context for key: {cache_key}")
            return entry["data"]

    features: List[Dict[str, Any]] = []
    reverse_data: Optional[Dict[str, Any]] = None
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Step 1: Query OSM Nominatim Reverse Geocoding API for exact local context
        reverse_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&extratags=1&addressdetails=1"
        try:
            resp = await client.get(reverse_url, headers=headers)
            if resp.status_code == 200:
                reverse_data = resp.json()
                
                # Check if target location itself is an industrial / feature node
                if reverse_data:
                    cat = reverse_data.get("category", "")
                    typ = reverse_data.get("type", "")
                    name = reverse_data.get("display_name", "").split(",")[0]
                    feat_lat = float(reverse_data.get("lat", lat))
                    feat_lon = float(reverse_data.get("lon", lon))
                    dist = haversine_distance_km(lat, lon, feat_lat, feat_lon)

                    f_type, f_cat = _categorize_osm_type(typ, cat, name)
                    features.append({
                        "name": name or "Local Area Feature",
                        "type": f_type,
                        "category": f_cat,
                        "latitude": feat_lat,
                        "longitude": feat_lon,
                        "distance_km": dist,
                        "osm_id": f"{reverse_data.get('osm_type', 'node')}/{reverse_data.get('osm_id', '0')}"
                    })
        except Exception as ex:
            logger.warning(f"Nominatim reverse API lookup failed: {ex}")

        # Step 2: Query OSM Nominatim Search API for nearby industrial facilities
        search_query = f"industrial near {lat},{lon}"
        search_url = f"https://nominatim.openstreetmap.org/search?q={search_query}&format=json&limit=10&extratags=1"
        try:
            s_resp = await client.get(search_url, headers=headers)
            if s_resp.status_code == 200:
                search_results = s_resp.json()
                for item in search_results:
                    f_lat = float(item["lat"])
                    f_lon = float(item["lon"])
                    dist = haversine_distance_km(lat, lon, f_lat, f_lon)
                    if dist <= radius_km:
                        name = item.get("display_name", "").split(",")[0]
                        f_type, f_cat = _categorize_osm_type(item.get("type", ""), item.get("category", ""), name)
                        features.append({
                            "name": name,
                            "type": f_type,
                            "category": f_cat,
                            "latitude": f_lat,
                            "longitude": f_lon,
                            "distance_km": dist,
                            "osm_id": f"{item.get('osm_type', 'way')}/{item.get('osm_id', '0')}"
                        })
        except Exception as ex:
            logger.warning(f"Nominatim search API lookup failed: {ex}")

    # Remove duplicates and sort by distance (closest first)
    unique_features: List[Dict[str, Any]] = []
    seen_ids = set()
    for feat in features:
        if feat["osm_id"] not in seen_ids:
            seen_ids.add(feat["osm_id"])
            unique_features.append(feat)

    unique_features.sort(key=lambda x: x["distance_km"])

    # Rule-based context classification
    context_classification = _classify_context(unique_features, reverse_data)

    result_data = {
        "hotspot": {
            "latitude": lat,
            "longitude": lon
        },
        "search_radius_km": radius_km,
        "context_classification": context_classification,
        "facility_count": len(unique_features),
        "nearby_features": unique_features[:10],
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))
    }

    # Store in memory cache
    _context_cache[cache_key] = {
        "timestamp": now,
        "data": result_data
    }

    return result_data
