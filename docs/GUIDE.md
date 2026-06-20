# PaisaPathau Scraper — Quick Guide

Concise setup, API keys, and pipeline flow for the remittance rate scraper.

---

## How It Works

```
main.py --once
    │
    ▼
scheduler.run_fetch_cycle()
    │
    ├── Tier A (APIs)          → Wise, ExchangeRate-API, Open Exchange Rates (AUD only)
    ├── Tier B (API + Playwright) → Remitly, WorldRemit, Instarem (API); Western Union (browser)
    └── Tier C (Mid-market)    → Skipped (AUD-only scope; re-enable via constants.py)
    │
    ▼
storage.py  → SQLite history (data/rates_history.db)
output.py   → latest_rates.json, snapshot JSON, CSV
    │
    ▼
GitHub Actions (every 30 min) → commit data → deploy GitHub Pages
    │
    ▼
WordPress frontend fetches JSON
```

Each provider runs independently. Failures get `"status": "error"`; others continue. Transient errors retry 3 times.

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
| `python main.py --once` | Single full scrape (CI mode) |
| `python main.py --once --skip-browser` | APIs only (~25 sec, good for testing) |
| `python main.py --serve` | **Live API** — fetch providers on each request (~10 sec) |
| `python main.py` | Continuous loop every 30 min |
| `python main.py --interval 15` | Custom interval (minutes) |
| `pytest tests/ -v` | Run unit tests |
| `python scripts/test_tier_b.py --api-only` | Test Remitly + WorldRemit API scrapers |
| `python scripts/test_tier_b.py --provider Remitly` | Test one provider |

Logs: `logs/scraper.log`

---

## Live API (real-time rates for WordPress)

GitHub Pages serves **static** JSON (updated every 30 min). For rates that match provider websites **now**, run the live API on a small host (Railway, Render, Fly.io):

```bash
python main.py --serve
# → http://localhost:8000/data/latest_rates.json
```

| Endpoint | Same shape as |
|----------|----------------|
| `GET /data/latest_rates.json` | GitHub Pages JSON |
| `GET /data/aud_npr_transfer_methods.json` | Transfer method matrix |
| `GET /health` | Health check |

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `send_amount` | 1000 | AUD send amount |
| `skip_browser` | `true` | `false` includes Western Union (~2 min response) |
| `fresh=true` | off | Bypass 120s cache, hit providers immediately |

**WordPress:** point your backend fetch to the live API URL instead of GitHub Pages:

```javascript
fetch('https://YOUR-API.railway.app/data/latest_rates.json')
```

Keep GitHub Pages as a **fallback** if the API is down.

### Railway deployment

Run the **live API**, not the scheduler (`python main.py` without `--serve`).

**Start command:** `python main.py --serve` (set in `railway.toml` / `Procfile`).

| Wrong start command | Problem |
|---------------------|---------|
| `python main.py` | Scheduler loop, Playwright missing, no HTTP |
| Playwright without `playwright install` | WU browser scrape fails |

**Env vars on Railway:**

```
LIVE_API_SKIP_BROWSER=true
LIVE_API_WARM_CACHE=true
LIVE_API_CACHE_SECONDS=120
EXCHANGERATE_API_KEY=your_key
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

## Output Files

All written to `data/` after each run:

| File | Purpose |
|------|---------|
| `latest_rates.json` | Live rates for WordPress |
| `rates_YYYYMMDD_HHMM.json` | Timestamped snapshot (auto-deleted after 3 days) |
| `latest_rates.csv` | Flat export |
| `aud_npr_transfer_methods.json` | AUD→NPR per-method matrix (fees, new/existing rates, speeds) |
| `rates_history.db` | SQLite trend history |

---

## GitHub Deployment

1. Push repo to GitHub
2. **Settings → Secrets → Actions** — add:
   - `EXCHANGERATE_API_KEY`
   - `OPEN_EXCHANGE_RATES_APP_ID` (optional)
   - `ALERT_WEBHOOK_URL` (optional)
3. **Settings → Pages → Source: GitHub Actions**
4. Workflow runs every 30 min (`.github/workflows/scraper.yml`)

### JSON endpoint for WordPress

```
https://YOUR_USERNAME.github.io/REPO-NAME/data/latest_rates.json
```

```javascript
fetch('https://YOUR_USERNAME.github.io/REPO-NAME/data/latest_rates.json')
  .then(r => r.json())
  .then(data => console.log(data.corridors));
```

---

## Tier B status (AUD→NPR only)

| Provider | Method | Status |
|----------|--------|--------|
| Remitly | Calculator API | AUD; New + Existing user rates |
| WorldRemit | GraphQL API | AUD; New + Existing user rates |
| Instarem | REST API | AUD; New + Existing user rates/fees |
| Western Union | Playwright send-flow estimate | AUD; per-method Bank/Cash rates + promo existing rate on bank |
| Xoom, MoneyGram, Xe, OFX, OrbitRemit, TorFX | — | Not in active pipeline (add corridors in `constants.py` later) |

Test API scrapers: `python scripts/test_tier_b.py --api-only`

Test browser scrapers: `python scripts/test_tier_b.py --provider Xe`

Full browser run (WU AUD + Xe): `python main.py --once` (~5–10 min)

| Tier | Source | Providers |
|------|--------|-------------|
| A | REST APIs | Wise, ExchangeRate-API, Open Exchange Rates (AUD→NPR) |
| B | API + Playwright | Remitly, WorldRemit, Instarem (API); Western Union (browser) |
| C | API fallback | Disabled (set `TIER_C_CURRENCIES` in `constants.py` when expanding) |

Default send amount: **1000 AUD** (configurable via `SEND_AMOUNT` in `.env` or `--send-amount` flag).

### Expanding to more send currencies

Edit `ACTIVE_SEND_CURRENCIES` in `constants.py` and re-enable providers in `tier_b/__init__.py` as needed.

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
| Empty `latest_rates.json` | Run `python main.py --once --skip-browser` to verify Tier A first |

For persistent hosting alternatives (Railway, Render), see [SCHEDULER_ALTERNATIVES.md](SCHEDULER_ALTERNATIVES.md).
