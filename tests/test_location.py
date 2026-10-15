"""Unit tests for backend/location.py (mocked network, no real requests)."""

import json
import urllib.error
from unittest.mock import MagicMock, patch

from backend.location import _try_fallback, _try_geojs, _try_ip_api, _try_ipwho


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


class TestTryIpApi:
    def test_uses_plain_http_free_tier(self):
        # ip-api.com free tier rejects HTTPS ("SSL unavailable"); plain
        # HTTP is the documented working endpoint.
        with patch(
            "backend.location.urlopen",
            return_value=_resp(
                {
                    "status": "success",
                    "city": "Mecca",
                    "country": "Saudi Arabia",
                    "timezone": "Asia/Riyadh",
                    "lat": 21.42,
                    "lon": 39.82,
                }
            ),
        ) as u:
            r = _try_ip_api(0)
        assert u.call_args[0][0].full_url.startswith("http://ip-api.com/")
        assert r is not None and r["city"] == "Mecca"

    def test_fail_status_returns_none(self):
        with patch(
            "backend.location.urlopen",
            return_value=_resp({"status": "fail", "message": "SSL unavailable"}),
        ):
            assert _try_ip_api(0) is None


class TestTryIpwho:
    def test_success_parsed_with_nested_timezone(self):
        with patch(
            "backend.location.urlopen",
            return_value=_resp(
                {
                    "success": True,
                    "city": "Mecca",
                    "country": "Saudi Arabia",
                    "country_code": "SA",
                    "latitude": 21.42,
                    "longitude": 39.82,
                    "timezone": {"id": "Asia/Riyadh"},
                }
            ),
        ):
            r = _try_ipwho()
        assert r is not None
        assert r["city"] == "Mecca"
        assert r["country_code"] == "SA"
        assert r["timezone"] == "Asia/Riyadh"

    def test_unsuccessful_returns_none(self):
        with patch("backend.location.urlopen", return_value=_resp({"success": False})):
            assert _try_ipwho() is None


class TestTryGeojs:
    def test_success_parsed_with_string_coords(self):
        with patch(
            "backend.location.urlopen",
            return_value=_resp(
                {
                    "city": "Mecca",
                    "country": "Saudi Arabia",
                    "country_code": "SA",
                    "latitude": "21.42",
                    "longitude": "39.82",
                    "timezone": "Asia/Riyadh",
                }
            ),
        ):
            r = _try_geojs()
        assert r is not None
        assert r["city"] == "Mecca"
        assert r["latitude"] == 21.42

    def test_missing_country_code_returns_none(self):
        with patch("backend.location.urlopen", return_value=_resp({"city": "X"})):
            assert _try_geojs() is None
