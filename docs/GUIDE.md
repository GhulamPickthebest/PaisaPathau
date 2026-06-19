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
    ├── Tier A (APIs)          → Wise, ExchangeRate-API, Open Exchange Rates
    ├── Tier B (API + Playwright) → Remitly, WorldRemit, Instarem (API); WU, Xe (browser)
    └── Tier C (Mid-market)    → 18 extra currencies via Wise fallback chain
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
| `python main.py` | Continuous loop every 30 min |
| `python main.py --interval 15` | Custom interval (minutes) |
| `pytest tests/ -v` | Run unit tests |
| `python scripts/test_tier_b.py --api-only` | Test Remitly + WorldRemit API scrapers |
| `python scripts/test_tier_b.py --provider Remitly` | Test one provider |

Logs: `logs/scraper.log`

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

## Tier B status

| Provider | Method | Status |
|----------|--------|--------|
| WorldRemit | GraphQL API | 5/6 corridors (CAD unavailable); New + Existing user rates |
| Instarem | REST API | AUD, GBP, SGD; New + Existing user rates/fees |
| Remitly | Calculator API | All 7 corridors; New + Existing user rates |
| Western Union | Playwright calculator | AUD only; New + Existing user rates |
| Xe | Playwright (`xe.com/currencyconverter`) | All corridors |
| Xoom | — | Skipped (sign-in required) |
| MoneyGram | — | Skipped (captcha / bot block) |
| OFX, OrbitRemit, TorFX | — | Skipped (no public API / Cloudflare) |

Test API scrapers: `python scripts/test_tier_b.py --api-only`

Test browser scrapers: `python scripts/test_tier_b.py --provider Xe`

Full browser run (WU AUD + Xe): `python main.py --once` (~5–10 min)

| Tier | Source | Providers |
|------|--------|-------------|
| A | REST APIs | Wise, ExchangeRate-API, Open Exchange Rates |
| B | API + Playwright | Remitly, WorldRemit, Instarem (API); Western Union, Xe (browser); Xoom, MoneyGram, OFX, OrbitRemit, TorFX (skipped) |
| C | API fallback | Mid-market rates for QAR, SAR, KWD, MYR, JPY, etc. |

Default send amount: **1000** (configurable via `SEND_AMOUNT` in `.env` or `--send-amount` flag).

### New vs existing user rates

Providers that offer different pricing return **two records** per corridor:

| Field | Example |
|-------|---------|
| `customer_type` | `new_user` or `existing_user` |
| `rate_label` | `"New User"` or `"Existing User"` |

Filter in WordPress by `rate_label` or `customer_type`. Providers without a split leave both fields empty.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Playwright not found | Run `playwright install chromium` |
| Tier B timeouts in CI | Normal on first run; providers may need selector updates if sites change |
| No ExchangeRate-API data | Add key to `.env` / GitHub secrets |
| Empty `latest_rates.json` | Run `python main.py --once --skip-browser` to verify Tier A first |

For persistent hosting alternatives (Railway, Render), see [SCHEDULER_ALTERNATIVES.md](SCHEDULER_ALTERNATIVES.md).
