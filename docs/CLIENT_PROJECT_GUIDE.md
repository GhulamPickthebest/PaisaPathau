# PaisaPathau Rates API Guide

Live URL: https://paisapathau-production.up.railway.app

**Preferred frontend endpoint:** [`/data/rates-table.json`](https://paisapathau-production.up.railway.app/data/rates-table.json)  
(JSON rows for the website table — not an HTML page. HTML preview: [`/`](https://paisapathau-production.up.railway.app/).)

---

## 1. How it works

1. Background workers fetch provider quotes and save a **snapshot**.
2. The API **only reads the snapshot** — visitors never trigger a scrape.
3. **API providers** refresh every **60 seconds**.
4. **Browser providers** (Xe, Ria, Taptap, Skrill) refresh every **5 minutes** on a separate worker.
5. Public responses only include **valid** quotes (`status=ok`, rate > 0, receive amount > 0).
6. On temporary failure (e.g. Remitly 429), we keep the **last successful quote** with its original `quoted_at` and set `is_fallback=true` / `quote_freshness=fallback`.
7. Quotes older than **1 hour** are marked `is_stale=true`. Quotes older than **24 hours** are **excluded** from the public table.

---

## 2. API endpoints

| URL | Use |
|-----|-----|
| `/` | HTML table (same public rows as rates-table) |
| `/data/rates-table.json` | **Preferred** clean public JSON for the website table |
| `/data/rates_table.json` | Same as rates-table.json (underscore alias) |
| `/data/latest_rates.json` | Snapshot body with cleaned `all_rates`, plus `public_table` and `admin` |
| `/data/latest_rates/stream` | SSE replay of public rows |
| `/data/aud_npr_transfer_methods.json` | Per payment-method matrix (valid rows in `latest_rates`; full matrix here) |
| `/data/admin_status.json` | Errors / unavailable / missing providers (not for public UI) |
| `/health` | Health + nested `admin` diagnostics |

Query params such as `send_amount`, `skip_browser`, `fresh` are accepted for compatibility but **do not trigger a live scrape**. The API always serves the stored snapshot.

---

## 3. Public table: `rates-table.json`

### Top-level fields

| Field | Meaning |
|-------|---------|
| `last_updated` | Snapshot timestamp (ISO UTC) |
| `send_amount` | AUD sent (default 1000) |
| `from_currency` / `to_currency` | `AUD` / `NPR` |
| `cached` / `fetch_mode` | Always snapshot mode for visitors |
| `snapshot_age_seconds` | Seconds since snapshot was written |
| `snapshot_refresh_seconds` | API refresh interval (60) |
| `quote_stale_after_seconds` | **3600** — quotes older than this are marked stale |
| `quote_expire_after_seconds` | **86400** — quotes older than this are hidden from public |
| `row_count` | Number of public rows |
| `rows` | Array of consumer-ready table rows |
| `status` | `ok` (or `warming` before first snapshot) |
| `canonical_rules` | Human-readable rules used to build the table |

### `canonical_rules` (returned live)

| Key | Rule |
|-----|------|
| `valid_only` | `status=ok` and exchange_rate > 0 and receive_amount > 0 |
| `wise` | Fee-inclusive Wise gateway v3 checkout quote; mid-market excluded |
| `instarem` | Instarem and Instarem (by Nium) are separate consumer brands on the same Nium network |
| `ranking` | Sorted by `receive_amount` descending |
| `freshness` | Marked stale after 3600s; excluded after 86400s |
| `fallback` | Temporary failures keep last successful quote with `is_fallback=true` |

### Row fields (each item in `rows`)

| Field | Meaning |
|-------|---------|
| `provider` | Company / brand name |
| `rate` / `exchange_rate` | NPR per 1 AUD (same value; 3dp display on HTML) |
| `fee` | Fee in AUD |
| `receive_amount` | NPR the recipient gets (**use this to rank providers**) |
| `send_amount` | AUD sent |
| `payment_method` | e.g. Bank Transfer, Cash Pickup |
| `customer_type` | `new_user` when applicable |
| `rate_label` | e.g. `New User` |
| `existing_user_rate` | Existing-user FX when available |
| `receive_amount_existing` | Existing-user receive NPR when available |
| `transfer_speed` | Delivery estimate text |
| `quoted_at` | Original timestamp of this quote |
| `quote_age_seconds` | Age of `quoted_at` in seconds |
| `is_fallback` | `true` if this is the last successful quote after a failed refresh |
| `is_stale` | `true` if age > 3600s **or** `is_fallback` |
| `quote_freshness` | `live` \| `stale` \| `fallback` |
| `brand_note` | Extra brand context (Instarem brands) |
| `news` | Human-readable notes (promo, fallback, existing rate, etc.) |
| `source` | e.g. `transfer_methods`, `wise_v3_quotes`, scraper source |
| `status` | Always `ok` in this endpoint |

**Frontend rule:** Use `/data/rates-table.json` only. Do not render error/zero rows from admin.

---

## 4. Freshness model

| Condition | Public behaviour |
|-----------|------------------|
| Quote age ≤ 3600s and not fallback | `quote_freshness=live`, `is_stale=false` |
| Quote age > 3600s | `is_stale=true`, `quote_freshness=stale` (still shown until expiry) |
| Provider failed this cycle; last good kept | `is_fallback=true`, `quote_freshness=fallback`, original `quoted_at` kept |
| Quote age > 86400s (24h) | **Excluded** from public table |

`aud_npr_transfer_methods.last_updated` is set when the matrix is refreshed and stays aligned with the snapshot update time.

---

## 5. Admin / health (errors only here)

Use `/data/admin_status.json` or `/health` → `admin`:

| Field | Meaning |
|-------|---------|
| `errors` | Fetch warnings (e.g. Remitly 429 cooldown) |
| `unavailable` | Providers not for the public table |

`unavailable.status` values include:

- `unavailable` — MoneyGram, ACE, LuLu, Revolut (no guest quote)
- `reference_only` — `Wise (mid-market)` (excluded from public comparison)
- `missing` — configured scraper but no current public quote (e.g. **Skrill** when down/expired)

---

## 6. New user vs existing user

| Provider | New vs existing? | Notes |
|----------|------------------|-------|
| Remitly | Yes | Separate rates/fees per method when available |
| WorldRemit | Sometimes | Promo vs crossed-out rate when API provides it |
| Instarem / Instarem (by Nium) | Fees may differ | Same FX; promo fee for new users possible |
| Wise | No | One public bank-transfer checkout quote |
| Western Union | No on current API | Bank transfer only from Wise comparisons |
| Others | No | Single quote |

---

## 7. Providers (AUD → NPR) — matches live public table

### Currently in public `rates-table` rows (typical)

| Provider | How we fetch | Methods in public API | Notes |
|----------|--------------|-----------------------|-------|
| Wise | Gateway v3 quotes (wise.com calculator) | Bank Transfer | Canonical fee-inclusive quote; mid-market excluded |
| Remitly | Remitly calculator API | Bank, Cash Pickup, Mobile Money | May show `is_fallback` during 429 cooldown |
| WorldRemit | GraphQL API | Bank, Cash, Mobile, Wallet | |
| Instarem | Instarem REST API | Bank Transfer | |
| Instarem (by Nium) | Same Nium API | Bank Transfer | Separate consumer brand; `brand_note` explains shared network |
| Western Union | Wise comparisons API | **Bank Transfer only** | Cash is **not** returned by the current production API |
| Xoom (PayPal) | Wise comparisons API | Bank transfer | Aggregated/indicative, not logged-in Xoom checkout |
| Xe Money Transfer | Playwright | Limited send-money quote | Browser; may be `stale` between browser cycles |
| Ria Money Transfer | Playwright + Ria API | Session-dependent label | Browser |
| Taptap Send | Playwright FX API | Wallet-oriented label | Browser |

### Configured but often missing from public rows

| Provider | Status |
|----------|--------|
| **Skrill** | Playwright scraper is configured, but it currently does **not** appear in live public rows (failed/expired). Listed under `admin.unavailable` as `missing` when absent. Do not document Skrill as a reliable live public row. |

### Not available (admin only)

| Provider | Why |
|----------|-----|
| MoneyGram | Captcha / no public guest API |
| ACE Money Transfer | Guest calculator has no AUD→NPR rate |
| LuLu Exchange | Rates only in app after eKYC |
| Revolut | No public AUD→NPR web/API quote |

---

## 8. Payment method coverage (what the API actually returns)

| Provider | Bank | Cash | Mobile / Wallet |
|----------|------|------|-----------------|
| Remitly | Yes | Yes | Yes |
| WorldRemit | Yes | Yes | Yes |
| Instarem | Yes | No | No |
| Instarem (by Nium) | Yes | No | No |
| Wise | Yes | No | No |
| Western Union | Yes | **No** (not in current API) | No |
| Xoom (PayPal) | Yes | No | No |
| Xe / Ria / Taptap | Limited / label varies | Limited | Limited |
| Skrill | No current public row | — | — |
| MoneyGram, ACE, LuLu, Revolut | No data | No data | No data |

---

## 9. Speed / refresh expectations

| Scenario | Typical |
|----------|---------|
| Visitor request (`rates-table.json`) | Milliseconds–~1s |
| API provider refresh | Every 60s |
| Browser provider refresh | Every 5 minutes |
| Remitly after 429 | 5-minute cooldown; last good quote kept as fallback |
| First deploy / warming | Until first snapshot is ready |

---

## 10. WordPress / frontend integration notes

1. Call **`/data/rates-table.json`** for the comparison table.
2. Rank by **`receive_amount`** (not FX alone).
3. Show `quoted_at` / `quote_freshness` / `is_stale` / `is_fallback` to users when useful.
4. Use `/data/admin_status.json` only for ops/admin UI.
5. `rates-table.json` is **JSON data** for your table UI; `/` is the HTML preview.
