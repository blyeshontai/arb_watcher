import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from hedge import (Leg, other_app, hedge_size, locked_in, can_place, max_hedge_price,
                   percent, outcome, contracts_for, shares_for, ask_leg, print_plan)


def answers(*typed):
    """Fake what I'd type at each input() prompt, and hide the printing."""
    with patch("builtins.input", side_effect=typed), redirect_stdout(io.StringIO()):
        return ask_leg()


class TestWording(unittest.TestCase):

    def test_percent(self):
        self.assertEqual(percent(0.38), "38%")
        self.assertEqual(percent(0.995), "99.5%")

    def test_outcome(self):
        self.assertEqual(outcome(0.12), "profit $0.12")
        self.assertEqual(outcome(-0.4), "loss $0.40")
        self.assertEqual(outcome(0.001), "break even")

    def test_plan_is_short(self):
        out = io.StringIO()
        with redirect_stdout(out):
            print_plan(Leg("poly", "up", 0.38, 12.6))
        self.assertEqual(out.getvalue(), (
            "\nBased on your leg:\n"
            "  You paid $4.99 for Polymarket UP at 38%.\n"
            "  To hedge, buy Kalshi DOWN.\n"
            "  Your break even is 56%.\n"
        ))


class TestSharesFor(unittest.TestCase):

    def test_kalshi_whole_contracts(self):
        self.assertEqual(contracts_for(5.00, 0.88), 5)  # 5 cost $4.44, 6 would be $5.33
        self.assertEqual(contracts_for(1.00, 0.98), 1)  # the $0.99 receipt
        self.assertEqual(contracts_for(0.50, 0.88), 0)
        self.assertEqual(shares_for("kalshi", 5.00, 0.88), 5)

    def test_polymarket_receipt(self):
        # receipt: $4.99 @ 38% showed "To win $12.60"; cents rounding costs a penny
        self.assertAlmostEqual(shares_for("poly", 4.99, 0.38), 12.6, delta=0.02)


class TestAskLeg(unittest.TestCase):

    def test_same_questions_for_both_apps(self):
        # app, side, price %, cost $, Enter to accept the worked-out shares
        poly = answers("poly", "up", "38", "4.99", "")
        kalshi = answers("kalshi", "yes", "88%", "5", "")
        self.assertEqual(kalshi, Leg("kalshi", "up", 0.88, 5))
        self.assertEqual((poly.app, poly.side, poly.price), ("poly", "up", 0.38))
        self.assertAlmostEqual(poly.shares, 12.6, delta=0.02)

    def test_shares_can_be_corrected(self):
        leg = answers("poly", "up", "38", "4.99", "12.60")
        self.assertEqual(leg.shares, 12.6)
        leg = answers("kalshi", "no", "88", "5", "4")
        self.assertEqual(leg, Leg("kalshi", "down", 0.88, 4))

    def test_bad_answers_ask_again(self):
        leg = answers("poly", "sideways", "down", "0", "abc", "62", "10", "five", "")
        self.assertEqual((leg.side, leg.price), ("down", 0.62))


class TestHedgeSize(unittest.TestCase):

    def test_other_app(self):
        self.assertEqual(other_app("kalshi"), "poly")
        self.assertEqual(other_app("poly"), "kalshi")

    def test_kalshi_hedge_is_whole_contracts(self):
        self.assertEqual(hedge_size(Leg("poly", "up", 0.47, 10.6)), 11)
        self.assertEqual(hedge_size(Leg("poly", "up", 0.47, 0.2)), 1)  # never 0

    def test_poly_hedge_matches_exactly(self):
        self.assertEqual(hedge_size(Leg("kalshi", "down", 0.48, 10.4)), 10.4)


class TestLockedIn(unittest.TestCase):
    # Poly UP 0.47 x10 costs 4.70 + 0.1731245 fee = 4.8731245

    def test_small_profit(self):
        leg = Leg("poly", "up", 0.47, 10)
        # Kalshi DOWN 0.49 x10 = 4.90 + 0.18 fee
        self.assertAlmostEqual(locked_in(leg, 0.49), 10 - (4.8731245 + 5.08))

    def test_small_loss(self):
        leg = Leg("poly", "up", 0.47, 10)
        # Kalshi DOWN 0.50 x10 = 5.00 + 0.18 fee
        self.assertAlmostEqual(locked_in(leg, 0.50), 10 - (4.8731245 + 5.18))

    def test_uneven_counts_assume_the_smaller_leg_wins(self):
        leg = Leg("poly", "up", 0.47, 10.6)  # hedge is 11 Kalshi contracts
        result = locked_in(leg, 0.30)
        self.assertLess(result, 10.6 - leg.cost())  # paid out on 10.6, not 11


class TestMaxHedgePrice(unittest.TestCase):

    def test_kalshi_ticks(self):
        self.assertTrue(can_place("kalshi", 470))    # 47¢
        self.assertFalse(can_place("kalshi", 474))   # 47.4¢ not allowed mid-range
        self.assertTrue(can_place("kalshi", 95))     # 9.5¢
        self.assertTrue(can_place("kalshi", 905))    # 90.5¢
        self.assertTrue(can_place("poly", 474))

    def test_break_even_price(self):
        # checked by hand: 0.49 makes a little, 0.50 loses
        self.assertEqual(max_hedge_price(Leg("poly", "up", 0.47, 10)), 0.49)

    def test_result_never_loses(self):
        leg = Leg("kalshi", "down", 0.48, 10)
        price = max_hedge_price(leg)
        self.assertGreaterEqual(locked_in(leg, price), -1e-9)
        self.assertLess(locked_in(leg, price + 0.001), 0)

    def test_no_break_even(self):
        # paid 99.9¢; even the cheapest hedge loses
        self.assertIsNone(max_hedge_price(Leg("poly", "up", 0.999, 10)))


if __name__ == "__main__":
    unittest.main()
