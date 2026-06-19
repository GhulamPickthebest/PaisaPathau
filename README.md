# PaisaPathau Remittance Rate Scraper

Production-grade Python pipeline that collects live exchange rates and transfer fees from remittance providers for **PaisaPathau.com** — a Nepal (NPR) remittance comparison site.

## Quick Guide

See **[docs/GUIDE.md](docs/GUIDE.md)** for setup, API keys, run commands, and pipeline flow.

## Features

- **Tier A** — Official APIs: Wise, ExchangeRate-API, Open Exchange Rates
- **Tier B** — Playwright browser scrapers: Remitly, Western Union, WorldRemit, Xoom, MoneyGram, Xe, Instarem, OFX, OrbitRemit, TorFX
- **Tier C** — Mid-market reference rates for 18 additional currencies
- Runs every **30 minutes** via GitHub Actions (or continuously on Railway/Render)
- Outputs JSON, CSV, and SQLite history for trend analysis
- Serves JSON via **GitHub Pages** for WordPress frontend consumption
- Graceful error handling with retries and optional Slack/webhook alerts

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/paisapathau-scraper.git
cd paisapathau-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

| Variable | Required | Description |
|----------|----------|-------------|
| `EXCHANGERATE_API_KEY` | Recommended | Free key from [exchangerate-api.com](https://www.exchangerate-api.com/) |
| `OPEN_EXCHANGE_RATES_APP_ID` | Optional | Backup from [openexchangerates.org](https://openexchangerates.org/) |
| `ALERT_WEBHOOK_URL` | Optional | Slack or generic webhook for failure alerts |
| `SEND_AMOUNT` | No | Default send amount (default: `1000`) |

### 3. Run locally

```bash
# Single fetch cycle
python main.py --once

# Continuous scheduler (every 30 min)
python main.py

# API-only mode (skip browser scrapers)
python main.py --once --skip-browser
```

## Output Files

After each cycle, files are written to `data/`:

| File | Description |
|------|-------------|
| `latest_rates.json` | Current rates (overwritten each run) |
| `rates_YYYYMMDD_HHMM.json` | Timestamped snapshot |
| `latest_rates.csv` | Flat CSV for WordPress / Google Sheets |
| `rates_history.db` | SQLite historical data |

Snapshots older than **3 days** are deleted automatically after each run. `latest_rates.json` is always kept.

### AUD → NPR transfer method matrix

`data/aud_npr_transfer_methods.json` includes per-provider rows for:

- Bank Transfer, Cash Pickup, Mobile Money Transfer, Wallet Transfer
- Fee, new/existing user rates, min/max amount (when API exposes them), transfer speeds

Also embedded in `latest_rates.json` under `aud_npr_transfer_methods`.

### JSON API Endpoint

Configure GitHub Pages to serve the `/data` folder. Your WordPress frontend fetches:

```
https://YOUR_USERNAME.github.io/REPO-NAME/data/latest_rates.json
```

Example WordPress integration:

```javascript
fetch('https://YOUR_USERNAME.github.io/REPO-NAME/data/latest_rates.json')
  .then(res => res.json())
  .then(data => {
    console.log(data.last_updated);
    console.log(data.corridors);
  });
```

## GitHub Actions Deploymentlatest_rates

### Setup

1. Push this repo to GitHub
2. Add repository secrets:
   - `EXCHANGERATE_API_KEY`
   - `OPEN_EXCHANGE_RATES_APP_ID` (optional)
   - `ALERT_WEBHOOK_URL` (optional)
3. Enable GitHub Pages: **Settings → Pages → Source: GitHub Actions**
4. The workflow (`.github/workflows/scraper.yml`) runs every 30 minutes, commits updated data, and deploys to Pages

### Manual trigger

Actions → **Scraper Pipeline** → **Run workflow**

## Project Structure

```
├── main.py                 # CLI entry point (--once, --interval)
├── scheduler.py            # Orchestrates Tier A/B/C fetch cycles
├── storage.py              # SQLite persistence
├── output.py               # JSON/CSV generation
├── alerting.py             # Optional webhook alerts
├── config.py               # Environment configuration
├── constants.py            # Currency/corridor definitions
├── models.py               # RateRecord data model
├── utils.py                # Logging, retries, parsing
├── tier_a/                 # API scrapers (Wise, ExchangeRate-API, OXR)
├── tier_b/                 # Playwright scrapers (10 providers)
├── tier_c/                 # Mid-market rate fetcher
├── data/                   # Output directory (GitHub Pages root)
├── tests/                  # Unit tests
└── .github/workflows/      # CI/CD scheduler
```

## Rate Record Schema

Each rate includes:

```json
{
  "provider": "Remitly",
  "customer_type": "new_user",
  "rate_label": "New User",
  "from_currency": "AUD",
  "from_country": "Australia",
  "from_flag": "🇦🇺",
  "to_currency": "NPR",
  "send_amount": 1000,
  "exchange_rate": 87.92,
  "fee": 6.50,
  "net_send_amount": 993.50,
  "receive_amount": 87420.44,
  "transfer_speed": "Minutes to 3 business days",
  "delivery_method": "Bank deposit / Cash pickup",
  "timestamp": "2026-06-11T12:00:00+00:00",
  "source": "scraper",
  "status": "ok"
}
```

## Testing

```bash
pytest tests/ -v
```

## Alternative Schedulers

See [docs/SCHEDULER_ALTERNATIVES.md](docs/SCHEDULER_ALTERNATIVES.md) for Railway.app and Render.com deployment options when you need a persistent process instead of GitHub Actions.

## Infrastructure Cost

| Service | Cost |
|---------|------|
| GitHub Actions | Free (2,000 min/month) |
| GitHub Pages | Free |
| ExchangeRate-API | Free tier (1,500 req/month) |
| Open Exchange Rates | Free tier (1,000 req/month) |
| Railway / Render | Free tier available |

**Estimated total: $0–$20/month**

## Error Handling

- Each provider fetch is isolated — one failure does not stop others
- 3 retry attempts for transient errors
- Failed records get `"status": "error"` in output
- Optional webhook alert when >50% of fetches fail
- All errors logged to `logs/scraper.log`

## License

MIT
