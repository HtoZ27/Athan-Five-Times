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

    def test_uae_no_fixed_interval(self):
        # Isha is angle-derived (18.0): the params must carry no
        # isha_interval key that would override the angle.
        import backend.prayer_calc as pc

        params = pc._get_calc_methods()["الهيئة العامة للشؤون الإسلامية (الإمارات)"]
        assert "isha_interval" not in params
        assert params.get("isha_angle") == 18.0
        assert params.get("fajr_angle") == 18.0

    def _minutes(self, got: str, want: str) -> float:
        gh, gm = int(got[:2]), int(got[3:5])
        wh, wm = int(want[:2]), int(want[3:5])
        return abs((gh * 60 + gm) - (wh * 60 + wm))

    def test_official_abu_dhabi_oct9(self):
        # Awqaf Abu Dhabi official: Fajr 05:01, Isha 19:18.
        r = calculate(
            24.4539,
            54.3773,
            target_date=date(2026, 10, 9),
            method_name="الهيئة العامة للشؤون الإسلامية (الإمارات)",
            tz_name="Asia/Dubai",
        )
        d = {k: v.strftime("%H:%M") for k, v in r.as_dict().items()}
        assert d["fajr"] == "05:01", d
        assert d["isha"] == "19:18", d

    def test_official_qatar_oct11(self):
        # Qatar Awqaf Al Rayyan official: Maghrib 17:13, Isha 18:43.
        r = calculate(
            25.29,
            51.18,
            target_date=date(2026, 10, 11),
            method_name="وزارة الأوقاف القطرية",
            tz_name="Asia/Qatar",
        )
        d = {k: v.strftime("%H:%M") for k, v in r.as_dict().items()}
        assert d["maghrib"] == "17:13", d
        assert d["isha"] == "18:43", d
        assert self._minutes(d["fajr"], "04:14") <= 1, d

    def test_official_tubas_oct11(self):
        # Jordan-convention Tubas official: Fajr 05:17, Isha 19:33.
        r = calculate(
            32.32,
            35.37,
            target_date=date(2026, 10, 11),
            method_name="فلسطين (وزارة الأوقاف)",
            tz_name="Asia/Hebron",
        )
        d = {k: v.strftime("%H:%M") for k, v in r.as_dict().items()}
        assert self._minutes(d["fajr"], "05:17") <= 1, d
        assert self._minutes(d["isha"], "19:33") <= 1, d

    def test_official_baghdad_sep14(self):
        # muwaqqit Baghdad (Egyptian 19.5/17.5): Fajr 04:14, Isha 19:32.
        r = calculate(
            33.34,
            44.40,
            target_date=date(2026, 9, 14),
            method_name="العراق",
            tz_name="Asia/Baghdad",
        )
        d = {k: v.strftime("%H:%M") for k, v in r.as_dict().items()}
        assert self._minutes(d["fajr"], "04:14") <= 1, d
        assert self._minutes(d["isha"], "19:32") <= 1, d


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
