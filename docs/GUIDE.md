# PaisaPathau Rates API — Quick Guide

Concise setup, API keys, and pipeline flow for the live rates API (Railway production).

---

## How It Works (production)

```
WordPress / frontend
        │
        ▼
Railway  →  python main.py --serve  (live_api.py)
        │
        ▼
GET /data/latest_rates.json
        │
        ├── Cache hit (< 60s)  → instant response, "cached": true
        └── Cache miss          → scheduler.fetch_live_payload()
                │
                ├── Tier A (APIs)     → Wise, ExchangeRate-API, Open Exchange Rates
                ├── Tier B (API)      → Remitly, WorldRemit, Instarem, …
                └── Tier C (API)      → QAR, KWD, JPY, EUR, … mid-market
                │
                ▼
        JSON response (~6–25s first fetch, ~1s cached)
```

Each provider runs independently. Failures get `"status": "error"`; others continue. Transient errors retry 3 times.

**No scheduled batch scraper** — rates are fetched on demand and cached on the server. GitHub Actions batch workflow is manual-only (legacy).

---

## Local Setup

```bash
git clone <repo-url> && cd scrapper
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

Edit `.env` with your keys (see below).

---

## How to Run

| Command | Use case |
|---------|----------|
| `python main.py --serve` | **Production mode** — live API with caching (same as Railway) |
| `python main.py --serve --port 8000` | Local dev server |
| `python main.py --once --skip-browser` | One-off fetch to `data/` (debug only) |
| `pytest tests/ -v` | Run unit tests |
| `python scripts/test_tier_b.py --api-only` | Test Remitly + WorldRemit API scrapers |

Logs: `logs/scraper.log`

---

## Live API (Railway production)

**WordPress should fetch from Railway**, not static JSON files:

```javascript
fetch('https://YOUR-APP.up.railway.app/data/latest_rates.json')
  .then(r => r.json())
  .then(data => {
    console.log(data.cached);        // true = served from 60s cache
    console.log(data.fetch_mode);    // "live"
    console.log(data.all_rates);
  });
```

| Endpoint | Description |
|----------|-------------|
| `GET /` | Table view (Provider, Rate, Payment Method, Fee, Notes) |
| `GET /data/rates_table.json` | Flat table rows as JSON |
| `GET /data/latest_rates.json` | Full rate payload |
| `GET /data/aud_npr_transfer_methods.json` | Transfer method matrix |
| `GET /health` | Health check |

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `send_amount` | 1000 | Send amount in source currency |
| `skip_browser` | `false` on Railway | `true` skips Playwright (faster; WU still works via Wise comparisons API) |
| `fresh=true` | off | Bypass 60s cache, hit providers immediately |

### Railway deployment

**Start command:** `python main.py --serve` (set in `railway.toml` / `Procfile`).

| Wrong start command | Problem |
|---------------------|---------|
| `python main.py` | Scheduler loop — no HTTP server |
| `uvicorn main:app` without env | Works now (`app` re-exported), but prefer `python main.py --serve` |

**Env vars on Railway:**

```
LIVE_API_SKIP_BROWSER=false
LIVE_API_WARM_CACHE=true
LIVE_API_CACHE_SECONDS=60
EXCHANGERATE_API_KEY=your_key
LIVE_API_CORS_ORIGINS=https://paisapathau.com,https://www.paisapathau.com
```

Use the **Dockerfile** build (`railway.toml` → `builder = DOCKERFILE`) for Playwright. First uncached fetch with all browser scrapers may take ~1–3 minutes; `/health` returns immediately while cache warms in the background.

Railway injects `PORT` — the app uses it automatically. Health check: `/health`.

**.env**

```
API_PORT=8000
LIVE_API_CACHE_SECONDS=60   # avoids Remitly 429 when many visitors load at once
LIVE_API_SKIP_BROWSER=false  # Railway Dockerfile default; true = fast mode without Playwright
LIVE_API_CORS_ORIGINS=https://paisapathau.com,https://www.paisapathau.com
```

Response includes `"fetch_mode": "live"` and `"cached": true/false`.

---

## API Keys

### Wise — no key needed
Public endpoint used automatically:
`https://wise.com/rates/live?source=AUD&target=NPR`

### ExchangeRate-API (recommended)
1. Sign up at [exchangerate-api.com](https://www.exchangerate-api.com/)
2. Free tier: 1,500 requests/month
3. Copy your API key → set in `.env`:
   ```
   EXCHANGERATE_API_KEY=your_key_here
   ```

### Open Exchange Rates (optional backup)
1. Sign up at [openexchangerates.org](https://openexchangerates.org/)
2. Free tier: 1,000 requests/month
3. Copy App ID → set in `.env`:
   ```
   OPEN_EXCHANGE_RATES_APP_ID=your_app_id_here
   ```

### Alert webhook (optional)
Set `ALERT_WEBHOOK_URL` to a Slack incoming webhook. Alerts fire when >50% of fetches fail in a cycle.

---

## Output (live API response)

The API returns the same JSON shape previously written to `data/latest_rates.json`:

| Field | Description |
|-------|-------------|
| `last_updated` | ISO timestamp of fetch |
| `cached` | `true` if served from server cache |
| `fetch_mode` | `"live"` |
| `all_rates` | All provider/corridor records |
| `aud_npr_transfer_methods` | Transfer method matrix |
| `coverage` | Configured corridors per provider |

### Legacy static files (optional)

`python main.py --once` still writes to `data/` for local debugging. Production does **not** use these files.

---

## Tier B status (AUD→NPR only)

| Provider | Status |
|----------|--------|
| **Wise** | Live — public transfer quote API |
| **Remitly** | Live — calculator API; new + existing user rates |
| **WorldRemit** | Live — GraphQL API |
| **Instarem** | Live — applied FX (`instarem_fx_rate`) |
| **Instarem (by Nium)** | Live — same Nium API as Instarem |
| **Western Union** | Live — Wise comparisons API (headline rate); per-method + new/existing rates with browser |
| **Xe Money Transfer** | Live with browser; skipped on Railway default |
| **Xoom (PayPal)** | Live — Wise comparisons API (aggregated quote) |
| **Ria Money Transfer** | Live — Playwright + `MoneyTransferCalculator/Calculate` |
| **Taptap Send** | Live — Playwright `api.taptapsend.com/api/fxRates` |
| **Skrill** | Live — Playwright calculator (AU→Nepal country select) |
| **MoneyGram** | Unavailable — fee-quote API returns 401/captcha (partner API only) |
| **Revolut** | Unavailable — no AUD→NPR on public web/API |
| **ACE Money Transfer** | Unavailable — calculator needs login; no guest rate |
| **LuLu Exchange** | Unavailable — rates only in LuLu Money app |

Unavailable providers still appear in API output with `"status": "error"` so the frontend can show them.

More send currencies can be added later via `ACTIVE_SEND_CURRENCIES` in `constants.py`.

### New vs existing user rates

Providers that offer different pricing return **two records** per corridor:

| Field | Example |
|-------|---------|
| `customer_type` | `new_user` or `existing_user` |
| `rate_label` | `"New User"` or `"Existing User"` |

Filter in WordPress by `rate_label` or `customer_type`. Providers without a split leave both fields empty.

### AUD→NPR transfer method matrix — provider coverage

| Provider | Bank | Cash | Mobile / Wallet | New vs existing rates | Why others are limited |
|----------|------|------|-----------------|----------------------|-------------------------|
| Remitly | Yes | Yes | Yes (Direct to phone) | Yes (dual API: `strict_promo`) | Fully covered via public calculator API |
| WorldRemit | Yes | Yes | Yes (MOB / Khalti wallet alias) | Yes (`crossedOutValue` when present) | Fully covered via GraphQL |
| Instarem | Yes | — | — | Same FX, different fees | Public API only exposes bank transfer for NPR |
| Wise | Yes | — | — | No split on public endpoint | Comparison API returns bank quote only |
| Western Union | Yes | Yes | Not offered online for NPR | Bank: promo ratio from landing page; Cash: same FX, higher fee | Per-method needs Playwright send-flow (no public REST API); mobile not in payout list |
| MoneyGram | — | — | — | — | Calculator API returns 403 / captcha |
| Xoom | — | — | — | — | Requires sign-in; no guest quote |
| Xe | — | — | — | — | Currency converter only, not send-money quotes |
| OFX, OrbitRemit, TorFX | — | — | — | — | Cloudflare / no public quote API |

Min/max send limits are mostly **not** exposed on public endpoints (Instarem min is the exception).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Playwright not found | Run `playwright install chromium` |
| Tier B timeouts in CI | Normal on first run; providers may need selector updates if sites change |
| No ExchangeRate-API data | Add key to `.env` / GitHub secrets |
| API returns 502 / timeout | First request can take 60s; use `fresh=false` and rely on cache |
| Remitly 429 | Increase `LIVE_API_CACHE_SECONDS`; avoid `fresh=true` on every page load |
| Railway `app not found` | Start command must be `python main.py --serve` |
