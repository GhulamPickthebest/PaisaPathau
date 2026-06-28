# Deployment Notes

## Railway (production — recommended)

The live API runs on Railway with on-demand fetching and server-side caching.

**Start command:**

```bash
python main.py --serve
```

Configured in `railway.toml`, `Procfile`, and `nixpacks.toml`.

**Key env vars:**

```
LIVE_API_SKIP_BROWSER=false
LIVE_API_WARM_CACHE=true
LIVE_API_CACHE_SECONDS=120
EXCHANGERATE_API_KEY=your_key
PORT                         # set automatically by Railway
```

**Build:** `railway.toml` uses `builder = DOCKERFILE` so Playwright + Chromium are installed.

**Health check:** `/health`

**Do not run** `python main.py` (scheduler loop) on Railway — that is the old batch mode with no HTTP server.

### Cache behaviour

| Scenario | Response time | `cached` field |
|----------|---------------|----------------|
| Startup warm-up | ~1–3 min (background) | — |
| First visitor after cache expires | ~1–3 min (with browser scrapers) | `false` |
| Subsequent visitors within 120s | ~1s | `true` |
| `?fresh=true` | ~1–3 min (hits providers) | `false` |
| `?skip_browser=true` | ~6–25s (API scrapers only) | varies |

Set `LIVE_API_CACHE_SECONDS=120` (or higher) to avoid Remitly rate limits when many users load the site.

### Fast mode (optional)

Set `LIVE_API_SKIP_BROWSER=true` (or `?skip_browser=true`) to skip Playwright. Western Union still returns a headline rate via the Wise comparisons API; Ria, Taptap, Skrill, and Xe are skipped.

---

## Render / Fly.io (alternatives)

Same start command and env vars as Railway:

```bash
python main.py --serve
```

Bind to `0.0.0.0` and use the platform's `PORT` env var (handled automatically via `config.py`).

---

## Legacy batch mode (not used in production)

`python main.py --once` fetches all providers once and writes static files to `data/`. Previously run every 30 minutes via GitHub Actions.

The scheduled workflow is **disabled**. Manual trigger only: Actions → **Scraper Pipeline (manual)**.

Use batch mode only for local debugging or if you need static JSON snapshots in the repo.
