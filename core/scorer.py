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


def score_area(area: dict, amenities: dict, nature: dict, crime: dict = None) -> int:
    """
    Calculate overall score for an area (0-100).

    Based on weighted criteria from config.

    Args:
        area: Area info dict with commute_minutes, etc.
        amenities: Amenities data from gather_amenities()
        nature: Nature data from gather_nature_data()
        crime: Crime data from gather_crime_data() (optional)
    """
    criteria = load_criteria()
    weights = criteria.get("scoring", {})
    crime = crime or {}
    
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

    # Apply train change penalty if applicable
    # Ideal: direct mainline train to London (0 changes)
    # Tube/bus within London after mainline is expected and doesn't count
    mainline_changes = area.get("mainline_changes", 0)
    if mainline_changes > 0:
        train_change_config = criteria["commute"].get("train_change_penalty", {})
        penalty_per_change = train_change_config.get("penalty_per_change", 15)
        scores["commute"] = max(0, scores["commute"] - (mainline_changes * penalty_per_change))
    
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
    
    # General vibe score (5 points default)
    # Placeholder - will use AI analysis later
    scores["general_vibe"] = 70  # Placeholder

    # Safety score (15 points default)
    # Based on crime statistics from UK Police API
    safety_config = criteria.get("safety", {})
    excellent_threshold = safety_config.get("excellent_threshold", 50)
    good_threshold = safety_config.get("good_threshold", 100)
    acceptable_threshold = safety_config.get("acceptable_threshold", 200)

    if crime.get("api_success"):
        # Weight serious crimes more heavily (count them 2x)
        total_crimes = crime.get("total_crimes", 0)
        serious_crimes = crime.get("serious_crimes", 0)
        weighted_crimes = total_crimes + serious_crimes  # Serious counted twice

        if weighted_crimes <= excellent_threshold:
            scores["safety"] = 100
        elif weighted_crimes <= good_threshold:
            # Scale from 100 to 80
            scores["safety"] = 100 - ((weighted_crimes - excellent_threshold) /
                                       (good_threshold - excellent_threshold)) * 20
        elif weighted_crimes <= acceptable_threshold:
            # Scale from 80 to 50
            scores["safety"] = 80 - ((weighted_crimes - good_threshold) /
                                      (acceptable_threshold - good_threshold)) * 30
        else:
            # Scale from 50 down to 0 (cap at 2x acceptable)
            over_threshold = weighted_crimes - acceptable_threshold
            scores["safety"] = max(0, 50 - (over_threshold / acceptable_threshold) * 50)
    else:
        # No crime data available - neutral score
        scores["safety"] = 70  # Default when data unavailable

    # Calculate weighted total
    total = 0
    for key, weight in weights.items():
        if key in scores:
            total += (scores[key] / 100) * weight
    
    return round(total)
