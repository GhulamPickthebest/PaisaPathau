# PaisaPathau Rates API Guide

Live URL: https://paisapathau-production.up.railway.app

## 1. How it works (simple)

1. A background worker fetches live quotes from each money transfer provider (some via API, some via browser automation).
2. Results are saved to a snapshot. The API only reads that snapshot — visitors never trigger a scrape.
3. API providers refresh every **60 seconds**. Browser providers refresh every **5 minutes** on a separate worker (so a hung browser cannot freeze rates).
4. If a provider fails on one run, we keep the last successful rate with `is_fallback=true` and the original quote timestamp.
5. The homepage (`/`) and **`/data/rates-table.json`** load only valid, deduplicated public rows. Unavailable providers are hidden.

## 2. API endpoints

| URL | Use |
|-----|-----|
| `/` | HTML table (public rows only) |
| `/data/rates-table.json` | **Preferred** clean public table for the website |
| `/data/rates_table.json` | Same as rates-table.json (underscore alias) |
| `/data/latest_rates/stream` | Streaming data for custom frontend (SSE) |
| `/data/latest_rates.json` | Full snapshot + `public_table` + `admin` diagnostics |
| `/data/aud_npr_transfer_methods.json` | Per payment method breakdown |
| `/data/admin_status.json` | Errors / unavailable providers (not for public UI) |
| `/health` | Health check + nested `admin` diagnostics |

Query params: `send_amount=1000`, `skip_browser=true` (faster, fewer providers). `fresh=true` is ignored (API always serves the stored snapshot).

### Public table rules (`rates-table.json`)

- Only `status=ok` with **exchange rate > 0** and **receive amount > 0**
- Temporary failures keep the last good quote (`is_fallback=true`, original `quoted_at`)
- Quotes older than 24h are excluded; quotes older than 1h are marked `is_stale=true`
- **Wise**: one fee-inclusive gateway v3 checkout quote (mid-market reference excluded)
- **Instarem** and **Instarem (by Nium)**: intentionally separate consumer brands on the same Nium network (`brand_note` explains this)
- Rows sorted by **receive_amount** descending (best for recipient ranking)
- Error/zero rows (MoneyGram, ACE, LuLu, Revolut, Remitly 429, etc.) appear only under `/health` → `admin` or `/data/admin_status.json`

## 3. Data fields (for WordPress / frontend)

### Main rate record (`all_rates`)

| Field | Meaning |
|-------|---------|
| `provider` | Company name |
| `exchange_rate` | NPR per 1 AUD (3 decimal precision) |
| `fee` | Fee in AUD |
| `receive_amount` | NPR recipient gets |
| `send_amount` | AUD sent (default 1000) |
| `delivery_method` | e.g. Bank transfer, Cash pickup |
| `transfer_speed` | e.g. Minutes, 1-2 business days |
| `customer_type` | `new_user` or `existing_user` (only some providers) |
| `rate_label` | "New User" or "Existing User" (only some providers) |
| `status` | `ok` or `error` |

### Transfer method matrix (`aud_npr_transfer_methods.rows`)

One row per provider + payment method:

| Field | Meaning |
|-------|---------|
| `transfer_method` | Bank Transfer, Cash Pickup, Mobile Money Transfer, Wallet Transfer |
| `new_user_rate` | Rate for new / promo users |
| `existing_user_rate` | Rate for existing users |
| `fee` | Fee for that method |
| `receive_amount_new` | NPR for new user |
| `receive_amount_existing` | NPR for existing user |
| `notes` | Extra info from our scraper |
| `status` | `ok`, `unavailable`, or `error` |

**Frontend rule:** Only show rows where `status` is `ok` and rate is greater than 0. The live table page already hides broken providers.

## 4. New user vs existing user (what we support)

| Provider | New vs existing? | Notes |
|----------|------------------|-------|
| Remitly | Yes | Two API calls. Reliable. |
| WorldRemit | Sometimes | Promo rate vs crossed-out “was” rate when API provides it |
| Western Union | Partial | Bank transfer can differ; cash often same FX, higher fee |
| Instarem | Fees only | Same FX rate; new users may get promo fee |
| Wise | No | One public rate. Wise may run promos on their site, but our API does not split new/existing |
| All others | No | Single quote or not available |

**Wise detail:** Wise usually uses the same exchange rate for everyone. Differences are mostly fees by payment method (card vs bank), not permanent new vs existing tiers. Our source only returns bank transfer quotes.

## 5. All 15 providers (AUD to NPR)

### Working now (11 providers)

**Wise**
- Status: Live
- How we fetch: Wise gateway v3 quotes API (same as wise.com calculator)
- Payment methods: Bank transfer only
- New / existing: No split
- Show on frontend: One fee-inclusive rate (canonical). Mid-market reference is stored separately as `Wise (mid-market)` and excluded from the public table.
- Limitation: No card vs bank breakdown from our API

**Remitly**
- Status: Live
- How we fetch: Remitly calculator API
- Payment methods: Bank, cash pickup, mobile (direct to phone)
- New / existing: Yes, separate rates
- Show on frontend: Two rates per method where different (new user / existing user). On 429, last successful quote is kept with `is_fallback=true`.

**WorldRemit**
- Status: Live
- How we fetch: GraphQL API
- Payment methods: Bank, cash, mobile wallet (Khalti alias)
- New / existing: Yes when promo data exists
- Show on frontend: Per method with new/existing when available

**Instarem**
- Status: Live
- How we fetch: Instarem public REST API
- Payment methods: Bank transfer only
- New / existing: Same FX; fees can differ
- Show on frontend: Bank transfer row. Rate uses applied FX (`instarem_fx_rate`)

**Instarem (by Nium)**
- Status: Live
- How we fetch: Same API as Instarem (intentional separate consumer brand on the Nium network)
- Payment methods: Bank transfer only
- New / existing: Same as Instarem
- Show on frontend: Separate brand row with `brand_note` explaining shared Nium rates

**Western Union**
- Status: Live
- How we fetch: Wise comparisons API (headline rate). Browser scrape optional for more detail.
- Payment methods: Bank transfer in API. Cash pickup via browser when enabled.
- New / existing: Partial (bank promo vs existing on website)
- Show on frontend: At minimum one bank rate. Full per-method data needs browser mode.

**Xoom (PayPal)**
- Status: Live
- How we fetch: Wise comparisons API (aggregated, not direct Xoom login)
- Payment methods: Bank transfer (as returned by comparisons API)
- New / existing: No
- Limitation: Not a logged-in Xoom quote. Good for comparison, not exact Xoom checkout rate.

**Xe Money Transfer**
- Status: Live (browser)
- How we fetch: Playwright on xe.com
- Payment methods: Limited send-money quote
- New / existing: No
- Note: Slower fetch. Needs Playwright on server.

**Ria Money Transfer**
- Status: Live (browser)
- How we fetch: Playwright + Ria calculator API
- Payment methods: Depends on Ria session
- New / existing: No

**Taptap Send**
- Status: Live (browser)
- How we fetch: Playwright captures api.taptapsend.com FX rates
- Payment methods: Mobile wallet focus
- New / existing: No

**Skrill**
- Status: Live (browser)
- How we fetch: Playwright on Skrill calculator (AU to Nepal)
- Payment methods: From calculator
- New / existing: No

### Not available (4 providers)

These cannot be scraped without login, partnership, or app access. Hidden on the live table page. Still in full JSON as `status: error` if needed for admin.

| Provider | Why not available |
|----------|-------------------|
| MoneyGram | Website blocks bots (captcha). Public API returns 401. Needs an official partner API. |
| ACE Money Transfer | The guest calculator does not show AUD to NPR rate. Login required. |
| LuLu Exchange | Live rates only inside LuLu Money app after eKYC. |
| Revolut | No AUD to NPR on public web or API. App/login required. |

## 6. Payment method coverage summary

| Provider | Bank | Cash | Mobile / Wallet |
|----------|------|------|-----------------|
| Remitly | Yes | Yes | Yes |
| WorldRemit | Yes | Yes | Yes |
| Instarem | Yes | No | No |
| Wise | Yes | No | No |
| Western Union | Yes | Yes* | No for NPR online |
| Xoom | Yes | No | No |
| Xe, Ria, Taptap, Skrill | Varies | Varies | Varies |
| MoneyGram, ACE, LuLu, Revolut | No data | No data | No data |

\*WU cash needs browser scrape for full detail.

## 7. Speed and caching (for client expectations)

| Scenario | Typical time |
|----------|--------------|
| Any visitor request (from snapshot) | ~1 second or less |
| API provider background refresh | Every 60 seconds |
| Browser provider background refresh | Every 5 minutes |
| First deploy / warming | Until first API snapshot is ready |

Visitors never trigger a live scrape. API and browser workers run separately — a hung browser scrape cannot freeze Wise/Remitly updates. Remitly 429s trigger a 5-minute cooldown (last good rate is kept). Railway runs on limited RAM; browser providers are fetched one at a time.
