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
        ├── Cache hit (< 120s)  → instant response, "cached": true
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
    console.log(data.cached);        // true = served from 120s cache
    console.log(data.fetch_mode);    // "live"
    console.log(data.all_rates);
  });
```

| Endpoint | Description |
|----------|-------------|
| `GET /data/latest_rates.json` | Full rate payload |
| `GET /data/aud_npr_transfer_methods.json` | Transfer method matrix |
| `GET /health` | Health check |

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `send_amount` | 1000 | Send amount in source currency |
| `skip_browser` | `true` | `false` includes Western Union (~2 min response) |
| `fresh=true` | off | Bypass 120s cache, hit providers immediately |

### Railway deployment

**Start command:** `python main.py --serve` (set in `railway.toml` / `Procfile`).

| Wrong start command | Problem |
|---------------------|---------|
| `python main.py` | Scheduler loop — no HTTP server |
| `uvicorn main:app` without env | Works now (`app` re-exported), but prefer `python main.py --serve` |

**Env vars on Railway:**

```
LIVE_API_SKIP_BROWSER=true
LIVE_API_WARM_CACHE=true
LIVE_API_CACHE_SECONDS=120
EXCHANGERATE_API_KEY=your_key
LIVE_API_CORS_ORIGINS=https://paisapathau.com,https://www.paisapathau.com
```

Railway injects `PORT` — the app uses it automatically. Health check: `/health`.

**.env**

```
API_PORT=8000
LIVE_API_CACHE_SECONDS=120   # avoids Remitly 429 when many visitors load at once
LIVE_API_SKIP_BROWSER=true  # fast mode; set false for full WU per-method data
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

## Tier B status (all corridors → NPR)

| Provider | Priority | Corridors | Method | Status |
|----------|----------|-----------|--------|--------|
| Remitly | High | AUD, USD, GBP, CAD, NZD, EUR, AED | Calculator API | Live; new + existing user rates |
| Western Union | High | AUD, USD, GBP, CAD, NZD, SAR, AED | Playwright | AUD per-method; others widget N/A |
| WorldRemit | High | AUD, USD, GBP, CAD, NZD, EUR | GraphQL API | Live; new + existing when promo present |
| Xoom | Medium | USD, GBP, CAD, EUR | — | Sign-in required; records `error` |
| MoneyGram | Medium | AUD, USD, GBP, CAD | — | Bot protection; records `error` |
| Xe Money Transfer | Medium | AUD, USD, GBP, CAD, NZD | Playwright | Live via xe.com converter |
| Instarem | Medium | AUD, SGD, GBP | REST API | Live; applied FX rate |
| OFX | Medium | AUD, USD, GBP, CAD, NZD | — | No public quote API |
| OrbitRemit | Low | AUD, NZD, GBP | — | Cloudflare protected |
| TorFX | Low | AUD, GBP, NZD | — | Cloudflare protected |

**Tier C** (mid-market reference, no send fee): QAR, SAR, KWD, BHD, OMR, MYR, JPY, KRW, SGD, HKD, INR, ILS, CHF, NOK, SEK, DKK, THB, EUR → NPR via Wise / ExchangeRate-API / Open Exchange Rates fallback.

Output JSON includes a `coverage` block listing all configured corridors.

Test API scrapers: `python scripts/test_tier_b.py --api-only`

Test browser scrapers: `python scripts/test_tier_b.py --provider Xe`

Full browser run: `python main.py --once` (~15–30 min with all corridors)

| Tier | Source | Providers |
|------|--------|-------------|
| A | REST APIs | Wise, ExchangeRate-API, Open Exchange Rates (all active send currencies → NPR) |
| B | API + Playwright | All 10 remittance providers (see table above) |
| C | API fallback | 18 mid-market reference currencies → NPR |

Default send amount: **1000** in send currency (configurable via `SEND_AMOUNT` in `.env` or `--send-amount` flag).

### Corridor configuration

Corridors are defined in `constants.py`:

- `ACTIVE_SEND_CURRENCIES` — Tier A + Tier B send currencies
- `TIER_B_CORRIDORS` — per-provider corridor list
- `TIER_C_CURRENCIES` — mid-market-only currencies

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
