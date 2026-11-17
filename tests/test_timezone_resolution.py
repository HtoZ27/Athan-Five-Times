"""Regression tests for country/city timezone resolution (review of 06809a1).

The packaged app ships without pytz, so these tests exercise the zone-table
path that real packages use: split comma-separated country codes, merge
``zone.tab`` + ``zone1970.tab``, pick the nearest zone for multi-zone
countries, and never keep a stale foreign zone when resolution used to fail.
"""

import sys

import pytest
from zoneinfo import ZoneInfo

from backend._constants import LANGS
from backend.i18n import set_lang
from backend.location import (
    _longitude_zone,
    _tz_for_country,
    _tz_for_country_code,
    _zones_by_country,
)
from backend.translations import country_name


def _tables_available() -> bool:
    return bool(_zones_by_country())


@pytest.mark.skipif(not _tables_available(), reason="system tzdata tables not installed")
class TestZoneTables:
    def test_comma_country_rows_are_split(self):
        zones = _zones_by_country()
        assert not [code for code in zones if "," in code]
        # Rows such as "SA,AQ,KW,YE" and "CH,DE,LI" used to land under a
        # literal comma key, leaving these countries with no zone at all.
        for code in ("BE", "AE", "CZ", "DK", "FI", "CH", "KW", "BH"):
            assert zones.get(code), f"{code} has no zone"

    @pytest.mark.parametrize(
        ("code", "expected"),
        [
            ("BE", "Europe/Brussels"),
            ("AE", "Asia/Dubai"),
            ("FR", "Europe/Paris"),
            ("GB", "Europe/London"),
            ("SA", "Asia/Riyadh"),
            ("KW", "Asia/Kuwait"),
            ("BH", "Asia/Bahrain"),
            ("OM", "Asia/Muscat"),
            ("MY", "Asia/Kuala_Lumpur"),
        ],
    )
    def test_single_zone_countries(self, code, expected):
        assert _tz_for_country_code(code) == expected

    @pytest.mark.parametrize(
        ("code", "latitude", "longitude", "expected"),
        [
            ("US", 34.0522, -118.2437, "America/Los_Angeles"),
            ("US", 40.7128, -74.0060, "America/New_York"),
            ("RU", 43.1333, 131.9000, "Asia/Vladivostok"),
            ("RU", 55.7558, 37.6173, "Europe/Moscow"),
            ("AU", -31.9505, 115.8605, "Australia/Perth"),
            ("AU", -33.8688, 151.2093, "Australia/Sydney"),
            ("CA", 49.2827, -123.1207, "America/Vancouver"),
            ("CA", 43.6532, -79.3832, "America/Toronto"),
            ("BR", -3.1190, -60.0217, "America/Manaus"),
            ("BR", -23.5505, -46.6333, "America/Sao_Paulo"),
            ("ES", 40.4168, -3.7038, "Europe/Madrid"),
            ("PT", 38.7223, -9.1393, "Europe/Lisbon"),
            ("ID", -6.2088, 106.8456, "Asia/Jakarta"),
            ("CN", 31.2304, 121.4737, "Asia/Shanghai"),
        ],
    )
    def test_multi_zone_uses_nearest_coordinates(self, code, latitude, longitude, expected):
        assert _tz_for_country_code(code, latitude, longitude) == expected

    def test_no_coordinates_keeps_first_zone(self):
        # Existing callers without coordinates must keep the old behaviour
        # (representative zone) instead of raising or returning "".
        assert _tz_for_country_code("BE") == "Europe/Brussels"
        assert _tz_for_country_code("US") == "America/New_York"

    def test_zero_coordinates_are_treated_as_missing(self):
        assert _tz_for_country_code("DE", 0.0, 0.0) == "Europe/Berlin"


class TestLanguageIndependence:
    def test_all_languages_resolve_by_iso_code(self):
        cities = {
            "SA": (21.4225, 39.8262, "Asia/Riyadh"),
            "GB": (51.5074, -0.1278, "Europe/London"),
            "DE": (52.5200, 13.4050, "Europe/Berlin"),
            "FR": (48.8566, 2.3522, "Europe/Paris"),
            "KW": (29.3759, 47.9774, "Asia/Kuwait"),
            "BH": (26.2285, 50.5860, "Asia/Bahrain"),
            "MY": (3.1390, 101.6869, "Asia/Kuala_Lumpur"),
            "OM": (23.5880, 58.3829, "Asia/Muscat"),
            "QA": (25.2854, 51.5310, "Asia/Qatar"),
            "YE": (15.3694, 44.1910, "Asia/Aden"),
            "AE": (25.2048, 55.2708, "Asia/Dubai"),
            "BE": (50.8503, 4.3517, "Europe/Brussels"),
        }
        failures = []
        original = "ar"
        try:
            for lang in LANGS:
                set_lang(lang)
                for code, (lat, lon, expected) in cities.items():
                    got = _tz_for_country(country_name(code), code, lat, lon)
                    if got != expected:
                        failures.append(f"{lang}/{code}: {got!r} != {expected!r}")
        finally:
            set_lang(original)
        assert not failures, "; ".join(failures)


class TestFallbacks:
    def test_unknown_country_falls_back_to_longitude(self):
        # XK (Kosovo) is an app country absent from the system tables.
        assert _tz_for_country("Kosovo", "XK", 42.66, 21.17) == "Etc/GMT-1"

    def test_longitude_zone_names_are_valid(self):
        for longitude in (-179, -118.24, -0.5, 0, 10.18, 151.2, 179):
            zone = _longitude_zone(longitude)
            assert ZoneInfo(zone) is not None
        assert _longitude_zone(0) == "UTC"
        assert _longitude_zone(10.18) == "Etc/GMT-1"
        assert _longitude_zone(-118.24) == "Etc/GMT+8"

    def test_bad_coordinates_do_not_crash(self):
        assert _tz_for_country("Tunisia", "TN", None, None) == "Africa/Tunis"
        assert _tz_for_country("Tunisia", "TN", "bad", "bad") == "Africa/Tunis"
        assert _longitude_zone("bad") == "UTC"


class TestControllerRegression:
    def _engine(self):
        from PySide6.QtWidgets import QApplication

        QApplication.instance() or QApplication(sys.argv)

        from backend.backend_controller import PrayerEngine

        return PrayerEngine()

    def test_country_change_replaces_stale_foreign_zone(self):
        engine = self._engine()
        try:
            engine.updateSetting("country", "AU")
            engine.updateSetting("city", "Perth")
            assert engine.getSetting("timezone") == "Australia/Perth"

            # BE used to resolve to "" and keep Australia/Lord_Howe.
            engine.updateSetting("country", "BE")
            engine.updateSetting("city", "Brussels")
            assert engine.getSetting("timezone") == "Europe/Brussels"
        finally:
            engine.cleanup()

    def test_timezone_entry_labels(self):
        engine = self._engine()
        try:
            assert engine.getTimezoneEntry("Australia/Perth")["name"] == "Perth"
            assert engine.getTimezoneEntry("Etc/GMT-1")["name"] == "UTC+1"
            assert engine.getTimezoneEntry("Etc/GMT+8")["name"] == "UTC-8"
        finally:
            engine.cleanup()

    def test_non_arabic_language_keeps_saudi_timezone(self):
        engine = self._engine()
        original = "ar"
        try:
            set_lang("fr")
            engine.updateSetting("country", "SA")
            engine.updateSetting("city", "Mecca")
            assert engine.getSetting("timezone") == "Asia/Riyadh"
            engine.recalculate()
            assert engine._result is not None
        finally:
            set_lang(original)
            engine.cleanup()

    def test_unchecking_custom_coords_restores_city_and_recalculates(self):
        engine = self._engine()
        try:
            engine.updateSetting("country", "TN")
            engine.updateSetting("city", "Tunis")
            engine.recalculate()
            tunis_fajr = engine._result.as_dict()["fajr"]

            engine.updateSetting("custom_coords", True)
            engine.updateSetting("latitude", -33.86)
            engine.updateSetting("longitude", 151.21)
            engine.updateSetting("timezone", "Australia/Sydney")
            engine.recalculate()
            sydney_fajr = engine._result.as_dict()["fajr"]
            assert abs((sydney_fajr - tunis_fajr).total_seconds()) > 3600

            engine._recalc_timer.stop()
            engine._recalc_pending = False
            engine.updateSetting("custom_coords", False)

            settings = engine.getSettings()
            assert settings["custom_coords"] is False
            assert abs(settings["latitude"] - 36.8065) < 0.01
            assert abs(settings["longitude"] - 10.1815) < 0.01
            assert settings["timezone"] == "Africa/Tunis"
            # The old code left the preview at the custom (Sydney) times.
            assert engine._recalc_pending is True
            engine._do_recalc()
            assert engine._result.as_dict()["fajr"] == tunis_fajr
        finally:
            engine.cleanup()
