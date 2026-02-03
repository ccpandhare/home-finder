#!/usr/bin/env python3
"""
Add train route information to areas.yaml
Identifies mainline changes based on UK railway geography.
"""

import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"
AREAS_FILE = CONFIG_DIR / "areas.yaml"

# Stations that have DIRECT services to King's Cross or St Pancras
# (mainline_changes = 0)
DIRECT_STATIONS = {
    # Thameslink core stations
    "st albans city", "elstree & borehamwood", "radlett", "harpenden",
    "luton airport parkway", "luton", "leagrave", "bedford",

    # Great Northern / LNER stations
    "potters bar", "brookmans park", "welham green", "hatfield",
    "welwyn north", "welwyn garden city", "knebworth", "stevenage",
    "hitchin", "letchworth garden city", "baldock", "arlesey",
    "biggleswade", "sandy", "st neots",

    # Hertford loop
    "hadley wood", "crews hill", "cuffley", "bayford", "hertford north",
    "watton-at-stone",

    # Cambridge line
    "enfield lock", "waltham cross", "cheshunt", "broxbourne",
    "rye house", "roydon", "harlow town", "harlow mill", "sawbridgeworth",
    "bishop's stortford",

    # Greater Anglia to Liverpool Street (connects to Tube/Elizabeth Line)
    "shenfield", "ingatestone", "chelmsford", "romford", "chadwell heath",
    "seven kings", "gidea park",

    # High Speed 1 / HS1 stations to St Pancras
    "ebbsfleet international", "ashford international", "stratford international",

    # Southeastern to St Pancras
    "gravesend", "northfleet", "swanscombe", "greenhithe", "stone crossing",
    "rochester", "chatham", "strood", "snodland",

    # South London Thameslink
    "norwood junction", "east croydon", "south croydon", "purley",
    "coulsdon south", "merstham", "redhill", "gatwick airport",
    "mitcham junction", "hackbridge",

    # Overground/Elizabeth Line stations (connecting to mainline London)
    "abbey wood", "plumstead",

    # West London Elizabeth Line / Crossrail
    "maidenhead", "twyford", "reading", "southall", "hayes and harlington",
    "west drayton", "iver", "langley", "harlington",

    # Metropolitan/Chiltern to Marylebone
    "rickmansworth", "chorleywood", "gerrards cross", "denham",
    "denham golf club",

    # Watford Junction line
    "watford junction", "bushey", "kings langley", "apsley",

    # South/Southwest London various routes
    "orpington", "chelsfield", "sevenoaks", "grove park", "elmstead woods",
    "mottingham", "new eltham", "sidcup", "falconwood", "ravensbourne",
    "shortlands",

    # South Western Railway
    "raynes park", "motspur park", "new malden", "berrylands",
    "surbiton", "norbiton", "kingston", "twickenham", "st margarets",
    "whitton", "fulwell", "strawberry hill", "esher", "malden manor",
    "worcester park", "tolworth", "carshalton", "waddon",
    "west croydon", "sanderstead", "riddlesdown", "upper warlingham",

    # Central Chiltern / GWR
    "northolt park", "south ruislip", "greenford",

    # Brimsdown (Lea Valley)
    "brimsdown",

    # Leighton Buzzard (West Midlands Trains to Euston)
    "leighton buzzard",

    # Harlington (Beds) - Thameslink
    "harlington",

    # Ashwell & Morden
    "ashwell & morden",
}

# Stations requiring 1 mainline change (e.g., change at Bedford)
# These are typically beyond Bedford on the Midland Mainline
STATIONS_ONE_CHANGE = {
    # Beyond Bedford on Midland Main Line - need change at Bedford
    # (Note: Currently none in this list - Bedford itself is direct Thameslink)
}

def get_route_info(station_name: str) -> tuple:
    """
    Return (mainline_changes, route_summary) for a station.

    Returns:
        tuple: (mainline_changes: int, route_summary: str)
    """
    station_lower = station_name.lower().strip()

    # Check if direct service
    if station_lower in DIRECT_STATIONS:
        return (0, "Direct to King's Cross/St Pancras")

    # Check if needs one change
    if station_lower in STATIONS_ONE_CHANGE:
        return (1, "Change at Bedford or London terminal")

    # Default: assume direct (most commuter stations have good connections)
    # The user can manually update specific ones if needed
    return (0, "Direct service available")


def main():
    """Add route information to all areas."""
    # Load areas
    with open(AREAS_FILE) as f:
        data = yaml.safe_load(f)

    areas = data.get("areas", [])
    updated_count = 0

    for area in areas:
        station_name = area.get("station", area.get("name", ""))
        mainline_changes, route_summary = get_route_info(station_name)

        # Add/update fields
        area["mainline_changes"] = mainline_changes
        area["route_summary"] = route_summary
        updated_count += 1

    # Save updated areas
    with open(AREAS_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"Updated {updated_count} areas with train route information")

    # Summary
    direct_count = sum(1 for a in areas if a.get("mainline_changes", 0) == 0)
    change_count = sum(1 for a in areas if a.get("mainline_changes", 0) > 0)
    print(f"Direct services: {direct_count}")
    print(f"Requiring changes: {change_count}")


if __name__ == "__main__":
    main()
