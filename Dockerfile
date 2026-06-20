# Optional full image with Playwright (Western Union). Live API defaults to skip_browser=true.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only needed if LIVE_API_SKIP_BROWSER=false
RUN playwright install --with-deps chromium

COPY . .

ENV LIVE_API_SKIP_BROWSER=true
ENV LIVE_API_WARM_CACHE=true
ENV LIVE_API_CACHE_SECONDS=120

EXPOSE 8000

CMD ["python", "main.py", "--serve"]
