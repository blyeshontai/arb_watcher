import unittest
from unittest.mock import patch

import requests

from server import app
from models import MarketQuote

WINDOW = "2026-10-21T16:00:00Z"


def quote(platform, up, down, close_time=WINDOW):
    return MarketQuote(platform, 100000.0, up, down, close_time)


class TestServer(unittest.TestCase):

    def setUp(self):
        # Flask's test client calls the routes without starting a real server
        self.client = app.test_client()

    @patch("server.current_event_slug", return_value="some-slug")
    @patch("server.get_polymarket_market", return_value=quote("Polymarket", 0.47, 0.54))
    @patch("server.get_kalshi_market", return_value=quote("Kalshi", 0.53, 0.48))
    def test_status_finds_opportunity(self, *mocks):
        data = self.client.get("/status").get_json()
        self.assertEqual(data["close_time"], WINDOW)
        self.assertEqual([p["label"] for p in data["pairs"]],
                         ["Poly UP + Kalshi DOWN", "Poly DOWN + Kalshi UP"])
        self.assertTrue(data["pairs"][0]["opportunity"])
        self.assertFalse(data["pairs"][1]["opportunity"])

    @patch("server.current_event_slug", return_value="some-slug")
    @patch("server.get_polymarket_market", return_value=None)
    @patch("server.get_kalshi_market", return_value=quote("Kalshi", 0.53, 0.48))
    def test_status_market_missing(self, *mocks):
        data = self.client.get("/status").get_json()
        self.assertIn("isn't open", data["message"])

    @patch("server.get_kalshi_market", side_effect=requests.ConnectionError("down"))
    def test_status_request_failed(self, mock_get):
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 502)
        self.assertIn("Request failed", response.get_json()["error"])

    def test_shares_from_receipt(self):
        data = self.client.get("/shares?app=kalshi&side=up&price=88&cost=5").get_json()
        self.assertEqual(data["shares"], 5)

    def test_bad_input_is_400(self):
        self.assertEqual(self.client.get("/shares?app=nope&side=up&price=88&cost=5").status_code, 400)
        self.assertEqual(self.client.get("/shares?app=poly&side=up&price=abc&cost=5").status_code, 400)
        self.assertEqual(self.client.get("/hedge?app=poly&side=up&price=38").status_code, 400)

    @patch("server.fetch_quote", return_value=quote("Kalshi", 0.62, 0.38))
    def test_hedge(self, mock_fetch):
        data = self.client.get("/hedge?app=poly&side=up&price=38&shares=12.59").get_json()
        self.assertEqual(data["hedge_label"], "Kalshi DOWN")
        self.assertEqual(data["break_even"], 0.56)
        self.assertAlmostEqual(data["live"]["enter"], 5.16)
        self.assertAlmostEqual(data["live"]["result"], 2.44, places=2)  # $2.4396, shown as $2.44
        mock_fetch.assert_called_with("kalshi")

    @patch("server.fetch_quote", return_value=None)
    def test_hedge_no_live_price(self, mock_fetch):
        data = self.client.get("/hedge?app=poly&side=up&price=38&shares=12.59").get_json()
        self.assertIsNone(data["live"])


if __name__ == "__main__":
    unittest.main()
