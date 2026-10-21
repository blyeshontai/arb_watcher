import requests
from flask import Flask, jsonify, request, send_from_directory

from kalshi import get_kalshi_market
from polymarket import get_polymarket_market, current_event_slug
from arb import ArbPair, side_price, opposite
from hedge import (Leg, other_app, fetch_quote, locked_in, leg_cost, hedge_size,
                   max_hedge_price, shares_for, side_label)
from main import SHARES

# Flask serves anything in static/ at /static/...
app = Flask(__name__, static_folder="static")


@app.errorhandler(requests.RequestException)
def request_failed(error):
    # Kalshi or Polymarket didn't answer; the page shows this and tries again
    return jsonify(error=f"Request failed: {error}"), 502


@app.errorhandler(ValueError)
def bad_input(error):
    return jsonify(error=str(error)), 400


def read_leg_args():
    """App, side and price from the URL, like ?app=poly&side=up&price=38"""
    leg_app = request.args.get("app")
    side = request.args.get("side")
    if leg_app not in ["kalshi", "poly"]:
        raise ValueError("app must be kalshi or poly")
    if side not in ["up", "down"]:
        raise ValueError("side must be up or down")

    price = float(request.args.get("price", "")) / 100  # the page sends a percent
    if not 0 < price < 1:
        raise ValueError("price must be a percent between 0 and 100")
    return leg_app, side, price


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/status")
def status():
    """Scan mode: both pairings for the current window."""
    kalshi = get_kalshi_market()
    poly = get_polymarket_market(current_event_slug())

    if kalshi is None or poly is None:
        return jsonify(message="A market isn't open right now")
    if kalshi.close_time != poly.close_time:
        return jsonify(message="The two apps are on different windows right now")

    pairs = []
    for poly_side in ["up", "down"]:
        pair = ArbPair(poly, kalshi, poly_side)
        pairs.append({
            "label": pair.label(),
            "price_sum": pair.poly_price() + pair.kalshi_price(),
            "profit": pair.profit(SHARES),
            "opportunity": pair.is_opportunity(SHARES),
        })

    return jsonify(
        close_time=kalshi.close_time,
        target_gap=abs(kalshi.target - poly.target),
        shares=SHARES,
        pairs=pairs,
    )


@app.route("/shares")
def shares():
    """How many shares a receipt's cost bought: /shares?app=poly&side=up&price=38&cost=4.99"""
    leg_app, _, price = read_leg_args()
    cost = float(request.args.get("cost", ""))
    return jsonify(shares=shares_for(leg_app, cost, price))


@app.route("/hedge")
def hedge():
    """Hedge mode: the plan plus the live hedge price.
    /hedge?app=poly&side=up&price=38&shares=12.59"""
    leg_app, side, price = read_leg_args()
    leg = Leg(leg_app, side, price, float(request.args.get("shares", "")))
    hedge_app = other_app(leg.app)
    hedge_side = opposite(leg.side)

    data = {
        "leg_label": side_label(leg.app, leg.side),
        "leg_cost": leg.cost(),
        "hedge_label": side_label(hedge_app, hedge_side),
        "break_even": max_hedge_price(leg),  # None turns into null
        "live": None,
    }

    quote = fetch_quote(hedge_app)
    if quote is not None:
        live_price = side_price(quote, hedge_side)
        data["live"] = {
            "price": live_price,
            "enter": leg_cost(hedge_app, live_price, hedge_size(leg)),
            "result": locked_in(leg, live_price),
            "close_time": quote.close_time,
        }
    return jsonify(data)


if __name__ == "__main__":
    # debug=True reloads the server when I save a file
    app.run(debug=True)
