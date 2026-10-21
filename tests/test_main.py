import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import requests

import main
from models import MarketQuote
from hedge import Leg

WINDOW = "2026-10-21T16:00:00Z"


def quote(platform, up, down, close_time=WINDOW, target=100000.0):
    return MarketQuote(platform, target, up, down, close_time)


def printed(func, *args):
    """Run func and return (what it returned, what it printed)."""
    output = io.StringIO()
    with redirect_stdout(output):
        result = func(*args)
    return result, output.getvalue()


@patch("main.current_event_slug", return_value="some-slug")
class TestScanOnce(unittest.TestCase):

    @patch("main.get_polymarket_market", return_value=quote("Polymarket", 0.47, 0.54))
    @patch("main.get_kalshi_market", return_value=quote("Kalshi", 0.53, 0.48))
    def test_alerts_on_opportunity(self, *mocks):
        _, out = printed(main.scan_once)
        self.assertIn("OPPORTUNITY  Poly UP + Kalshi DOWN", out)
        self.assertNotIn("OPPORTUNITY  Poly DOWN", out)

    @patch("main.get_polymarket_market", return_value=quote("Polymarket", 0.55, 0.50))
    @patch("main.get_kalshi_market", return_value=quote("Kalshi", 0.55, 0.50))
    def test_quiet_when_no_opportunity(self, *mocks):
        _, out = printed(main.scan_once)
        self.assertNotIn("OPPORTUNITY", out)

    @patch("main.get_polymarket_market", return_value=None)
    @patch("main.get_kalshi_market", return_value=quote("Kalshi", 0.53, 0.48))
    def test_market_missing(self, *mocks):
        _, out = printed(main.scan_once)
        self.assertIn("isn't open", out)

    @patch("main.get_polymarket_market", return_value=quote("Polymarket", 0.47, 0.54, "2026-10-21T16:15:00Z"))
    @patch("main.get_kalshi_market", return_value=quote("Kalshi", 0.53, 0.48))
    def test_windows_dont_match(self, *mocks):
        _, out = printed(main.scan_once)
        self.assertIn("windows don't match", out)
        self.assertNotIn("OPPORTUNITY", out)


class TestHedgeOnce(unittest.TestCase):
    leg = Leg("poly", "up", 0.47, 10)  # break-even Kalshi DOWN price is 0.49

    @patch("main.fetch_quote", return_value=quote("Kalshi", 0.52, 0.48))
    def test_alerts_when_hedge_profits(self, mock_fetch):
        keep_going, out = printed(main.hedge_once, self.leg, WINDOW)
        self.assertTrue(keep_going)
        self.assertIn("HEDGE NOW", out)
        mock_fetch.assert_called_with("kalshi")

    @patch("main.fetch_quote", return_value=quote("Kalshi", 0.45, 0.55))
    def test_shows_loss_without_alert(self, mock_fetch):
        keep_going, out = printed(main.hedge_once, self.leg, WINDOW)
        self.assertTrue(keep_going)
        self.assertIn("loss", out)
        self.assertNotIn("HEDGE NOW", out)

    @patch("main.fetch_quote", return_value=quote("Kalshi", 0.52, 0.48, "2026-10-21T16:15:00Z"))
    def test_stops_when_window_ends(self, mock_fetch):
        keep_going, out = printed(main.hedge_once, self.leg, WINDOW)
        self.assertFalse(keep_going)
        self.assertNotIn("HEDGE NOW", out)

    @patch("main.fetch_quote", return_value=None)
    def test_no_quote_keeps_going(self, mock_fetch):
        keep_going, _ = printed(main.hedge_once, self.leg, WINDOW)
        self.assertTrue(keep_going)


@patch("main.time.sleep")  # don't actually wait between checks
class TestRunEvery(unittest.TestCase):

    def test_stops_when_check_returns_false(self, mock_sleep):
        results = iter([True, True, False])
        calls = []

        def check():
            calls.append(1)
            return next(results)

        printed(main.run_every, check)
        self.assertEqual(len(calls), 3)

    def test_survives_a_failed_request(self, mock_sleep):
        results = iter([requests.ConnectionError("down"), False])

        def check():
            result = next(results)
            if isinstance(result, Exception):
                raise result
            return result

        _, out = printed(main.run_every, check)
        self.assertIn("request failed", out)

    def test_ctrl_c_stops_cleanly(self, mock_sleep):
        def check():
            raise KeyboardInterrupt

        _, out = printed(main.run_every, check)
        self.assertIn("Stopped", out)


if __name__ == "__main__":
    unittest.main()
