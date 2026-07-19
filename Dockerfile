# Production image: Playwright + Chromium for Ria, Taptap, Skrill, Xe, etc.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

COPY . .

ENV LIVE_API_SKIP_BROWSER=false
ENV LIVE_API_WARM_CACHE=false
ENV LIVE_API_WARM_CACHE_WITH_BROWSER=false
ENV LIVE_API_CACHE_SECONDS=60
ENV LIVE_API_BROWSER_REFRESH_SECONDS=300
ENV QUOTE_STALE_AFTER_SECONDS=3600
ENV QUOTE_EXPIRE_AFTER_SECONDS=86400

EXPOSE 8000

CMD ["python", "main.py", "--serve"]
