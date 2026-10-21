import unittest
from fees import kalshi_fee, polymarket_fee


class TestKalshiFee(unittest.TestCase):
    # expected values worked out by hand, then rounded up to the cent

    def test_rounds_up_to_the_cent(self):
        self.assertEqual(kalshi_fee(0.60, 3), 0.06)   # 0.0504 -> 0.06
        self.assertEqual(kalshi_fee(0.30, 10), 0.15)  # 0.147  -> 0.15

    def test_exact_cents_stay_put(self):
        # float noise must not bump these up a cent
        self.assertEqual(kalshi_fee(0.50, 4), 0.07)
        self.assertEqual(kalshi_fee(0.50, 100), 1.75)

    def test_tiny_fee_is_at_least_a_cent(self):
        self.assertEqual(kalshi_fee(0.99, 1), 0.01)   # 0.000693 -> 0.01

    def test_zero_contracts(self):
        self.assertEqual(kalshi_fee(0.47, 0), 0.0)


class TestPolymarketFee(unittest.TestCase):

    def test_not_rounded(self):
        # assertAlmostEqual because floats rarely match exactly
        self.assertAlmostEqual(polymarket_fee(0.50, 100), 1.7375)
        self.assertAlmostEqual(polymarket_fee(0.47, 10), 0.1731245)

    def test_zero_shares(self):
        self.assertAlmostEqual(polymarket_fee(0.47, 0), 0.0)


if __name__ == "__main__":
    unittest.main()
