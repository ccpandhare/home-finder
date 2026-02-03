# AGENTS.md - AI Agent Context

## Project Context

This is **home-finder** — helping Chin & Reg find a rental home near London.

### The Humans
- **Chin** — tech-savvy, likes automation, will review code
- **Reg** — partner, joint decision-maker, will use web UI and Telegram updates

### Timeline
- **Now → April 2026:** Phase 1 — exploring areas, building shortlist of neighborhoods
- **April → June 2026:** Phase 2 — hunting actual properties in shortlisted areas
- **June 2026:** Move-in target

## When Working on This Project

### Do
- Keep token usage in mind — expensive AI calls should be batched/limited
- Cache aggressively — commute times and amenities don't change often
- **Prefer free APIs** — use OSM/Overpass for amenities, postcodes.io for geocoding
- **Use Google APIs sparingly** — only Directions, Places, Geocoding allowed
- Make the web UI simple and glanceable — Reg needs to check progress easily
- Test scrapers carefully — sites may block or change structure
- Log everything — debugging scraper issues needs good logs

### Don't
- Don't make API calls without caching results
- Don't process more than 1-2 areas per day (token budget)
- Don't ignore rate limits — we're guests on these sites
- Don't hardcode criteria — everything should come from config/criteria.yaml
- Don't use Google Maps for map rendering — use Leaflet + OSM (free)
- Don't use Distance Matrix API — use Directions API instead

## Key Files

| File | Purpose |
|------|---------|
| `config/criteria.yaml` | Rental requirements (budget, beds, commute, safety weights) |
| `config/areas.yaml` | Queue of areas to explore |
| `config/stations.json` | Cached station → KX commute times |
| `data/cache/` | Cached amenity, nature, and crime data |
| `web/app.py` | Flask web UI |
| `core/enrichers.py` | Data gathering (amenities, nature, crime) |
| `core/scorer.py` | Area scoring based on criteria weights |

## Crime Statistics

Crime data is gathered from the UK Police Data API (data.police.uk):
- **Free API** - no key required
- **Coverage** - ~1 mile radius around coordinates
- **Data** - Monthly crime counts by category
- **Scoring** - Serious crimes weighted 2x in safety score

Crime categories tracked:
- Serious: violence, weapons, robbery, public order
- Property: burglary, theft, vehicle crime
- Anti-social behaviour

Thresholds (configurable in criteria.yaml):
- Excellent: ≤50 crimes/month
- Good: ≤100 crimes/month
- Acceptable: ≤200 crimes/month

## Telegram Integration

Daily updates go to a Telegram group. Format should be:

```
🏠 Home Finder Daily Update

📍 Area Explored: St Albans
🚂 Commute to KX: 22 min train + 8 min walk
🌳 Nature Score: 8/10 (3 parks within 1km)
🛒 Supermarkets: Sainsbury's, Tesco Express, Aldi
💰 Avg Rent (2bed): £1,350 pcm
⭐ Overall Score: 82/100

Status: 12/47 areas explored
Next up: Hitchin
```

## Scraping Notes

- **Rightmove:** Use `rightmove-webscraper` pip package, max 1050 results per search
- **Zoopla:** Needs Playwright (JS-heavy site)
- **OpenRent:** Simple HTML, requests + BeautifulSoup should work
- All scrapers should respect rate limits and rotate user agents

## Map Integration

The dashboard includes an interactive Leaflet + OpenStreetMap map showing all commutable areas.

- **Leaflet JS/CSS** loaded from unpkg CDN (version 1.9.4)
- **Marker colors:** Green = explored, Blue = pending, Red = King's Cross
- **Marker size:** Larger markers for higher scores (20-32px based on score/100)
- **Data source:** Areas are rendered server-side via Jinja2 template from areas.yaml
- **King's Cross coords:** 51.5309, -0.1233 (destination marker)
- **Responsive:** Map height adapts to screen size (450px desktop, 350px tablet, 280px mobile)

When modifying the map:
- Keep Leaflet CSS before app styles (in `<head>`)
- Keep Leaflet JS before map init script (bottom of `<body>`)
- Popup content includes link to area detail page
- Markers auto-fit to show all areas on initial load

## Daily Exploration Script

The `scripts/daily_explore.py` handles automated area exploration via cron job.

### Features
- **Retry with backoff:** API calls retry 3 times with exponential backoff (2s, 4s, 8s)
- **Endpoint fallback:** Uses multiple Overpass API endpoints if one fails
- **Partial saves:** Cache is saved after each step (amenities, nature) so failures don't lose data
- **Comprehensive logging:** Logs to console (INFO) and file (DEBUG) in `data/logs/`

### Running Manually
```bash
# Explore next pending area
python scripts/daily_explore.py

# Explore specific area
python scripts/daily_explore.py --area "Cambridge"

# Test without saving (dry run)
python scripts/daily_explore.py --dry-run

# Skip Telegram notification
python scripts/daily_explore.py --no-notify
```

### Cron Job
Set up via OpenClaw to run daily at 9am GMT:
```bash
openclaw cron list  # View scheduled jobs
```

### Log Files
- `data/logs/daily_explore_YYYYMMDD.log` — Daily log files with detailed DEBUG info
- Cache files: `data/cache/area_<name>.json` — Contains amenities, nature, score

### Troubleshooting
- If Overpass API returns 504, check if overpass-api.de is under heavy load
- Script automatically falls back to `overpass.kumi.systems` as backup endpoint
- Check `exploration_status` in cache files: `in_progress`, `amenities_complete`, `nature_complete`, `complete`, or `failed`

## Development Tips

- Run `python -m pytest tests/` before committing
- Web UI runs on port 5000 by default
- Use `.env` for API keys, never commit them
