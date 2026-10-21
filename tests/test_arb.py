import unittest
from models import MarketQuote
from arb import ArbPair, side_price, opposite


def make_quotes(poly_target=100000.0, kalshi_target=100000.0):
    poly = MarketQuote("Polymarket", poly_target, 0.47, 0.54, "2026-10-21T16:00:00Z")
    kalshi = MarketQuote("Kalshi", kalshi_target, 0.53, 0.48, "2026-10-21T16:00:00Z")
    return poly, kalshi


class TestHelpers(unittest.TestCase):

    def test_side_price(self):
        poly, _ = make_quotes()
        self.assertEqual(side_price(poly, "up"), 0.47)
        self.assertEqual(side_price(poly, "down"), 0.54)

    def test_opposite(self):
        self.assertEqual(opposite("up"), "down")
        self.assertEqual(opposite("down"), "up")


class TestArbPair(unittest.TestCase):

    def test_picks_opposite_sides(self):
        poly, kalshi = make_quotes()
        pair = ArbPair(poly, kalshi, "up")
        self.assertEqual(pair.label(), "Poly UP + Kalshi DOWN")
        self.assertEqual(pair.poly_price(), 0.47)
        self.assertEqual(pair.kalshi_price(), 0.48)

    def test_total_cost_includes_fees(self):
        poly, kalshi = make_quotes()
        pair = ArbPair(poly, kalshi, "up")
        # poly: 4.70 + 0.1731245 fee | kalshi: 4.80 + 0.18 fee (0.17472 rounded up)
        self.assertAlmostEqual(pair.total_cost(10), 9.8531245)

    def test_profit(self):
        poly, kalshi = make_quotes()
        pair = ArbPair(poly, kalshi, "up")
        self.assertAlmostEqual(pair.profit(10), 10 - 9.8531245)

    def test_is_opportunity(self):
        poly, kalshi = make_quotes()
        self.assertTrue(ArbPair(poly, kalshi, "up").is_opportunity(10))
        # Poly DOWN 0.54 + Kalshi UP 0.53 costs more than $1 per pair
        self.assertFalse(ArbPair(poly, kalshi, "down").is_opportunity(10))

    def test_min_profit(self):
        poly, kalshi = make_quotes()
        pair = ArbPair(poly, kalshi, "up")
        self.assertFalse(pair.is_opportunity(10, min_profit=1.00))

    def test_target_gap_blocks_opportunity(self):
        poly, kalshi = make_quotes(poly_target=100010.0)
        pair = ArbPair(poly, kalshi, "up")
        self.assertAlmostEqual(pair.target_gap(), 10.0)
        self.assertFalse(pair.is_opportunity(10))
        self.assertTrue(pair.is_opportunity(10, max_gap=10.0))


if __name__ == "__main__":
    unittest.main()
