"""Calculation integrity: ordering, sane gaps and robustness grid.

Guards the prayer engine against angle/offset wiring regressions
(the class of bug that once dead-coded the UAE 90-minute rule).
"""

from datetime import date, timedelta

import pytest

from backend.prayer_calc import CALCULATION_METHODS, calculate


CITIES = [
    (36.8, 10.18, "Africa/Tunis"),  # Tunis
    (21.42, 39.82, "Asia/Riyadh"),  # Makkah
    (25.20, 55.27, "Asia/Dubai"),  # Dubai
    (41.0, 28.97, "Europe/Istanbul"),  # Istanbul
    (40.7, -74.0, "America/New_York"),  # New York
    (-33.9, 151.2, "Australia/Sydney"),  # Sydney (southern hemisphere)
    (64.1, -21.9, "Atlantic/Reykjavik"),  # high latitude
]

DATES = [date(2025, 1, 15), date(2025, 3, 20), date(2025, 6, 21), date(2025, 12, 21)]

METHODS = [k for k in CALCULATION_METHODS if k != "مخصص"]


def _span_hours(d, a, b):
    return (d[b] - d[a]).total_seconds() / 3600


class TestOrdering:
    @pytest.mark.parametrize("method", METHODS)
    @pytest.mark.parametrize("day", DATES)
    def test_strict_order_tunis(self, method, day):
        r = calculate(36.8, 10.18, target_date=day, method_name=method, tz_name="Africa/Tunis")
        assert r is not None
        d = r.as_dict()
        order = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
        times = [d[k] for k in order]
        assert times == sorted(times), (method, day, times)
        assert len(set(times)) == 6

    @pytest.mark.parametrize("lat,lon,tz", CITIES)
    def test_strict_order_world(self, lat, lon, tz):
        r = calculate(
            lat,
            lon,
            target_date=date(2025, 6, 15),
            method_name="رابطة العالم الإسلامي (MWL)",
            tz_name=tz,
        )
        if r is None:  # polar edge: explicit None, never garbage
            return
        d = r.as_dict()
        times = [d[k] for k in ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]]
        assert times == sorted(times)


class TestSaneGaps:
    @pytest.mark.parametrize("method", METHODS)
    def test_gaps_bounded(self, method):
        r = calculate(
            36.8, 10.18, target_date=date(2025, 6, 15), method_name=method, tz_name="Africa/Tunis"
        )
        assert r is not None
        d = r.as_dict()
        assert 0 < _span_hours(d, "fajr", "sunrise") < 3
        assert 0 < _span_hours(d, "maghrib", "isha") < 4
        assert 0 < _span_hours(d, "sunrise", "dhuhr") < 8
        assert 0 < _span_hours(d, "dhuhr", "asr") < 6

    def test_uae_interval_exact(self):
        r = calculate(
            25.20,
            55.27,
            target_date=date(2025, 6, 15),
            method_name="الهيئة العامة للشؤون الإسلامية (الإمارات)",
            tz_name="Asia/Dubai",
        )
        gap = (r.as_dict()["isha"] - r.as_dict()["maghrib"]).total_seconds() / 60
        assert abs(gap - 90.0) < 0.6


class TestRobustness:
    def test_cache_consistency(self):
        a = calculate(
            36.8,
            10.18,
            target_date=date(2025, 6, 15),
            method_name="رابطة العالم الإسلامي (MWL)",
            tz_name="Africa/Tunis",
        )
        b = calculate(
            36.8,
            10.18,
            target_date=date(2025, 6, 15),
            method_name="رابطة العالم الإسلامي (MWL)",
            tz_name="Africa/Tunis",
        )
        assert a.as_dict() == b.as_dict()

    def test_day_continuity(self):
        def tod(dt):
            return dt.hour * 3600 + dt.minute * 60 + dt.second

        prev = None
        for i in range(5):
            day = date(2025, 6, 15) + timedelta(days=i)
            r = calculate(
                36.8,
                10.18,
                target_date=day,
                method_name="رابطة العالم الإسلامي (MWL)",
                tz_name="Africa/Tunis",
            )
            assert r is not None
            if prev is not None:
                drift = abs(tod(r.as_dict()["dhuhr"]) - tod(prev))
                assert drift < 300, (day, drift)
            prev = r.as_dict()["dhuhr"]

    def test_unknown_method_falls_back(self):
        r = calculate(
            36.8, 10.18, target_date=date(2025, 6, 15), method_name="لا شيء", tz_name="Africa/Tunis"
        )
        assert r is not None
