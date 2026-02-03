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


def find_commutable_stations(max_minutes: int, walking_buffer: int = 10) -> list:
    """
    Find all stations within commute time of King's Cross.
    
    Args:
        max_minutes: Maximum total commute time
        walking_buffer: Minutes to allow for walking to station
    
    Returns:
        List of station dicts with commute times
    """
    print(f"🔍 Finding stations within {max_minutes} min of King's Cross...")
    print(f"   (including {walking_buffer} min walking buffer)")
    
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
            commutable.append({
                "name": station["town"] or station["name"].replace(" Station", ""),
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
