"""
Area scoring based on criteria weights.
"""

from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent.parent / "config"


def load_criteria() -> dict:
    """Load scoring criteria."""
    with open(CONFIG_DIR / "criteria.yaml") as f:
        return yaml.safe_load(f)


def score_area(area: dict, amenities: dict, nature: dict) -> int:
    """
    Calculate overall score for an area (0-100).
    
    Based on weighted criteria from config.
    """
    criteria = load_criteria()
    weights = criteria.get("scoring", {})
    
    scores = {}
    
    # Commute score (35 points default)
    # Perfect score if commute <= 30 min, decreasing to 0 at max_minutes
    max_minutes = criteria["commute"]["max_minutes"]
    commute = area.get("commute_minutes", max_minutes)
    
    if commute <= 30:
        scores["commute"] = 100
    elif commute >= max_minutes:
        scores["commute"] = 0
    else:
        # Linear scale from 30 to max
        scores["commute"] = 100 - ((commute - 30) / (max_minutes - 30)) * 100
    
    # Nature score (20 points default)
    # Based on number of parks and countryside access
    parks_count = nature.get("parks_count", 0)
    has_countryside = nature.get("countryside_access", False)
    
    nature_score = min(100, parks_count * 15)  # Each park worth 15 points, max 100
    if has_countryside:
        nature_score = min(100, nature_score + 30)  # Bonus for countryside
    scores["nature"] = nature_score
    
    # Amenities score (10 points default)
    # Based on supermarket access
    supermarkets = len(amenities.get("supermarkets", []))
    
    if supermarkets >= 3:
        scores["amenities"] = 100
    elif supermarkets >= 1:
        scores["amenities"] = 60 + (supermarkets - 1) * 20
    else:
        scores["amenities"] = 20  # Minimum for being a real place
    
    # Price score (25 points default)
    # This will be calculated in Phase 2 with actual listings
    # For now, assume average based on area type
    scores["price"] = 70  # Placeholder
    
    # General vibe score (10 points default)
    # Placeholder - will use AI analysis later
    scores["general_vibe"] = 70  # Placeholder
    
    # Calculate weighted total
    total = 0
    for key, weight in weights.items():
        if key in scores:
            total += (scores[key] / 100) * weight
    
    return round(total)
