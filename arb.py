from dataclasses import dataclass
from models import MarketQuote
from fees import kalshi_fee, polymarket_fee

PAYOUT = 1.00  # every winning share or contract pays $1


def side_price(quote, side):
    """What it costs to buy one share of `side` ("up" or "down") on this quote."""
    if side == "up":
        return quote.up
    return quote.down


def opposite(side):
    if side == "up":
        return "down"
    return "up"


@dataclass
class ArbPair:
    """Buy one side on Polymarket and the other side on Kalshi."""
    poly: MarketQuote
    kalshi: MarketQuote
    poly_side: str  # "up" or "down"; Kalshi gets the opposite

    def label(self):
        return f"Poly {self.poly_side.upper()} + Kalshi {opposite(self.poly_side).upper()}"

    def poly_price(self):
        return side_price(self.poly, self.poly_side)

    def kalshi_price(self):
        return side_price(self.kalshi, opposite(self.poly_side))

    def total_cost(self, shares):
        """Cost of buying `shares` of each side, fees included."""
        poly_cost = self.poly_price() * shares + polymarket_fee(self.poly_price(), shares)
        kalshi_cost = self.kalshi_price() * shares + kalshi_fee(self.kalshi_price(), shares)
        return poly_cost + kalshi_cost

    def profit(self, shares):
        # exactly one side wins (if the targets match), so we get $1 back per pair
        return shares * PAYOUT - self.total_cost(shares)

    def target_gap(self):
        return abs(self.poly.target - self.kalshi.target)

    def is_opportunity(self, shares, min_profit=0.0, max_gap=0.0):
        # a gap between targets means BTC could land between them and BOTH legs lose
        return self.profit(shares) > min_profit and self.target_gap() <= max_gap


if __name__ == "__main__":
    # the example from claude.md: Poly UP 0.47 + Kalshi DOWN 0.48
    poly = MarketQuote("Polymarket", 100000.0, 0.47, 0.54, "2026-10-21T16:00:00Z")
    kalshi = MarketQuote("Kalshi", 100000.0, 0.53, 0.48, "2026-10-21T16:00:00Z")
    pair = ArbPair(poly, kalshi, "up")

    print(pair.label())
    print(f"Cost for 10:   {pair.total_cost(10):.4f}")
    print(f"Profit for 10: {pair.profit(10):.4f}")
    print(f"Target gap:    {pair.target_gap():.2f}")
    print(f"Opportunity?   {pair.is_opportunity(10)}")
