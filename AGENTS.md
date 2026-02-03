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
| `config/criteria.yaml` | Rental requirements (budget, beds, commute) |
| `config/areas.yaml` | Queue of areas to explore |
| `config/stations.json` | Cached station → KX commute times |
| `data/cache/` | Cached amenity and scoring data |
| `web/app.py` | Flask web UI |

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

## Development Tips

- Run `python -m pytest tests/` before committing
- Web UI runs on port 5000 by default
- Use `.env` for API keys, never commit them
