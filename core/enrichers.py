"""
Area enrichment - gather amenities, nature data, etc.
Uses OpenStreetMap Overpass API (free) or Google Places.

Features:
- Retry with exponential backoff for failed API calls
- Handles rate limiting (429), server errors (500, 502, 503)
- Returns empty data gracefully when APIs fail
- Logs all operations with timestamps
"""

import os
import time
import logging
from typing import Optional, Callable, Any

import httpx

# Set up logging
logger = logging.getLogger(__name__)

# Overpass API endpoints (with fallbacks)
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _retry_with_backoff(
    func: Callable[[], Any],
    max_retries: int = 3,
    initial_delay: float = 2.0,
    max_delay: float = 30.0,
    retry_on_status: tuple = (429, 500, 502, 503, 504),
) -> Any:
    """
    Retry a function with exponential backoff.

    Args:
        func: Callable function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (doubles each retry)
        max_delay: Maximum delay between retries
        retry_on_status: HTTP status codes that trigger a retry

    Returns:
        Result from func or raises last exception
    """
    delay = initial_delay
    last_error = None

    for attempt in range(max_retries):
        try:
            return func()
        except httpx.HTTPStatusError as e:
            last_error = e
            status_code = e.response.status_code
            if status_code in retry_on_status and attempt < max_retries - 1:
                # Rate limited or server error - wait longer
                if status_code == 429:
                    delay = min(delay * 2, max_delay)
                    logger.warning(f"Rate limited (429). Waiting {delay}s before retry...")
                else:
                    logger.warning(f"Server error ({status_code}). Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
            else:
                logger.error(f"HTTP error {status_code} after {attempt + 1} attempts")
                raise
        except httpx.TimeoutException as e:
            last_error = e
            if attempt < max_retries - 1:
                logger.warning(f"Timeout on attempt {attempt + 1}. Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
            else:
                logger.error(f"Timeout after {max_retries} attempts")
                raise
        except httpx.ConnectError as e:
            last_error = e
            if attempt < max_retries - 1:
                logger.warning(f"Connection error on attempt {attempt + 1}. Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
            else:
                logger.error(f"Connection failed after {max_retries} attempts: {e}")
                raise
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
            else:
                logger.error(f"All {max_retries} attempts failed. Last error: {e}")
                raise

    raise last_error


def _query_overpass(query: str, timeout: int = 45) -> dict:
    """
    Query Overpass API with automatic endpoint fallback.

    Tries multiple Overpass endpoints if one fails.
    """
    last_error = None

    for endpoint in OVERPASS_ENDPOINTS:
        try:
            logger.debug(f"Trying Overpass endpoint: {endpoint}")
            response = httpx.post(
                endpoint,
                data={"data": query},
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            last_error = e
            logger.warning(f"Endpoint {endpoint} failed: {e}")
            continue

    raise last_error or Exception("All Overpass endpoints failed")


def gather_amenities(lat: float, lng: float, radius_m: int = 1500) -> dict:
    """
    Gather amenity data for an area.

    Returns dict with supermarkets, pharmacies, etc.
    Handles API failures gracefully by returning empty lists.
    """
    amenities = {
        "supermarkets": [],
        "pharmacies": [],
        "restaurants": [],
        "api_success": False,
        "error": None,
    }

    logger.info(f"Gathering amenities for ({lat}, {lng}) within {radius_m}m radius")

    def _fetch_amenities():
        # More comprehensive query - includes ways and relations, and shop=convenience
        query = f"""
        [out:json][timeout:45];
        (
          node["shop"="supermarket"](around:{radius_m},{lat},{lng});
          way["shop"="supermarket"](around:{radius_m},{lat},{lng});
          node["shop"="convenience"](around:{radius_m},{lat},{lng});
          node["amenity"="pharmacy"](around:{radius_m},{lat},{lng});
          way["amenity"="pharmacy"](around:{radius_m},{lat},{lng});
        );
        out center body;
        """
        return _query_overpass(query, timeout=45)

    # Try Overpass API with retries
    try:
        data = _retry_with_backoff(_fetch_amenities, max_retries=3, initial_delay=2.0)
        seen_names = set()  # Deduplicate by name

        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name", tags.get("brand", "Unknown"))

            # Skip duplicates
            if name != "Unknown" and name in seen_names:
                continue
            if name != "Unknown":
                seen_names.add(name)

            # Get coordinates (center for ways, direct for nodes)
            center = element.get("center", {})
            elem_lat = center.get("lat", element.get("lat"))
            elem_lng = center.get("lon", element.get("lon"))

            if elem_lat is None or elem_lng is None:
                continue

            item = {
                "name": name,
                "lat": elem_lat,
                "lng": elem_lng,
                "distance_m": _calculate_distance_m(lat, lng, elem_lat, elem_lng),
            }

            shop_type = tags.get("shop")
            amenity_type = tags.get("amenity")

            if shop_type == "supermarket":
                amenities["supermarkets"].append(item)
            elif shop_type == "convenience":
                # Add convenience stores as secondary supermarkets
                item["type"] = "convenience"
                amenities["supermarkets"].append(item)
            elif amenity_type == "pharmacy":
                amenities["pharmacies"].append(item)

        # Sort by distance
        for key in ["supermarkets", "pharmacies", "restaurants"]:
            amenities[key] = sorted(amenities[key], key=lambda x: x["distance_m"])

        amenities["api_success"] = True
        logger.info(f"Found {len(amenities['supermarkets'])} supermarkets/convenience stores, {len(amenities['pharmacies'])} pharmacies")

        # Log warning if no supermarkets found (edge case)
        if not amenities["supermarkets"]:
            logger.warning(f"No supermarkets found within {radius_m}m - this may indicate sparse data for this area")

    except httpx.TimeoutException as e:
        error_msg = f"API timeout after retries: {e}"
        logger.error(error_msg)
        amenities["error"] = error_msg
        print(f"      ⚠️  {error_msg}")

    except httpx.HTTPStatusError as e:
        error_msg = f"API error (HTTP {e.response.status_code}): {e}"
        logger.error(error_msg)
        amenities["error"] = error_msg
        print(f"      ⚠️  {error_msg}")

    except Exception as e:
        error_msg = f"Failed to gather amenities: {e}"
        logger.error(error_msg, exc_info=True)
        amenities["error"] = error_msg
        print(f"      ⚠️  {error_msg}")

    return amenities


def gather_nature_data(lat: float, lng: float, radius_m: int = 2000) -> dict:
    """
    Gather nature/green space data for an area.

    Returns dict with parks, nature reserves, etc.
    Handles API failures gracefully by returning empty lists.
    """
    nature = {
        "parks": [],
        "parks_count": 0,
        "nature_reserves": [],
        "countryside_access": False,
        "api_success": False,
        "error": None,
    }

    logger.info(f"Gathering nature data for ({lat}, {lng}) within {radius_m}m radius")

    def _fetch_nature():
        # Comprehensive query for green spaces
        query = f"""
        [out:json][timeout:45];
        (
          way["leisure"="park"](around:{radius_m},{lat},{lng});
          relation["leisure"="park"](around:{radius_m},{lat},{lng});
          way["leisure"="nature_reserve"](around:{radius_m},{lat},{lng});
          relation["leisure"="nature_reserve"](around:{radius_m},{lat},{lng});
          way["landuse"="forest"](around:{radius_m},{lat},{lng});
          way["leisure"="garden"](around:{radius_m},{lat},{lng});
          way["natural"="wood"](around:{radius_m},{lat},{lng});
        );
        out center body;
        """
        return _query_overpass(query, timeout=45)

    try:
        data = _retry_with_backoff(_fetch_nature, max_retries=3, initial_delay=2.0)

        seen_names = set()

        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")

            # Skip unnamed or duplicate entries
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            # Get center coordinates
            center = element.get("center", {})
            elem_lat = center.get("lat", element.get("lat"))
            elem_lng = center.get("lon", element.get("lon"))

            if elem_lat is None or elem_lng is None:
                continue

            item = {
                "name": name,
                "lat": elem_lat,
                "lng": elem_lng,
                "distance_m": _calculate_distance_m(lat, lng, elem_lat, elem_lng),
                "type": tags.get("leisure") or tags.get("landuse") or tags.get("natural"),
            }

            leisure = tags.get("leisure")
            landuse = tags.get("landuse")
            natural = tags.get("natural")

            if leisure == "park" or leisure == "garden":
                nature["parks"].append(item)
            elif leisure == "nature_reserve" or landuse == "forest" or natural == "wood":
                nature["nature_reserves"].append(item)
                nature["countryside_access"] = True

        # Sort by distance and limit
        nature["parks"] = sorted(nature["parks"], key=lambda x: x["distance_m"])[:10]
        nature["nature_reserves"] = sorted(nature["nature_reserves"], key=lambda x: x["distance_m"])[:5]
        nature["parks_count"] = len(nature["parks"])
        nature["api_success"] = True

        logger.info(f"Found {len(nature['parks'])} parks, {len(nature['nature_reserves'])} nature reserves")

        # Log info if no parks found (edge case - still valid result)
        if not nature["parks"]:
            logger.info(f"No named parks found within {radius_m}m - area may have limited green spaces")

    except httpx.TimeoutException as e:
        error_msg = f"API timeout after retries: {e}"
        logger.error(error_msg)
        nature["error"] = error_msg
        print(f"      ⚠️  {error_msg}")

    except httpx.HTTPStatusError as e:
        error_msg = f"API error (HTTP {e.response.status_code}): {e}"
        logger.error(error_msg)
        nature["error"] = error_msg
        print(f"      ⚠️  {error_msg}")

    except Exception as e:
        error_msg = f"Failed to gather nature data: {e}"
        logger.error(error_msg, exc_info=True)
        nature["error"] = error_msg
        print(f"      ⚠️  {error_msg}")

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


# UK Police Data API
POLICE_API_BASE = "https://data.police.uk/api"


def gather_crime_data(lat: float, lng: float) -> dict:
    """
    Gather crime statistics for an area using the UK Police Data API.

    Returns dict with crime counts by category, total crimes, and crime rate.
    Uses the most recent available month of data.

    API: https://data.police.uk/docs/
    """
    crime_data = {
        "total_crimes": 0,
        "crimes_by_category": {},
        "crime_rate_per_1000": None,  # Would need population data for this
        "month": None,
        "serious_crimes": 0,  # Violent/weapons/robbery
        "property_crimes": 0,  # Burglary/theft/vehicle
        "antisocial_behaviour": 0,
        "api_success": False,
        "error": None,
    }

    logger.info(f"Gathering crime data for ({lat}, {lng})")

    # Serious crime categories (affect safety perception more)
    SERIOUS_CATEGORIES = {
        "violent-crime", "violence-and-sexual-offences",
        "robbery", "possession-of-weapons", "public-order"
    }

    # Property crime categories
    PROPERTY_CATEGORIES = {
        "burglary", "theft-from-the-person", "vehicle-crime",
        "bicycle-theft", "shoplifting", "other-theft"
    }

    def _fetch_crimes():
        # Get crimes for all categories at this location
        # The API returns data for a 1-mile radius by default
        response = httpx.get(
            f"{POLICE_API_BASE}/crimes-street/all-crime",
            params={"lat": lat, "lng": lng},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    try:
        crimes = _retry_with_backoff(_fetch_crimes, max_retries=3, initial_delay=2.0)

        # Count crimes by category
        category_counts = {}
        for crime in crimes:
            category = crime.get("category", "other-crime")
            category_counts[category] = category_counts.get(category, 0) + 1

            # Track the month (should be consistent across all crimes)
            if not crime_data["month"] and crime.get("month"):
                crime_data["month"] = crime["month"]

        crime_data["total_crimes"] = len(crimes)
        crime_data["crimes_by_category"] = category_counts

        # Calculate serious crimes count
        crime_data["serious_crimes"] = sum(
            count for cat, count in category_counts.items()
            if cat in SERIOUS_CATEGORIES
        )

        # Calculate property crimes count
        crime_data["property_crimes"] = sum(
            count for cat, count in category_counts.items()
            if cat in PROPERTY_CATEGORIES
        )

        # Anti-social behaviour (often a major concern)
        crime_data["antisocial_behaviour"] = category_counts.get("anti-social-behaviour", 0)

        crime_data["api_success"] = True

        logger.info(
            f"Found {crime_data['total_crimes']} crimes in {crime_data['month']}: "
            f"{crime_data['serious_crimes']} serious, "
            f"{crime_data['property_crimes']} property, "
            f"{crime_data['antisocial_behaviour']} antisocial"
        )

    except httpx.TimeoutException as e:
        error_msg = f"Police API timeout: {e}"
        logger.error(error_msg)
        crime_data["error"] = error_msg
        print(f"      ⚠️  {error_msg}")

    except httpx.HTTPStatusError as e:
        error_msg = f"Police API error (HTTP {e.response.status_code}): {e}"
        logger.error(error_msg)
        crime_data["error"] = error_msg
        print(f"      ⚠️  {error_msg}")

    except Exception as e:
        error_msg = f"Failed to gather crime data: {e}"
        logger.error(error_msg, exc_info=True)
        crime_data["error"] = error_msg
        print(f"      ⚠️  {error_msg}")

    return crime_data
