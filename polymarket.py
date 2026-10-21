import requests
from datetime import datetime, timezone
from models import MarketQuote

BASE_URL = "https://gateway.polymarket.us/v1"


def current_event_slug(now=None):
    """Slug for the 15-minute window that's live at `now` (default: right now)."""
    if now is None:
        now = datetime.now(timezone.utc)

    # round down to the last 15-minute mark
    window_start = now.replace(
        minute=now.minute - now.minute % 15,
        second=0,
        microsecond=0,
    )

    # format like: btc-updown-15m-2026-10-21-1615z
    return "btc-updown-15m-" + window_start.strftime("%Y-%m-%d-%H%M") + "z"


def get_polymarket_market(event_slug):
    """Fetch a 15-min BTC market from Polymarket US.
    Returns a MarketQuote, or None if there are no live quotes."""

    # the event has the market's slug, the target, and when the window ends
    response = requests.get(f"{BASE_URL}/events/slug/{event_slug}", timeout=5)
    response.raise_for_status()
    market = response.json()["event"]["markets"][0]

    # for the first few seconds of a window, the target isn't set yet (null)
    price_to_beat = market["assetPriceTerms"].get("priceToBeat")
    if price_to_beat is None:
        return None

    market_slug = market["slug"]
    target = float(price_to_beat["value"])
    close_time = market["assetPriceTerms"]["windowEnd"]

    # the BBO (best bid and offer) has the live prices
    bbo_response = requests.get(f"{BASE_URL}/markets/{market_slug}/bbo", timeout=5)
    bbo_response.raise_for_status()
    market_data = bbo_response.json()["marketData"]

    # near the close (or right after a new window opens), there may be no quotes
    if "longQuote" not in market_data or "shortQuote" not in market_data:
        return None

    return MarketQuote(
        platform="Polymarket",
        target=target,
        up=float(market_data["longQuote"]["value"]),
        down=float(market_data["shortQuote"]["value"]),
        close_time=close_time,
    )


if __name__ == "__main__":
    print(current_event_slug())
    print(get_polymarket_market(current_event_slug()))
