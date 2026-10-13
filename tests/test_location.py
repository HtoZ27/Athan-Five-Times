"""Unit tests for backend/location.py (mocked network, no real requests)."""

import json
import urllib.error
from unittest.mock import MagicMock, patch

from backend.location import _try_fallback


def _resp(payload):
    m = MagicMock()
    m.read.return_value = json.dumps(payload).encode()
    m.__enter__.return_value = m
    return m


class TestTryFallback:
    def test_uppercase_country_code(self):
        with patch(
            "backend.location.urlopen",
            return_value=_resp(
                {
                    "country_code": "tn",
                    "city": "Tunis",
                    "country_name": "Tunisia",
                    "latitude": 36.8,
                    "longitude": 10.18,
                    "timezone": "Africa/Tunis",
                }
            ),
        ):
            r = _try_fallback()
        assert r is not None
        assert r["country_code"] == "TN"

    def test_zero_coords_rejected(self):
        with patch(
            "backend.location.urlopen",
            return_value=_resp(
                {"country_code": "TN", "city": "X", "latitude": 0.0, "longitude": 0.0}
            ),
        ):
            assert _try_fallback() is None

    def test_out_of_range_rejected(self):
        with patch(
            "backend.location.urlopen",
            return_value=_resp(
                {"country_code": "TN", "city": "X", "latitude": 91.0, "longitude": 10.0}
            ),
        ):
            assert _try_fallback() is None

    def test_error_payload_rejected(self):
        with patch("backend.location.urlopen", return_value=_resp({"error": True})):
            assert _try_fallback() is None

    def test_network_failure_returns_none(self):
        with patch("backend.location.urlopen", side_effect=urllib.error.URLError("offline")):
            assert _try_fallback() is None
