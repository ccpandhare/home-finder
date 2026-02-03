"""
UK Train Station Database
Provides station data for commute calculations.
"""

import json
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path
from typing import Optional

import httpx

DATA_DIR = Path(__file__).parent.parent / "data"
STATIONS_FILE = DATA_DIR / "stations.json"

# Approximate center of London for distance calculations
LONDON_LAT = 51.5074
LONDON_LNG = -0.1278


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371  # Earth's radius in km
    
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


class StationDatabase:
    """
    Database of UK train stations.
    Uses National Rail or OpenStreetMap data.
    """
    
    def __init__(self):
        self.stations = self._load_stations()
    
    def _load_stations(self) -> list:
        """Load stations from cache or fetch fresh."""
        if STATIONS_FILE.exists():
            with open(STATIONS_FILE) as f:
                return json.load(f)
        return []
    
    def _save_stations(self, stations: list) -> None:
        """Save stations to cache."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATIONS_FILE, "w") as f:
            json.dump(stations, f, indent=2)
    
    def refresh(self) -> None:
        """
        Refresh station database from source.
        Uses Overpass API (OpenStreetMap) to get UK railway stations.
        """
        print("Fetching UK railway stations from OpenStreetMap...")
        
        # Overpass query for UK railway stations
        overpass_url = "https://overpass-api.de/api/interpreter"
        query = """
        [out:json][timeout:120];
        area["ISO3166-1"="GB"]->.uk;
        (
          node["railway"="station"]["network"~"National Rail|Transport for Wales|ScotRail|Northern|Southeastern|Southern|Thameslink|Great Western|CrossCountry|LNER|TransPennine|Avanti"](area.uk);
        );
        out body;
        """
        
        try:
            response = httpx.post(overpass_url, data={"data": query}, timeout=120)
            response.raise_for_status()
            data = response.json()
            
            stations = []
            for element in data.get("elements", []):
                if element.get("type") == "node":
                    tags = element.get("tags", {})
                    stations.append({
                        "name": tags.get("name", "Unknown"),
                        "lat": element["lat"],
                        "lng": element["lon"],
                        "town": tags.get("addr:city") or tags.get("addr:town"),
                        "operator": tags.get("operator"),
                        "network": tags.get("network"),
                    })
            
            self.stations = stations
            self._save_stations(stations)
            print(f"Saved {len(stations)} stations")
            
        except Exception as e:
            print(f"Error fetching stations: {e}")
            # Fall back to minimal hardcoded list
            self._use_fallback_stations()
    
    def _use_fallback_stations(self) -> None:
        """Use a minimal fallback list of major stations."""
        # This would be expanded with actual station data
        self.stations = [
            {"name": "St Albans City", "lat": 51.7500, "lng": -0.3275, "town": "St Albans"},
            {"name": "Hitchin", "lat": 51.9467, "lng": -0.2604, "town": "Hitchin"},
            {"name": "Stevenage", "lat": 51.9019, "lng": -0.2065, "town": "Stevenage"},
            {"name": "Welwyn Garden City", "lat": 51.8014, "lng": -0.2033, "town": "Welwyn Garden City"},
            {"name": "Hatfield", "lat": 51.7636, "lng": -0.2155, "town": "Hatfield"},
            {"name": "Potters Bar", "lat": 51.6981, "lng": -0.1803, "town": "Potters Bar"},
            {"name": "Luton", "lat": 51.8822, "lng": -0.4147, "town": "Luton"},
            {"name": "Bedford", "lat": 52.1361, "lng": -0.4797, "town": "Bedford"},
            {"name": "Cambridge", "lat": 52.1943, "lng": 0.1376, "town": "Cambridge"},
            {"name": "Peterborough", "lat": 52.5750, "lng": -0.2486, "town": "Peterborough"},
        ]
        self._save_stations(self.stations)
    
    def get_stations_near_london(self, radius_km: float = 150) -> list:
        """Get all stations within radius of London."""
        if not self.stations:
            self.refresh()
        
        nearby = []
        for station in self.stations:
            distance = haversine_distance(
                LONDON_LAT, LONDON_LNG,
                station["lat"], station["lng"]
            )
            if distance <= radius_km:
                nearby.append({**station, "distance_km": round(distance, 1)})
        
        return sorted(nearby, key=lambda x: x["distance_km"])
    
    def find_nearest(self, lat: float, lng: float) -> Optional[dict]:
        """Find the nearest station to given coordinates."""
        if not self.stations:
            self.refresh()
        
        nearest = None
        min_distance = float("inf")
        
        for station in self.stations:
            distance = haversine_distance(lat, lng, station["lat"], station["lng"])
            if distance < min_distance:
                min_distance = distance
                nearest = {**station, "distance_km": round(distance, 1)}
        
        return nearest
