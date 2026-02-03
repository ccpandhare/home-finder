"""
Commute time calculation and caching.
Uses TravelTime API or Google Maps for train times to King's Cross.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_FILE = CACHE_DIR / "commute_times.json"

# King's Cross coordinates
KX_LAT = 51.5308
KX_LNG = -0.1238


class CommuteChecker:
    """Calculate and cache commute times to King's Cross."""
    
    def __init__(self):
        self.cache = self._load_cache()
        self.traveltime_app_id = os.getenv("TRAVELTIME_APP_ID")
        self.traveltime_api_key = os.getenv("TRAVELTIME_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    def _load_cache(self) -> dict:
        """Load cached commute times."""
        if CACHE_FILE.exists():
            with open(CACHE_FILE) as f:
                return json.load(f)
        return {}
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(self.cache, f, indent=2)
    
    def get_cached_time(self, station_name: str) -> Optional[int]:
        """Get cached commute time for a station."""
        return self.cache.get(station_name.lower())
    
    def cache_time(self, station_name: str, minutes: int) -> None:
        """Cache a commute time."""
        self.cache[station_name.lower()] = minutes
        self._save_cache()
    
    def get_train_time_to_kx(
        self, 
        station_name: str, 
        lat: float, 
        lng: float
    ) -> Optional[int]:
        """
        Get train time from station to King's Cross.
        
        Tries TravelTime API first, falls back to Google Maps.
        Returns time in minutes, or None if unavailable.
        """
        # Check cache first
        cached = self.get_cached_time(station_name)
        if cached is not None:
            return cached
        
        # Try TravelTime API
        if self.traveltime_app_id and self.traveltime_api_key:
            time = self._query_traveltime(lat, lng)
            if time is not None:
                return time
        
        # Try Google Maps
        if self.google_api_key:
            time = self._query_google_maps(lat, lng)
            if time is not None:
                return time
        
        # No API available
        return None
    
    def _query_traveltime(self, lat: float, lng: float) -> Optional[int]:
        """Query TravelTime API for travel time."""
        try:
            # TravelTime API endpoint for time-filter
            url = "https://api.traveltimeapp.com/v4/time-filter"
            
            headers = {
                "Content-Type": "application/json",
                "X-Application-Id": self.traveltime_app_id,
                "X-Api-Key": self.traveltime_api_key,
            }
            
            # Query: can we reach KX from this location within 90 min by public transit?
            payload = {
                "locations": [
                    {"id": "origin", "coords": {"lat": lat, "lng": lng}},
                    {"id": "kings_cross", "coords": {"lat": KX_LAT, "lng": KX_LNG}},
                ],
                "departure_searches": [{
                    "id": "commute",
                    "departure_location_id": "origin",
                    "arrival_location_ids": ["kings_cross"],
                    "departure_time": self._next_weekday_8am(),
                    "travel_time": 5400,  # 90 min max
                    "properties": ["travel_time"],
                    "transportation": {"type": "public_transport"},
                }],
            }
            
            response = httpx.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            if results and results[0].get("locations"):
                travel_time_seconds = results[0]["locations"][0].get("properties", {}).get("travel_time")
                if travel_time_seconds:
                    return travel_time_seconds // 60
            
            return None
            
        except Exception as e:
            print(f"      TravelTime API error: {e}")
            return None
    
    def _query_google_maps(self, lat: float, lng: float) -> Optional[int]:
        """Query Google Maps Directions API for travel time."""
        try:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            
            params = {
                "origin": f"{lat},{lng}",
                "destination": f"{KX_LAT},{KX_LNG}",
                "mode": "transit",
                "transit_mode": "rail",
                "departure_time": int(self._next_weekday_8am_timestamp()),
                "key": self.google_api_key,
            }
            
            response = httpx.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get("routes"):
                duration = data["routes"][0]["legs"][0]["duration"]["value"]
                return duration // 60
            
            return None
            
        except Exception as e:
            print(f"      Google Maps API error: {e}")
            return None
    
    def _next_weekday_8am(self) -> str:
        """Get ISO timestamp for next weekday at 8am."""
        from datetime import timedelta
        
        now = datetime.utcnow()
        # Find next Monday if weekend
        days_ahead = (7 - now.weekday()) % 7  # Days until next Monday
        if now.weekday() < 5:  # Weekday
            days_ahead = 0
        
        target = now.replace(hour=8, minute=0, second=0, microsecond=0)
        target += timedelta(days=days_ahead if days_ahead > 0 else (1 if now.hour >= 8 else 0))
        
        return target.isoformat() + "Z"
    
    def _next_weekday_8am_timestamp(self) -> float:
        """Get Unix timestamp for next weekday at 8am."""
        from datetime import timedelta
        
        now = datetime.utcnow()
        days_ahead = (7 - now.weekday()) % 7
        if now.weekday() < 5:
            days_ahead = 0
        
        target = now.replace(hour=8, minute=0, second=0, microsecond=0)
        target += timedelta(days=days_ahead if days_ahead > 0 else (1 if now.hour >= 8 else 0))
        
        return target.timestamp()
