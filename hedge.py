from dataclasses import dataclass
from fees import kalshi_fee, polymarket_fee
from arb import PAYOUT, side_price, opposite
from kalshi import get_kalshi_market
from polymarket import get_polymarket_market, current_event_slug


@dataclass
class Leg:
    """A position I already bought."""
    app: str     # "kalshi" or "poly"
    side: str    # "up" or "down"
    price: float
    shares: float

    def cost(self):
        return leg_cost(self.app, self.price, self.shares)


def other_app(app):
    if app == "kalshi":
        return "poly"
    return "kalshi"


def fee_for(app, price, shares):
    if app == "kalshi":
        return kalshi_fee(price, shares)
    return polymarket_fee(price, shares)


def leg_cost(app, price, shares):
    """What one leg costs, fees included."""
    return price * shares + fee_for(app, price, shares)


def hedge_size(leg):
    """How many to buy on the other app. Kalshi only sells whole contracts."""
    if other_app(leg.app) == "kalshi":
        return max(1, round(leg.shares))
    return leg.shares


def locked_in(leg, hedge_price):
    """Worst-case result if I hedge `leg` at `hedge_price`. Only one side pays
    out, so if the share counts differ, assume the smaller one wins."""
    hedge_shares = hedge_size(leg)
    total_cost = leg.cost() + leg_cost(other_app(leg.app), hedge_price, hedge_shares)
    return min(leg.shares, hedge_shares) * PAYOUT - total_cost


def can_place(app, tenths):
    """Kalshi only uses tenths of a cent below 10¢ and above 90¢.
    `tenths` is the price in tenths of a cent (474 = $0.474)."""
    if app == "kalshi" and 100 <= tenths <= 900:
        return tenths % 10 == 0
    return True


def max_hedge_price(leg):
    """Highest hedge price that doesn't lose money, or None."""
    hedge_app = other_app(leg.app)

    # walk down from 99.9¢; the first price that breaks even is the max
    for tenths in range(999, 0, -1):
        if not can_place(hedge_app, tenths):
            continue
        price = tenths / 1000
        # tiny tolerance so float noise doesn't hide an exact break-even
        if locked_in(leg, price) >= -1e-9:
            return price
    return None


def fetch_quote(app):
    """Live quote for `app`, or None if there isn't one."""
    if app == "kalshi":
        return get_kalshi_market()
    return get_polymarket_market(current_event_slug())


def app_name(app):
    return "Kalshi" if app == "kalshi" else "Polymarket"


def side_label(app, side):
    # "Polymarket UP", "Kalshi DOWN"
    return f"{app_name(app)} {side.upper()}"


def percent(price):
    # 0.38 -> "38%", 0.995 -> "99.5%", the way the apps show prices
    return f"{price * 100:g}%"


def outcome(result):
    if abs(result) < 0.005:
        return "break even"
    if result > 0:
        return f"profit ${result:.2f}"
    return f"loss ${-result:.2f}"


def contracts_for(amount, price):
    """How many whole Kalshi contracts `amount` dollars buys, fees included."""
    contracts = int(amount // price)
    while contracts > 0 and leg_cost("kalshi", price, contracts) > amount + 1e-9:
        contracts -= 1
    return contracts


def shares_for(app, amount, price):
    """How many shares `amount` dollars bought, fees included."""
    if app == "kalshi":
        return contracts_for(amount, price)
    # Polymarket's fee grows evenly with shares, so the cost of 1 share
    # (fee included) divides straight into the amount
    return round(amount / leg_cost("poly", price, 1), 2)


def ask_choice(prompt, choices):
    # keep asking until the answer is one of the choices
    while True:
        answer = input(prompt).strip().lower()
        if answer in choices:
            return answer
        print(f"Please type one of: {', '.join(choices)}")


def ask_number(prompt):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Please type a number, like 0.47")


def ask_percent(prompt):
    # receipts show prices as percents, so "38" or "38%" means $0.38
    while True:
        answer = input(prompt).strip().rstrip("%")
        try:
            value = float(answer)
        except ValueError:
            print("Please type a percent, like 38")
            continue
        if 0 < value < 100:
            return value / 100
        print("Please type a percent between 0 and 100, like 38")


def ask_shares(app, amount, price):
    # neither receipt reliably shows the share count, so work it out and let me correct it
    shares = shares_for(app, amount, price)
    if app == "kalshi":
        prompt = f"That's {shares} contracts (check Kalshi's Portfolio). "
    else:
        prompt = f'That\'s ${shares:g} "To win" on the receipt. '
    while True:
        answer = input(prompt + "Press Enter if right, or type the real number: ").strip()
        if not answer:
            return shares
        try:
            return float(answer)
        except ValueError:
            print("Please type a number, or just press Enter")


def ask_leg():
    print("Enter the leg you already bought, from its receipt.")
    app = ask_choice("App (kalshi/poly): ", ["kalshi", "poly"])
    # Kalshi's buttons say Yes/No, so accept those too
    answer = ask_choice("Side (up/down, or yes/no on Kalshi): ", ["up", "down", "yes", "no"])
    side = "up" if answer in ["up", "yes"] else "down"
    price = ask_percent("Price you bought at (%): ")
    amount = ask_number("Cost ($): ")
    return Leg(app, side, price, ask_shares(app, amount, price))


def print_plan(leg):
    # kept short to read mid-trade; the live lines say how much to enter
    print()
    print("Based on your leg:")
    print(f"  You paid ${leg.cost():.2f} for {side_label(leg.app, leg.side)} at {percent(leg.price)}.")
    print(f"  To hedge, buy {side_label(other_app(leg.app), opposite(leg.side))}.")

    max_price = max_hedge_price(leg)
    if max_price is None:
        print("  No break even. Hedging can only cut your loss.")
    else:
        print(f"  Your break even is {percent(max_price)}.")


if __name__ == "__main__":
    # one-off plan, no live loop (main.py has the loop)
    print_plan(ask_leg())
