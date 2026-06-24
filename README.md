# PaisaPathau Remittance Rate API

Production pipeline for **PaisaPathau.com** — fetches live remittance rates from 10+ providers across **all major send currencies → NPR** (AUD, USD, GBP, CAD, NZD, EUR, AED, SAR, SGD + Tier C mid-market).

**Production runs on [Railway](https://railway.app/)** as a live API with on-demand provider fetching and a 120-second server-side cache.

## Quick Guide

See **[docs/GUIDE.md](docs/GUIDE.md)** for setup, API keys, endpoints, and provider coverage.

## Architecture

```
WordPress / frontend
        │
        ▼
Railway  →  python main.py --serve
        │       ├── GET /data/latest_rates.json
        │       ├── GET /data/aud_npr_transfer_methods.json
        │       └── GET /health
        │
        ▼
On request (or cache hit):
  Tier A (Wise, ExchangeRate-API, OXR)
  Tier B (Remitly, WorldRemit, Instarem, …)
  Tier C (mid-market: QAR, KWD, JPY, EUR, …)
```

- **First request** (cold): ~6–25 seconds — hits provider APIs live
- **Cached requests** (within 120s): ~1 second — same payload, `"cached": true`
- **Cache warm-up** on startup when `LIVE_API_WARM_CACHE=true`

## Features

- **Live API** — real-time rates on each request (with smart caching)
- **Tier A** — Wise, ExchangeRate-API, Open Exchange Rates
- **Tier B** — Remitly, WorldRemit, Instarem, Western Union, Xe, and more
- **Tier C** — Mid-market NPR rates for Gulf, Asia, and Europe reference currencies
- CORS support for WordPress frontend
- Graceful per-provider error handling

## Railway (production)

Start command (already in `railway.toml` / `Procfile`):

```bash
python main.py --serve
```

**Required env vars:**

```
LIVE_API_SKIP_BROWSER=true
LIVE_API_WARM_CACHE=true
LIVE_API_CACHE_SECONDS=120
EXCHANGERATE_API_KEY=your_key
LIVE_API_CORS_ORIGINS=https://paisapathau.com,https://www.paisapathau.com
```

Health check path: `/health`

### API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /data/latest_rates.json` | Full rate payload (all providers + corridors) |
| `GET /data/aud_npr_transfer_methods.json` | AUD→NPR transfer method matrix |
| `GET /health` | Health check |

**Query params:** `send_amount`, `fresh=true` (bypass cache), `skip_browser`

### WordPress integration

```javascript
fetch('https://YOUR-APP.up.railway.app/data/latest_rates.json')
  .then(res => res.json())
  .then(data => {
    console.log(data.last_updated);
    console.log(data.cached);       // true if served from cache
    console.log(data.fetch_mode);   // "live"
    console.log(data.all_rates);
  });
```

## Local development

```bash
git clone <repo-url> && cd scrapper
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add EXCHANGERATE_API_KEY

# Start live API locally
python main.py --serve --port 8000
# → http://localhost:8000/data/latest_rates.json
```

| Command | Use case |
|---------|----------|
| `python main.py --serve` | **Live API** (same as Railway) |
| `python main.py --once --skip-browser` | One-off fetch to `data/` (dev/debug) |
| `pytest tests/ -v` | Run unit tests |

Playwright is only needed if `LIVE_API_SKIP_BROWSER=false` (Western Union browser scrape).

## Legacy batch mode (optional)

`python main.py --once` still writes static JSON/CSV/SQLite to `data/` for local debugging. The scheduled GitHub Actions scraper is **disabled** — use Railway for production. Manual workflow: Actions → **Scraper Pipeline (manual)** → Run workflow.

## Project Structure

```
├── main.py                 # CLI (--serve, --once)
├── live_api.py             # FastAPI app (Railway entrypoint)
├── scheduler.py            # Fetch orchestration + cache backing
├── constants.py            # Currency/corridor definitions
├── tier_a/                 # Reference rate APIs
├── tier_b/                 # Remittance provider scrapers
├── tier_c/                 # Mid-market rate fetcher
├── railway.toml            # Railway deploy config
└── tests/
```

## Infrastructure

| Service | Role | Cost |
|---------|------|------|
| **Railway** | Production live API | Free tier / ~$5+/mo |
| ExchangeRate-API | Tier A + Tier C fallback | Free tier |
| GitHub Actions | Optional manual batch only | Free |

## Testing

```bash
pytest tests/ -v
```

## License

MIT
