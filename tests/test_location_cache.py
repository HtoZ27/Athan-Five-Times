"""Tests for the 24h auto-location disk cache (ported from original prayer_app)."""

import json
import time
import urllib.error
from unittest.mock import patch

from backend.location import (
    _detect_sync,
    _get_cached_location,
    _save_location_cache,
    clear_location_cache,
)


def _resp(payload):
    class _R:
        def read(self):
            return json.dumps(payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return _R()


_GOOD = {
    "status": "success",
    "city": "Tunis",
    "country": "Tunisia",
    "lat": 36.8,
    "lon": 10.18,
    "timezone": "Africa/Tunis",
}


def _use_tmp_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))


class TestLocationCache:
    def test_success_saves_cache(self, monkeypatch, tmp_path):
        _use_tmp_cache(monkeypatch, tmp_path)
        with patch("backend.location.urlopen", return_value=_resp(_GOOD)):
            r = _detect_sync()
        assert r is not None and r["city"] == "Tunis"
        cache = tmp_path / "prayer-times" / "location.json"
        assert cache.is_file()
        payload = json.loads(cache.read_text(encoding="utf-8"))
        assert payload["data"]["city"] == "Tunis"

    def test_fresh_cache_skips_network(self, monkeypatch, tmp_path):
        _use_tmp_cache(monkeypatch, tmp_path)
        _save_location_cache({"city": "Cached", "country_code": "TN"})
        with patch(
            "backend.location.urlopen",
            side_effect=urllib.error.URLError("must not be called"),
        ):
            r = _detect_sync()
        assert r is not None and r["city"] == "Cached"

    def test_stale_cache_ignored(self, monkeypatch, tmp_path):
        _use_tmp_cache(monkeypatch, tmp_path)
        cache = tmp_path / "prayer-times" / "location.json"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps({"timestamp": time.time() - 90000, "data": {"city": "Old"}}),
            encoding="utf-8",
        )
        with patch("backend.location.urlopen", return_value=_resp(_GOOD)):
            r = _detect_sync()
        assert r is not None and r["city"] == "Tunis"

    def test_corrupt_cache_ignored(self, monkeypatch, tmp_path):
        _use_tmp_cache(monkeypatch, tmp_path)
        cache = tmp_path / "prayer-times" / "location.json"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text("not-json{{{", encoding="utf-8")
        with patch("backend.location.urlopen", return_value=_resp(_GOOD)):
            r = _detect_sync()
        assert r is not None and r["city"] == "Tunis"

    def test_clear_removes_cache(self, monkeypatch, tmp_path):
        _use_tmp_cache(monkeypatch, tmp_path)
        _save_location_cache({"city": "X"})
        assert _get_cached_location() is not None
        clear_location_cache()
        assert _get_cached_location() is None

    def test_failure_saves_nothing(self, monkeypatch, tmp_path):
        _use_tmp_cache(monkeypatch, tmp_path)
        with patch(
            "backend.location.urlopen",
            side_effect=urllib.error.URLError("offline"),
        ):
            assert _detect_sync() is None
        assert not (tmp_path / "prayer-times" / "location.json").exists()
