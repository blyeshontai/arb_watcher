import time
from datetime import datetime

import requests

from kalshi import get_kalshi_market
from polymarket import get_polymarket_market, current_event_slug
from arb import ArbPair, side_price, opposite
from hedge import (ask_choice, ask_leg, print_plan, fetch_quote, other_app, locked_in,
                   leg_cost, hedge_size, side_label, percent, outcome)

CHECK_EVERY = 1.5  # seconds between checks
SHARES = 10        # pair size for the scan math


def now_str():
    return datetime.now().strftime("%H:%M:%S")


def alert(message):
    # a block of ! so it stands out from the normal lines
    bar = "!" * (len(message) + 8)
    print(bar)
    print(f"!!! {message} !!!")
    print(bar)


def scan_once():
    """One check of both apps for an arb in the current window."""
    kalshi = get_kalshi_market()
    poly = get_polymarket_market(current_event_slug())

    if kalshi is None or poly is None:
        print(f"{now_str()}  a market isn't open right now")
        return
    if kalshi.close_time != poly.close_time:
        print(f"{now_str()}  windows don't match: Kalshi {kalshi.close_time} vs Polymarket {poly.close_time}")
        return

    pairs = [ArbPair(poly, kalshi, "up"), ArbPair(poly, kalshi, "down")]

    parts = []
    for pair in pairs:
        price_sum = pair.poly_price() + pair.kalshi_price()
        parts.append(f"{pair.label()} {price_sum:.3f} (${pair.profit(SHARES):+.2f})")
    line = f"{now_str()}  " + " | ".join(parts)
    if pairs[0].target_gap() > 0:
        line += f" | target gap {pairs[0].target_gap():.2f}"
    print(line)

    for pair in pairs:
        if pair.is_opportunity(SHARES):
            alert(f"OPPORTUNITY  {pair.label()}  profit ${pair.profit(SHARES):+.3f} for {SHARES}")


def hedge_once(leg, window):
    """One check of the live hedge price. Returns False once the window is over."""
    hedge_app = other_app(leg.app)
    quote = fetch_quote(hedge_app)

    if quote is None:
        print(f"{now_str()}  no live {hedge_app} quote right now")
        return True
    if quote.close_time != window:
        print(f"{now_str()}  the window that closed at {window} is over")
        return False

    price = side_price(quote, opposite(leg.side))
    result = locked_in(leg, price)
    # what to type into the app's amount box to get the matching shares
    enter = leg_cost(hedge_app, price, hedge_size(leg))
    hedge = f"{side_label(hedge_app, opposite(leg.side))} {percent(price)}  enter ${enter:.2f}  {outcome(result)}"
    print(f"{now_str()}  {hedge}")

    if result >= 0:
        alert(f"HEDGE NOW  {hedge}")
    return True


def run_every(check):
    """Call check() every CHECK_EVERY seconds until it returns False or Ctrl+C."""
    try:
        while True:
            try:
                if check() is False:
                    return
            except requests.RequestException as error:
                # a dropped request shouldn't kill the loop; try again next time
                print(f"{now_str()}  request failed: {error}")
            time.sleep(CHECK_EVERY)
    except KeyboardInterrupt:
        print("\nStopped")


def scan_mode():
    print(f"Scanning every {CHECK_EVERY}s for {SHARES} pairs. Ctrl+C to stop.")
    run_every(scan_once)


def hedge_mode():
    leg = ask_leg()
    print_plan(leg)

    # the leg belongs to the window that's live now; stop when it ends
    quote = fetch_quote(other_app(leg.app))
    if quote is None:
        print("No live quote to hedge against right now.")
        return
    window = quote.close_time

    print(f"\nWatching the hedge price every {CHECK_EVERY}s. Ctrl+C to stop.")
    run_every(lambda: hedge_once(leg, window))


if __name__ == "__main__":
    mode = ask_choice("Mode (scan/hedge): ", ["scan", "hedge"])
    if mode == "scan":
        scan_mode()
    else:
        hedge_mode()

