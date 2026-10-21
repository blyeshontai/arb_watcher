import requests
from models import MarketQuote

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"


def get_kalshi_market():
    """Fetch the open 15-min BTC market from Kalshi.
    Returns a MarketQuote, or None between windows."""
    response = requests.get(
        f"{BASE_URL}/markets",
        params={"series_ticker": "KXBTC15M", "status": "open"},
        timeout=5,
    )
    response.raise_for_status()
    data = response.json()

    # no open market between windows
    if not data["markets"]:
        return None

    market = data["markets"][0]
    return MarketQuote(
        platform="Kalshi",
        target=float(market["floor_strike"]),
        up=float(market["yes_ask_dollars"]),
        down=float(market["no_ask_dollars"]),
        close_time=market["close_time"],
    )


if __name__ == "__main__":
    market = get_kalshi_market()
    if market is None:
        print("No open market right now")
    else:
        print(f"Target: ${market.target} | UP: {market.up} | DOWN: {market.down} | CLOSES: {market.close_time}")
