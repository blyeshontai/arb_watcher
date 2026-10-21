import requests
from models import MarketQuote

BASE_URL = "https://gateway.polymarket.us/v1"


def get_polymarket_market(event_slug):
    """Fetch a 15-min BTC market from Polymarket US.
    Returns a MarketQuote, or None if the event isn't found."""


    # 1. GET the event: f"{BASE_URL}/events/slug/{event_slug}"
    #    (use timeout=5 and raise_for_status(), like Kalshi)
    # send the request to Polymarket's server, give up after 5 seconds
    response = requests.get(
    f"{BASE_URL}/events/slug/{event_slug}",
    timeout = 5,
    )

    #stop with a clear error if request failed
    response.raise_for_status()

    # 2. from the JSON, get the first market: data["event"]["markets"][0]
    # turns the response into a python dictionary to manipulate
    data = response.json()




    # 3. from that market, pull out:
    #       - its slug               → needed for step 4
    #       - the price to beat      → market["assetPriceTerms"]["priceToBeat"]["value"]
    #       - the close time         → market["assetPriceTerms"]["windowEnd"]
    market = data["event"]["markets"][0]
    market_slug = market["slug"]
    target = float(market["assetPriceTerms"]["priceToBeat"]["value"])
    close_time = market["assetPriceTerms"]["windowEnd"]

    print(market_slug, target, close_time)

    # 4. GET the BBO: f"{BASE_URL}/markets/{market_slug}/bbo", live prices
    bbo_response = requests.get(
            f"{BASE_URL}/markets/{market_slug}/bbo",
            timeout=5,
        )
    bbo_response.raise_for_status()
    bbo_data = bbo_response.json()


    # 5. from that JSON, pull UP and DOWN from longQuote / shortQuote
    # or pull out what it costs to buy each side
    up = float(bbo_data["marketData"]["longQuote"]["value"])
    down = float(bbo_data["marketData"]["shortQuote"]["value"])

    # 6. return a MarketQuote(platform="Polymarket", ...)
    # package it in the same shape as Kalshi's
    return MarketQuote(
            platform="Polymarket",
            target=target,
            up=up,
            down=down,
            close_time=close_time,
        )


quote = get_polymarket_market("btc-updown-15m-2026-10-21-1600z")

