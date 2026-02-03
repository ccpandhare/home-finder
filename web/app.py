"""
Home Finder Web UI
Simple Flask app to track area exploration progress
"""

import json
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, jsonify
import yaml

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-key-change-me")

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
CACHE_DIR = BASE_DIR / "data" / "cache"


def load_yaml(path: Path) -> dict:
    """Load YAML file safely."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path) -> dict:
    """Load JSON file safely."""
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def get_areas() -> list:
    """Get all areas with their status."""
    areas_config = load_yaml(CONFIG_DIR / "areas.yaml")
    return areas_config.get("areas", [])


def get_area_cache(area_name: str) -> dict:
    """Get cached data for an area."""
    cache_file = CACHE_DIR / f"area_{area_name.lower().replace(' ', '_')}.json"
    return load_json(cache_file)


def get_criteria() -> dict:
    """Get current search criteria."""
    return load_yaml(CONFIG_DIR / "criteria.yaml")


def get_stats() -> dict:
    """Get exploration statistics."""
    areas = get_areas()
    return {
        "total": len(areas),
        "explored": len([a for a in areas if a.get("status") == "explored"]),
        "pending": len([a for a in areas if a.get("status") == "pending"]),
        "skipped": len([a for a in areas if a.get("status") == "skipped"]),
    }


@app.route("/")
def index():
    """Main dashboard."""
    criteria = get_criteria()
    areas = get_areas()
    stats = get_stats()
    
    # Sort: explored first (by score desc), then pending
    explored = sorted(
        [a for a in areas if a.get("status") == "explored"],
        key=lambda x: x.get("score", 0),
        reverse=True
    )
    pending = [a for a in areas if a.get("status") == "pending"]
    
    return render_template(
        "index.html",
        criteria=criteria,
        explored=explored,
        pending=pending,
        stats=stats,
        phase=criteria.get("phase", 1),
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
    )


@app.route("/area/<name>")
def area_detail(name: str):
    """Detailed view of a single area."""
    areas = get_areas()
    area = next((a for a in areas if a.get("name", "").lower() == name.lower()), None)
    
    if not area:
        return "Area not found", 404
    
    cache = get_area_cache(name)
    
    return render_template(
        "area.html",
        area=area,
        cache=cache,
        amenities=cache.get("amenities", {}),
        nature=cache.get("nature", {}),
        sample_listings=cache.get("sample_listings", [])
    )


@app.route("/api/stats")
def api_stats():
    """API endpoint for stats."""
    return jsonify(get_stats())


@app.route("/api/areas")
def api_areas():
    """API endpoint for all areas."""
    return jsonify(get_areas())


@app.route("/api/area/<name>")
def api_area(name: str):
    """API endpoint for single area."""
    areas = get_areas()
    area = next((a for a in areas if a.get("name", "").lower() == name.lower()), None)
    if not area:
        return jsonify({"error": "not found"}), 404
    
    cache = get_area_cache(name)
    return jsonify({**area, "cache": cache})


if __name__ == "__main__":
    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    app.run(debug=True, host="0.0.0.0", port=5000)
