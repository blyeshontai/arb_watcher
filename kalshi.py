import requests

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"




# fetches and returns the data
def get_kalshi_market():

    # send the request to Kalshi's server with param filters, give up after 5 seconds
    response = requests.get(
    f"{BASE_URL}/markets",
    params={"series_ticker": "KXBTC15M", "status": "open"},
    timeout = 5,
    )

    #stop with a clear error if request failed
    response.raise_for_status()

    # turns the response into a python dictionary to manipulate
    data = response.json()

    #if there's no open market between windows
    if not data["markets"]:
        return None

    market = data["markets"][0]

    return {
        "target": market["floor_strike"],
        "up_price": float(market["yes_ask_dollars"]),
        "down_price": float(market["no_ask_dollars"]),
        "close_time": market["close_time"],
    }
market = get_kalshi_market()

if market is None:
    print("No Open Market Right Now")
else:
    print(f"Target: ${market['target']} | UP: {market['up_price']} | DOWN: {market['down_price']} | CLOSES: {market['close_time']}")
