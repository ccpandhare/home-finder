# CLAUDE.md - Home Finder Project

## Overview
A home-finding service for Chin & Reg to discover rental properties within commuting distance of London King's Cross. Built in two phases:

**Phase 1 (Now → April 2026):** Area Discovery
- Identify stations/areas within 1hr commute to King's Cross
- Analyze neighborhoods for livability (nature, supermarkets, general vibe)
- Build a shortlist of favorable areas
- NOT focused on specific listings (they'll change)

**Phase 2 (April → June 2026):** Property Shortlisting  
- Switch focus to actual rental listings
- Scrape from Rightmove, Zoopla, OpenRent
- AI vibe-check on images
- Rank and notify on best matches

## Key Requirements

### Rental Criteria
- **Commute:** ≤60 min to King's Cross (train + walking buffer)
- **Bedrooms:** 2+
- **Parking:** Required
- **Budget:** £1250 (guide) → £1500 (good) → £1750 (great) pcm
- **Nature:** Parks nearby or countryside vibes
- **Move-in:** June 2026

### Technical Constraints
- **Token budget:** Claude tokens reset 8am GMT — limit AI analysis to ~1 area/day
- **Caching:** Aggressively cache commute times, amenity data, station info
- **Daily updates:** Send Telegram summary to group with Chin & Reg

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Web UI (Flask)                       │
│  - Station list with exploration status                  │
│  - Cached amenities per area                            │
│  - Progress dashboard                                    │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                    Core Pipeline                         │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌───────────┐  │
│  │ Commute │→ │ Amenity  │→ │ Scorer │→ │ Notifier  │  │
│  │ Finder  │  │ Enricher │  │        │  │ (Telegram)│  │
│  └─────────┘  └──────────┘  └────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                            │
│  - config/: criteria, areas queue, stations             │
│  - data/cache/: commute times, amenities                │
│  - data/raw/: scraped listings (Phase 2)                │
└─────────────────────────────────────────────────────────┘
```

## Code Principles

1. **Cache everything** — API calls are expensive, station data is stable
2. **Fail gracefully** — missing data shouldn't crash the pipeline
3. **Idempotent runs** — re-running should skip already-processed items
4. **Human-readable configs** — YAML for criteria, easy to tweak
5. **Progress visibility** — web UI shows what's done, what's pending

## Daily Run Behavior

The daily script should:
1. Pick next unexplored area from queue
2. Gather amenity data (parks, supermarkets, train frequency)
3. Score the area
4. Update web UI cache
5. Send Telegram summary with findings
6. Mark area as explored

## File Naming Conventions

- Scripts: `snake_case.py`
- Config files: `snake_case.yaml`
- Cache files: `{type}_{identifier}.json` (e.g., `commute_hitchin.json`)

## API Keys & Usage

### Google Maps (Primary - $300 free credit)
**Allowed APIs:**
- ✅ **Directions API** — commute times (train/transit to King's Cross)
- ✅ **Places API** — supermarkets, parks, amenities lookup
- ✅ **Geocoding API** — postcode ↔ coordinates

**NOT allowed (use free alternatives):**
- ❌ Maps JavaScript API — use Leaflet + OpenStreetMap for map rendering
- ❌ Distance Matrix API — use Directions API instead (more control)

**Cost management:**
- Cache ALL results aggressively (station times are stable)
- Limit to ~1 area exploration per day
- Batch API calls where possible

### Free Alternatives (prefer these when possible)
- **OpenStreetMap Overpass API** — parks, amenities, green spaces (FREE, unlimited)
- **postcodes.io** — UK postcode geocoding (FREE)
- **Leaflet + OSM tiles** — map rendering (FREE)
- **National Rail open data** — station locations (FREE)

### Telegram Bot
- For daily updates (configure in OpenClaw)
- Group notifications for Chin & Reg

## Commands

```bash
# Find commutable areas
python scripts/find_commutable_areas.py --max-minutes 60

# Run daily exploration
python scripts/daily_explore.py

# Check specific location
python scripts/check_area.py --postcode "AL1 1AA"

# Start web UI
python web/app.py
```

## Phase 2 Trigger

When `config/criteria.yaml` has `phase: 2`, the pipeline switches to:
- Scraping actual listings
- Image analysis for vibe
- Property-level notifications instead of area-level
