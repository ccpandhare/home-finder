#!/usr/bin/env python3
"""
Daily Area Explorer
Picks the next unexplored area, gathers data, scores it, and sends notification.

Usage:
    python scripts/daily_explore.py
    python scripts/daily_explore.py --area "St Albans"  # Explore specific area
    python scripts/daily_explore.py --dry-run           # Don't save or notify
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.enrichers import gather_amenities, gather_nature_data
from core.scorer import score_area
from core.notifier import send_telegram_update

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
CACHE_DIR = BASE_DIR / "data" / "cache"


def load_areas() -> dict:
    """Load areas configuration."""
    with open(CONFIG_DIR / "areas.yaml") as f:
        return yaml.safe_load(f) or {"areas": []}


def save_areas(data: dict) -> None:
    """Save areas configuration."""
    with open(CONFIG_DIR / "areas.yaml", "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def save_area_cache(area_name: str, data: dict) -> None:
    """Save cached data for an area."""
    cache_file = CACHE_DIR / f"area_{area_name.lower().replace(' ', '_')}.json"
    with open(cache_file, "w") as f:
        json.dump(data, f, indent=2)


def get_next_area(areas_data: dict) -> dict | None:
    """Get next pending area to explore."""
    areas = areas_data.get("areas", [])
    
    # Check priority areas first
    for name in areas_data.get("priority_areas", []):
        area = next((a for a in areas if a["name"] == name and a["status"] == "pending"), None)
        if area:
            return area
    
    # Then first pending
    return next((a for a in areas if a["status"] == "pending"), None)


def explore_area(area: dict, dry_run: bool = False) -> dict:
    """
    Explore an area and gather all relevant data.
    
    Returns enriched area data with score.
    """
    print(f"\n🔍 Exploring: {area['name']}")
    print(f"   Station: {area['station']}")
    print(f"   Commute: {area['commute_minutes']} min to King's Cross")
    
    cache_data = {
        "explored_at": datetime.now().isoformat(),
        "station": area["station"],
        "commute_minutes": area["commute_minutes"],
    }
    
    # Gather amenities (supermarkets, pharmacies)
    print("   📍 Gathering amenities...")
    amenities = gather_amenities(area["lat"], area["lng"])
    cache_data["amenities"] = amenities
    print(f"      Found {len(amenities.get('supermarkets', []))} supermarkets")
    
    # Gather nature data (parks, green spaces)
    print("   🌳 Gathering nature data...")
    nature = gather_nature_data(area["lat"], area["lng"])
    cache_data["nature"] = nature
    print(f"      Found {nature.get('parks_count', 0)} parks")
    
    # Calculate score
    print("   📊 Calculating score...")
    score = score_area(area, amenities, nature)
    cache_data["score"] = score
    print(f"      Score: {score}/100")
    
    if not dry_run:
        # Save cache
        save_area_cache(area["name"], cache_data)
        print(f"   💾 Cached data saved")
    
    return {
        **area,
        "status": "explored",
        "explored_at": datetime.now().strftime("%Y-%m-%d"),
        "score": score,
    }


def format_telegram_message(area: dict, cache: dict) -> str:
    """Format the daily Telegram update message."""
    amenities = cache.get("amenities", {})
    nature = cache.get("nature", {})
    
    supermarkets = amenities.get("supermarkets", [])
    supermarket_names = ", ".join([s["name"] for s in supermarkets[:4]]) or "None found"
    
    parks = nature.get("parks", [])
    nature_score = min(10, len(parks) * 2) if parks else 0
    
    msg = f"""🏠 **Home Finder Daily Update**

📍 **Area Explored:** {area['name']}
🚂 **Commute to KX:** {area['commute_minutes']} min
🌳 **Nature Score:** {nature_score}/10 ({len(parks)} parks nearby)
🛒 **Supermarkets:** {supermarket_names}
⭐ **Overall Score:** {area['score']}/100

"""
    
    # Add a verdict
    if area['score'] >= 80:
        msg += "**Verdict:** 🌟 Excellent area! Worth prioritizing."
    elif area['score'] >= 60:
        msg += "**Verdict:** 👍 Good option. Solid choice."
    elif area['score'] >= 40:
        msg += "**Verdict:** 🤔 Decent, but has some drawbacks."
    else:
        msg += "**Verdict:** ⚠️ May not meet your criteria."
    
    return msg


def main():
    parser = argparse.ArgumentParser(description="Daily area explorer")
    parser.add_argument("--area", type=str, help="Explore specific area by name")
    parser.add_argument("--dry-run", action="store_true", help="Don't save or notify")
    parser.add_argument("--no-notify", action="store_true", help="Skip Telegram notification")
    
    args = parser.parse_args()
    
    # Ensure cache dir exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load areas
    areas_data = load_areas()
    
    if not areas_data.get("areas"):
        print("❌ No areas configured. Run find_commutable_areas.py first.")
        sys.exit(1)
    
    # Get area to explore
    if args.area:
        area = next(
            (a for a in areas_data["areas"] if a["name"].lower() == args.area.lower()),
            None
        )
        if not area:
            print(f"❌ Area '{args.area}' not found")
            sys.exit(1)
    else:
        area = get_next_area(areas_data)
        if not area:
            print("✅ All areas have been explored!")
            sys.exit(0)
    
    # Explore the area
    updated_area = explore_area(area, dry_run=args.dry_run)
    
    if not args.dry_run:
        # Update areas config
        for i, a in enumerate(areas_data["areas"]):
            if a["name"] == updated_area["name"]:
                areas_data["areas"][i] = updated_area
                break
        
        save_areas(areas_data)
        print(f"\n✅ Area status updated")
        
        # Send notification
        if not args.no_notify:
            cache = json.loads(
                (CACHE_DIR / f"area_{updated_area['name'].lower().replace(' ', '_')}.json").read_text()
            )
            message = format_telegram_message(updated_area, cache)
            
            print("\n📱 Sending Telegram update...")
            send_telegram_update(message)
            print("✅ Notification sent!")
    
    # Print stats
    explored = len([a for a in areas_data["areas"] if a["status"] == "explored"])
    total = len(areas_data["areas"])
    print(f"\n📊 Progress: {explored}/{total} areas explored")


if __name__ == "__main__":
    main()
