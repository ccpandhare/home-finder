# 🏠 Home Finder

Finding the perfect home for Chin & Reg near London.

## Overview

A two-phase home-finding service:
- **Phase 1 (Now → April 2026):** Explore areas within 1hr commute of King's Cross
- **Phase 2 (April → June 2026):** Hunt for actual rental properties in shortlisted areas

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Find commutable areas
python scripts/find_commutable_areas.py

# Run daily exploration
python scripts/daily_explore.py

# Start web UI
python web/app.py
```

## Search Criteria

| Requirement | Value |
|-------------|-------|
| Max commute | 60 min to King's Cross |
| Bedrooms | 2+ |
| Parking | Required |
| Budget | £1250-1750 pcm |
| Move date | June 2026 |

## Project Structure

```
home-finder/
├── config/           # Search criteria and area queue
├── core/             # Core logic (commute, scoring, etc.)
├── scrapers/         # Property site scrapers (Phase 2)
├── data/             # Cached and scraped data
├── web/              # Flask dashboard
├── scripts/          # CLI tools
└── tests/            # Test suite
```

## Web Dashboard

View exploration progress at `http://localhost:5000`

## Daily Updates

Telegram notifications are sent to the group when new areas are explored.

## API Keys Needed

- **TravelTime API** or **Google Maps** — commute calculations
- **Telegram Bot** (optional) — notifications

## License

Private project for Chin & Reg 🏡
