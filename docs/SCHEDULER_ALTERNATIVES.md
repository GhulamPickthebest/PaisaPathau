# Alternative Scheduler Options

GitHub Actions is the default scheduler (every 30 minutes, zero cost). For a **persistent 24/7 process** or faster recovery from cold starts, use one of these free-tier alternatives.

## Railway.app

[Railway](https://railway.app/) offers a free tier suitable for long-running workers.

### Setup

1. Create a new project on Railway and connect your GitHub repo
2. Add environment variables from `.env.example`
3. Set the start command:

```bash
python main.py --interval 30
```

4. Railway `Procfile` (optional):

```
worker: python main.py --interval 30
```

### Notes

- Railway free tier includes limited monthly hours; monitor usage in the dashboard
- Playwright requires a build step — add to `railway.toml` or Dockerfile:

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y wget gnupg && \
    pip install -r requirements.txt && \
    playwright install --with-deps chromium
COPY . .
CMD ["python", "main.py", "--interval", "30"]
```

- Push `data/` to your repo separately (e.g. via a second GitHub Action on a schedule) if you still want GitHub Pages hosting

---

## Render.com

[Render](https://render.com/) free **Background Worker** tier runs continuously with spin-down after inactivity.

### Setup

1. Create a **Background Worker** service
2. Connect your GitHub repository
3. Build command:

```bash
pip install -r requirements.txt && playwright install chromium && playwright install-deps
```

4. Start command:

```bash
python main.py --interval 30
```

5. Add environment variables in the Render dashboard

### Notes

- Free workers spin down after 15 minutes of inactivity; use `--once` with an external cron (e.g. Render Cron Job or cron-job.org) as an alternative:

```bash
python main.py --once
```

- For Cron Jobs on Render, schedule every 30 minutes and use `--once`

---

## Comparison

| Feature | GitHub Actions | Railway | Render |
|---------|---------------|---------|--------|
| Cost | Free | Free tier | Free tier |
| 24/7 persistent | No (cron) | Yes | Yes (with spin-down) |
| Playwright support | Good | Good (Docker) | Good |
| Auto-commit data | Built-in | Manual/extra step | Manual/extra step |
| GitHub Pages deploy | Built-in | Separate step | Separate step |

**Recommendation:** Start with GitHub Actions (included in this repo). Move to Railway or Render only if you need sub-30-minute intervals or hit Actions minute limits.
