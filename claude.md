# arb-watcher

A Python tool that watches the 15-minute Bitcoin "Up or Down" markets on **Kalshi** and **Polymarket US** and tells me when buying opposite sides on the two apps would pay out more than it costs (after fees). It only **alerts**; I place every trade myself.

## How to help me

I'm an apprentice software engineer and I'm building this to learn.

- **Explain and review; don't write or edit my files unless I ask.** I type the code myself.
- When a concept is new to me, it's fine to show an example I can retype. Otherwise give hints and let me try first.
- Explain errors by walking me through the traceback.
- Keep things simple. Don't add libraries or structure the project doesn't need yet.

## Files

| File | What it does |
|---|---|
| `models.py` | `MarketQuote` dataclass: `platform`, `target`, `up`, `down`, `close_time` |
| `kalshi.py` | `get_kalshi_market()` returns the current open market as a `MarketQuote`, or `None` |
| `polymarket.py` | `current_event_slug(now=None)` builds the live window's slug from the clock; `get_polymarket_market(event_slug)` returns a `MarketQuote` or `None` |
| `fees.py` | `kalshi_fee(price, contracts)` (rounded up to the cent) and `polymarket_fee(price, shares)` (unrounded) |
| `arb.py` | `ArbPair` (one side on Poly, the opposite on Kalshi): `total_cost`, `profit`, `target_gap`, `is_opportunity`; helpers `side_price`, `opposite` |
| `hedge.py` | `Leg` dataclass and the hedge math: `hedge_size`, `locked_in`, `max_hedge_price`; plus `fetch_quote` and the `input()` helpers. Asks the same 4 things for either app (app, side, price %, cost $), works out the shares, and lets me correct them. Output is in plain sentences |
| `main.py` | The live loop. Asks for a mode: **scan** checks both apps every 1.5s; **hedge** asks for my leg and watches the hedge price until the window ends |
| `server.py` | Flask server for the web UI. `GET /status` (scan), `GET /shares` (shares from a receipt's cost), `GET /hedge` (plan + live hedge price). Returns JSON; errors come back as `{"error": ...}` |
| `static/` | The web UI: `index.html` (layout), `style.css` (looks, green = opportunity), `app.js` (asks the server every 1.5s and fills the page) |
| `tests/` | `unittest` tests (`tests/__init__.py` is empty but lets `unittest` find them). The API tests use `unittest.mock` with fake JSON, so they don't hit the internet |

Each module has an `if __name__ == "__main__":` block for testing it on its own.

## Running

- `python main.py`: pick `scan` or `hedge`; Ctrl+C stops it
- `python server.py`, then open http://127.0.0.1:5000: the web UI (Ctrl+C in the terminal stops it)
- `python -m unittest`: runs every test file
- Libraries: `requests`, `flask`

## API facts we've confirmed

### Kalshi
- Base URL: `https://external-api.kalshi.com/trade-api/v2` (market data needs no auth)
- Request: `GET /markets?series_ticker=KXBTC15M&status=open`
- Series ticker `KXBTC15M` never changes. Event tickers look like `KXBTC15M-26OCT211100`, where the time is the window's **close** time in Eastern.
- Fields used: `floor_strike` (target, a number), `yes_ask_dollars` (cost of UP), `no_ask_dollars` (cost of DOWN), `close_time` (UTC). Prices are **strings**, so they need `float()`.
- Below 10¢ and above 90¢, prices move in tenths of a cent.

### Polymarket US
- This is `polymarket.us`, **not** the international `polymarket.com`. Different API; don't use the international (Gamma/CLOB) docs.
- Base URL: `https://gateway.polymarket.us/v1` (market data needs no auth)
- Event slug format: `btc-updown-15m-2026-10-21-1545z`, where the time is the window's **start** time in UTC.
- `GET /events/slug/{event_slug}` → `event.markets[0]` has:
  - `slug` (the **market** slug, which has a `cpc-` prefix)
  - `assetPriceTerms.priceToBeat.value` (target, a string)
  - `assetPriceTerms.windowEnd` (use this, not the market's `endDate`)
  - `feeCoefficient` (was 0.0695)
- `GET /markets/{market_slug}/bbo` → `marketData.longQuote.value` = cost of UP, `marketData.shortQuote.value` = cost of DOWN (strings).
- Near a window's close or open, `longQuote` / `shortQuote` can be missing. The function returns `None` then.
- In the first few seconds of a window, `priceToBeat` is `null` (also returns `None`), and the BBO request can 404 (shows as a failed request; the next check usually works).

### Matching the two
- Same window = Kalshi `close_time` equals Polymarket `windowEnd`.
- Both settle on **CF Benchmarks BRTI**, averaged over the last 60 seconds before the start and end times. In testing, the two targets matched exactly (gap 0.00).

## Fees
- Kalshi: `0.07 × contracts × price × (1 − price)`, rounded **up** to the cent.
  - Only buys **whole contracts**, so leftover money from the amount I enter isn't spent.
  - Receipt: entered $1.00 on Yes (UP) → 1 contract, cost $0.99 = 98¢ + 1¢ fee (0.07 × 1 × 0.98 × 0.02 = $0.0014, rounded up).
- Polymarket US: same shape with rate `0.0695` (from `feeCoefficient`). **Confirmed** by a receipt.
  - The fee comes **out of** the dollar amount I enter, so I get fewer shares rather than paying extra.
  - Allows **fractional shares** (3.95 below).
  - Receipt: entered $1.00 on UP at 24¢ → 3.95 shares, cost $0.95, fee $0.05 (0.0695 × 3.95 × 0.24 × 0.76 ≈ $0.050).
  - Rounding rule still unknown: $0.0501 shows as $0.05 whether it's rounded or not. Unrounded in `fees.py` for now.
- Example: Poly UP 0.47 + Kalshi DOWN 0.48 = 95¢ looked like 5¢ profit per pair, but fees took ~3.5¢ of it.

## Phase plan

- [x] **Phase 0:** Setup (venv, git, requests)
- [x] **Phase 1:** Read Kalshi
- [x] **Phase 2:** Read Polymarket US; `MarketQuote` class
- [x] **Phase 3:** Build the slug from the clock; `main.py` compares both for the same window
- [x] **Phase 4:** The math: fees, `ArbPair`, hedge mode
- [x] **Phase 5:** Live loop every 1.5s, two modes (scan and hedge). Alerts are a standout block of `!` lines, no sound. Failed requests are printed and the loop keeps going.
- [x] **Tests:** `unittest` for fees, `ArbPair`, the hedge math, both API parsers (mocked), and the loop pieces in `main.py`
- [ ] **Phase 6 (later):** Log every check and alert to CSV to see how often real opportunities happen.
- [ ] **Phase 7:** ~~Flask endpoint (`GET /status`) plus an HTML/CSS/JS dashboard that turns green on an opportunity~~ done (`server.py`, `static/`); I can test the endpoints in Postman. README still to do.

## Open questions
- Polymarket US fee rounding is still unknown (the 0.0695 rate is confirmed). A larger trade's receipt would show it. Only `fees.py` would change.
- Scan math uses a fixed 10 pairs (`SHARES` in `main.py`).

## Notes
- I also track real trades in a spreadsheet (`Prediction_Market_Arb_Tracker.xlsx`, not in this repo). Its Read Me says the two apps use different price feeds. That turned out to be wrong for Polymarket US; they both use BRTI.
