import unittest
from datetime import datetime, timezone
from unittest.mock import patch, Mock

from kalshi import get_kalshi_market
from polymarket import current_event_slug, get_polymarket_market


def fake_response(data):
    """Stands in for what requests.get returns, so tests don't hit the internet."""
    response = Mock()
    response.json.return_value = data
    return response


KALSHI_DATA = {"markets": [{
    "floor_strike": 84358.55,
    "yes_ask_dollars": "0.94",
    "no_ask_dollars": "0.061",
    "close_time": "2026-10-21T17:30:00Z",
}]}

POLY_EVENT = {"event": {"markets": [{
    "slug": "cpc-btc-updown-15m-2026-10-21-1715z",
    "assetPriceTerms": {
        "priceToBeat": {"value": "84358.55"},
        "windowEnd": "2026-10-21T17:30:00Z",
    },
}]}}

POLY_BBO = {"marketData": {
    "longQuote": {"value": "0.91"},
    "shortQuote": {"value": "0.1"},
}}


class TestKalshi(unittest.TestCase):

    @patch("kalshi.requests.get")
    def test_parses_market(self, mock_get):
        mock_get.return_value = fake_response(KALSHI_DATA)
        quote = get_kalshi_market()
        self.assertEqual(quote.platform, "Kalshi")
        self.assertEqual(quote.target, 84358.55)
        self.assertEqual(quote.up, 0.94)     # string turned into a float
        self.assertEqual(quote.down, 0.061)
        self.assertEqual(quote.close_time, "2026-10-21T17:30:00Z")

    @patch("kalshi.requests.get")
    def test_no_open_market(self, mock_get):
        mock_get.return_value = fake_response({"markets": []})
        self.assertIsNone(get_kalshi_market())


class TestPolymarketSlug(unittest.TestCase):

    def slug_at(self, hour, minute):
        return current_event_slug(datetime(2026, 10, 21, hour, minute, 30, tzinfo=timezone.utc))

    def test_rounds_down_to_window_start(self):
        self.assertEqual(self.slug_at(15, 52), "btc-updown-15m-2026-10-21-1545z")

    def test_exactly_on_the_mark(self):
        self.assertEqual(self.slug_at(15, 0), "btc-updown-15m-2026-10-21-1500z")

    def test_end_of_day(self):
        self.assertEqual(self.slug_at(23, 59), "btc-updown-15m-2026-10-21-2345z")


class TestPolymarketMarket(unittest.TestCase):

    @patch("polymarket.requests.get")
    def test_parses_market(self, mock_get):
        # first call returns the event, second the BBO
        mock_get.side_effect = [fake_response(POLY_EVENT), fake_response(POLY_BBO)]
        quote = get_polymarket_market("btc-updown-15m-2026-10-21-1715z")

        self.assertEqual(quote.platform, "Polymarket")
        self.assertEqual(quote.target, 84358.55)
        self.assertEqual(quote.up, 0.91)
        self.assertEqual(quote.down, 0.1)
        self.assertEqual(quote.close_time, "2026-10-21T17:30:00Z")

        # the BBO request used the market slug (with cpc-), not the event slug
        bbo_url = mock_get.call_args_list[1].args[0]
        self.assertTrue(bbo_url.endswith("/markets/cpc-btc-updown-15m-2026-10-21-1715z/bbo"))

    @patch("polymarket.requests.get")
    def test_missing_quote(self, mock_get):
        no_short = {"marketData": {"longQuote": {"value": "0.91"}}}
        mock_get.side_effect = [fake_response(POLY_EVENT), fake_response(no_short)]
        self.assertIsNone(get_polymarket_market("btc-updown-15m-2026-10-21-1715z"))


if __name__ == "__main__":
    unittest.main()
