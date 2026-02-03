"""
Geographic utilities - postcode lookup, distance calculations.
"""

from typing import Optional

import httpx

from .stations import StationDatabase, haversine_distance


def postcode_to_coords(postcode: str) -> Optional[dict]:
    """
    Convert UK postcode to coordinates.
    Uses postcodes.io (free, no API key).
    """
    try:
        # Clean postcode
        postcode = postcode.strip().upper().replace(" ", "")
        
        url = f"https://api.postcodes.io/postcodes/{postcode}"
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get("status") == 200:
            result = data["result"]
            return {
                "lat": result["latitude"],
                "lng": result["longitude"],
                "town": result.get("admin_ward") or result.get("parish"),
                "district": result.get("admin_district"),
            }
        
        return None
        
    except Exception as e:
        print(f"Postcode lookup error: {e}")
        return None


def find_nearest_station(lat: float, lng: float) -> Optional[dict]:
    """
    Find the nearest train station to coordinates.
    Returns station info with walking time estimate.
    """
    db = StationDatabase()
    station = db.find_nearest(lat, lng)
    
    if station:
        # Estimate walking time (assuming 5 km/h walking speed)
        distance_km = station["distance_km"]
        walking_minutes = int((distance_km / 5) * 60)
        station["walking_minutes"] = walking_minutes
    
    return station


def get_area_bounds(lat: float, lng: float, radius_km: float = 5) -> dict:
    """
    Get bounding box around a point.
    Useful for search queries.
    """
    # Rough approximation (1 degree latitude ≈ 111 km)
    lat_delta = radius_km / 111
    lng_delta = radius_km / (111 * abs(cos(radians(lat))))
    
    return {
        "north": lat + lat_delta,
        "south": lat - lat_delta,
        "east": lng + lng_delta,
        "west": lng - lng_delta,
    }


def coords_to_postcode(lat: float, lng: float) -> Optional[str]:
    """
    Reverse geocode coordinates to nearest postcode.
    """
    try:
        url = "https://api.postcodes.io/postcodes"
        response = httpx.get(
            url,
            params={"lon": lng, "lat": lat, "limit": 1},
            timeout=10,
        )
        response.raise_for_status()
        
        data = response.json()
        if data.get("result"):
            return data["result"][0]["postcode"]
        
        return None
        
    except Exception as e:
        print(f"Reverse geocode error: {e}")
        return None


# Import math functions needed
from math import radians, cos
