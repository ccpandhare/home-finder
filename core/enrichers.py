"""
Area enrichment - gather amenities, nature data, etc.
Uses OpenStreetMap Overpass API (free) or Google Places.
"""

import os
from typing import Optional

import httpx


def gather_amenities(lat: float, lng: float, radius_m: int = 1500) -> dict:
    """
    Gather amenity data for an area.
    
    Returns dict with supermarkets, pharmacies, etc.
    """
    amenities = {
        "supermarkets": [],
        "pharmacies": [],
        "restaurants": [],
    }
    
    # Try Overpass API first (free)
    try:
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Query for amenities within radius
        query = f"""
        [out:json][timeout:30];
        (
          node["shop"="supermarket"](around:{radius_m},{lat},{lng});
          node["amenity"="pharmacy"](around:{radius_m},{lat},{lng});
        );
        out body;
        """
        
        response = httpx.post(overpass_url, data={"data": query}, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            item = {
                "name": tags.get("name", tags.get("brand", "Unknown")),
                "lat": element["lat"],
                "lng": element["lon"],
                "distance_m": _calculate_distance_m(lat, lng, element["lat"], element["lon"]),
            }
            
            if tags.get("shop") == "supermarket":
                amenities["supermarkets"].append(item)
            elif tags.get("amenity") == "pharmacy":
                amenities["pharmacies"].append(item)
        
        # Sort by distance
        for key in amenities:
            amenities[key] = sorted(amenities[key], key=lambda x: x["distance_m"])
        
    except Exception as e:
        print(f"      Error gathering amenities: {e}")
    
    return amenities


def gather_nature_data(lat: float, lng: float, radius_m: int = 2000) -> dict:
    """
    Gather nature/green space data for an area.
    
    Returns dict with parks, nature reserves, etc.
    """
    nature = {
        "parks": [],
        "parks_count": 0,
        "nature_reserves": [],
        "countryside_access": False,
    }
    
    try:
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Query for parks and green spaces
        query = f"""
        [out:json][timeout:30];
        (
          way["leisure"="park"](around:{radius_m},{lat},{lng});
          relation["leisure"="park"](around:{radius_m},{lat},{lng});
          way["leisure"="nature_reserve"](around:{radius_m},{lat},{lng});
          way["landuse"="forest"](around:{radius_m},{lat},{lng});
        );
        out center body;
        """
        
        response = httpx.post(overpass_url, data={"data": query}, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        seen_names = set()
        
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")
            
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            
            # Get center coordinates
            center = element.get("center", {})
            elem_lat = center.get("lat", element.get("lat", lat))
            elem_lng = center.get("lon", element.get("lon", lng))
            
            item = {
                "name": name,
                "lat": elem_lat,
                "lng": elem_lng,
                "distance_m": _calculate_distance_m(lat, lng, elem_lat, elem_lng),
                "type": tags.get("leisure") or tags.get("landuse"),
            }
            
            if tags.get("leisure") == "park":
                nature["parks"].append(item)
            elif tags.get("leisure") == "nature_reserve" or tags.get("landuse") == "forest":
                nature["nature_reserves"].append(item)
                nature["countryside_access"] = True
        
        # Sort by distance
        nature["parks"] = sorted(nature["parks"], key=lambda x: x["distance_m"])[:10]
        nature["nature_reserves"] = sorted(nature["nature_reserves"], key=lambda x: x["distance_m"])[:5]
        nature["parks_count"] = len(nature["parks"])
        
    except Exception as e:
        print(f"      Error gathering nature data: {e}")
    
    return nature


def _calculate_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """Calculate distance in meters between two points."""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371000  # Earth's radius in meters
    
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return int(R * c)
