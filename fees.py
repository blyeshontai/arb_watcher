import math

KALSHI_FEE_RATE = 0.07
POLYMARKET_FEE_RATE = 0.0695  # from the market's feeCoefficient


def kalshi_fee(price, contracts):
    """Kalshi's trading fee in dollars, rounded UP to the next cent."""
    raw = KALSHI_FEE_RATE * contracts * price * (1 - price)

    # floats are slightly off (0.07 can come out as 0.07000000000000001),
    # and ceil would bump that up a whole cent. Round off the noise first.
    cents = round(raw * 100, 6)
    return math.ceil(cents) / 100


def polymarket_fee(price, shares):
    """Polymarket US fee in dollars. Assumed same shape as Kalshi's.
    Not rounded until we can check it against a real receipt."""
    return POLYMARKET_FEE_RATE * shares * price * (1 - price)


if __name__ == "__main__":
    print(kalshi_fee(0.60, 3))       # 0.06
    print(kalshi_fee(0.50, 100))     # 1.75
    print(polymarket_fee(0.47, 10))  # about 0.173
