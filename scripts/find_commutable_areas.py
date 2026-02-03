#!/usr/bin/env python3
"""
Find Commutable Areas
Identifies train stations and areas within specified commute time to King's Cross.

Usage:
    python scripts/find_commutable_areas.py --max-minutes 60
    python scripts/find_commutable_areas.py --refresh-stations
    python scripts/find_commutable_areas.py --check "AL1 1AA"
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.commute import CommuteChecker
from core.stations import StationDatabase

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"


def load_criteria() -> dict:
    """Load search criteria from config."""
    with open(CONFIG_DIR / "criteria.yaml") as f:
        return yaml.safe_load(f)


def save_areas(areas: list) -> None:
    """Save discovered areas to config."""
    areas_file = CONFIG_DIR / "areas.yaml"
    
    # Load existing to preserve manual additions
    existing = {}
    if areas_file.exists():
        with open(areas_file) as f:
            existing = yaml.safe_load(f) or {}
    
    existing["areas"] = areas
    existing["last_updated"] = datetime.now().isoformat()
    
    with open(areas_file, "w") as f:
        yaml.dump(existing, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Saved {len(areas)} areas to {areas_file}")


def is_london_zone_1_4(name: str, station: str, lat: float, lng: float) -> bool:
    """
    Check if a station is in London Zones 1-4 (should be excluded).
    Uses keyword matching + distance from central London.
    """
    from math import radians, sin, cos, sqrt, atan2
    
    # Central London (King's Cross)
    CENTRAL_LAT, CENTRAL_LNG = 51.5308, -0.1238
    MIN_DISTANCE_KM = 15  # Roughly Zone 4 boundary
    
    # Known London Zone 1-4 keywords
    london_keywords = [
        'london ', 'kings cross', "king's cross", 'st pancras', 'euston', 'paddington',
        'liverpool street', 'fenchurch', 'cannon street', 'waterloo', 'victoria',
        'charing cross', 'blackfriars', 'moorgate', 'marylebone', 'old street',
        'angel', 'bank', 'monument', 'tower', 'aldgate', 'shoreditch',
        'whitechapel', 'stratford', 'west ham', 'canning town', 'canary wharf',
        'greenwich', 'lewisham', 'peckham', 'brixton', 'clapham', 'battersea',
        'vauxhall', 'elephant', 'borough', 'southwark', 'bermondsey',
        'finsbury park', 'highbury', 'islington', 'hackney', 'dalston',
        'bethnal green', 'mile end', 'bow', 'tottenham hale', 'seven sisters',
        'camden', 'kentish town', 'hampstead', 'kilburn', 'willesden',
        'cricklewood', 'west hampstead', 'finchley', 'barnet', 'edgware',
        'harrow', 'wembley', 'ealing', 'acton', 'shepherd', 'hammersmith',
        'fulham', 'putney', 'wandsworth', 'wimbledon', 'tooting', 'balham',
        'streatham', 'tulse hill', 'herne hill', 'denmark hill', 'penge',
        'crystal palace', 'sydenham', 'forest hill', 'catford', 'ladywell',
        'brockley', 'new cross', 'deptford', 'surrey quays', 'canada water',
        'rotherhithe', 'wapping', 'shadwell', 'limehouse', 'poplar',
        'drayton park', 'essex road', 'hornsey', 'crouch hill', 'harringay'
    ]
    
    name_lower = name.lower()
    station_lower = station.lower()
    
    # Check keywords
    if any(kw in name_lower or kw in station_lower for kw in london_keywords):
        return True
    
    # Check distance (haversine)
    R = 6371
    lat1, lng1, lat2, lng2 = map(radians, [CENTRAL_LAT, CENTRAL_LNG, lat, lng])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    dist_km = 2 * R * atan2(sqrt(a), sqrt(1-a))
    
    return dist_km < MIN_DISTANCE_KM


def find_commutable_stations(max_minutes: int, walking_buffer: int = 10) -> list:
    """
    Find all stations within commute time of King's Cross.
    Excludes London Zones 1-4 (focus on commuter belt).
    
    Args:
        max_minutes: Maximum total commute time
        walking_buffer: Minutes to allow for walking to station
    
    Returns:
        List of station dicts with commute times
    """
    print(f"🔍 Finding stations within {max_minutes} min of King's Cross...")
    print(f"   (including {walking_buffer} min walking buffer)")
    print(f"   (excluding London Zones 1-4)")
    
    effective_max = max_minutes - walking_buffer
    
    # Initialize services
    stations_db = StationDatabase()
    commute_checker = CommuteChecker()
    
    # Get candidate stations (rough geographic filter first)
    candidates = stations_db.get_stations_near_london(radius_km=150)
    print(f"   Found {len(candidates)} candidate stations to check")
    
    commutable = []
    
    for i, station in enumerate(candidates):
        if (i + 1) % 50 == 0:
            print(f"   Checking station {i + 1}/{len(candidates)}...")
        
        # Check cache first
        cached = commute_checker.get_cached_time(station["name"])
        if cached is not None:
            train_time = cached
        else:
            # Query API
            train_time = commute_checker.get_train_time_to_kx(
                station["name"],
                station["lat"],
                station["lng"]
            )
            if train_time is not None:
                commute_checker.cache_time(station["name"], train_time)
        
        if train_time is not None and train_time <= effective_max:
            area_name = station["town"] or station["name"].replace(" Station", "")
            
            # Skip London Zones 1-4
            if is_london_zone_1_4(area_name, station["name"], station["lat"], station["lng"]):
                continue
                
            commutable.append({
                "name": area_name,
                "station": station["name"],
                "commute_minutes": train_time + walking_buffer,
                "train_minutes": train_time,
                "lat": station["lat"],
                "lng": station["lng"],
                "status": "pending",
                "explored_at": None,
                "score": None,
            })
    
    # Sort by commute time
    commutable.sort(key=lambda x: x["commute_minutes"])
    
    print(f"✅ Found {len(commutable)} stations within {max_minutes} min commute")
    return commutable


def check_postcode(postcode: str) -> None:
    """Check commute time for a specific postcode."""
    from core.geo import postcode_to_coords, find_nearest_station
    
    print(f"🔍 Checking postcode: {postcode}")
    
    coords = postcode_to_coords(postcode)
    if not coords:
        print("❌ Could not find coordinates for postcode")
        return
    
    station = find_nearest_station(coords["lat"], coords["lng"])
    if not station:
        print("❌ Could not find nearby station")
        return
    
    commute_checker = CommuteChecker()
    train_time = commute_checker.get_train_time_to_kx(
        station["name"],
        station["lat"],
        station["lng"]
    )
    
    if train_time is None:
        print("❌ Could not calculate commute time")
        return
    
    walking_time = station.get("walking_minutes", 10)
    total = train_time + walking_time
    
    print(f"\n📍 {postcode}")
    print(f"🚶 Nearest station: {station['name']} ({walking_time} min walk)")
    print(f"🚂 Train to King's Cross: {train_time} min")
    print(f"⏱️  Total commute: {total} min")
    
    criteria = load_criteria()
    max_commute = criteria["commute"]["max_minutes"]
    
    if total <= max_commute:
        print(f"✅ Within {max_commute} min limit!")
    else:
        print(f"❌ Exceeds {max_commute} min limit by {total - max_commute} min")


def main():
    parser = argparse.ArgumentParser(description="Find commutable areas")
    parser.add_argument("--max-minutes", type=int, help="Max commute time")
    parser.add_argument("--refresh-stations", action="store_true", help="Refresh station data")
    parser.add_argument("--check", type=str, help="Check specific postcode")
    parser.add_argument("--output", type=str, default="config/areas.yaml", help="Output file")
    
    args = parser.parse_args()
    
    # Ensure directories exist
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.check:
        check_postcode(args.check)
        return
    
    if args.refresh_stations:
        print("🔄 Refreshing station database...")
        db = StationDatabase()
        db.refresh()
        print("✅ Station database refreshed")
        return
    
    # Load criteria for defaults
    criteria = load_criteria()
    max_minutes = args.max_minutes or criteria["commute"]["max_minutes"]
    walking_buffer = criteria["commute"].get("walking_buffer_minutes", 10)
    
    # Find commutable stations
    areas = find_commutable_stations(max_minutes, walking_buffer)
    
    # Save results
    save_areas(areas)
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"   Total areas: {len(areas)}")
    if areas:
        print(f"   Fastest commute: {areas[0]['name']} ({areas[0]['commute_minutes']} min)")
        print(f"   Slowest commute: {areas[-1]['name']} ({areas[-1]['commute_minutes']} min)")


if __name__ == "__main__":
    main()
