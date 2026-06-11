from datetime import date, datetime

import pytest

from backend.prayer_calc import calculate, PrayerTimesResult


class TestCalculate:
    def test_returns_result_for_tunis(self):
        r = calculate(36.8065, 10.1815)
        assert r is not None
        assert isinstance(r, PrayerTimesResult)
        assert r.calc_date == date.today()

    def test_returns_all_six_prayers(self):
        r = calculate(36.8065, 10.1815)
        d = r.as_dict()
        assert set(d.keys()) == {"fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"}

    def test_prayer_times_are_datetime(self):
        r = calculate(36.8065, 10.1815)
        for v in r.as_dict().values():
            assert isinstance(v, datetime)

    def test_fajr_before_sunrise(self):
        r = calculate(36.8065, 10.1815)
        assert r.fajr < r.sunrise

    def test_sunrise_before_dhuhr(self):
        r = calculate(36.8065, 10.1815)
        assert r.sunrise < r.dhuhr

    def test_dhuhr_before_asr(self):
        r = calculate(36.8065, 10.1815)
        assert r.dhuhr < r.asr

    def test_asr_before_maghrib(self):
        r = calculate(36.8065, 10.1815)
        assert r.asr < r.maghrib

    def test_maghrib_before_isha(self):
        r = calculate(36.8065, 10.1815)
        assert r.maghrib < r.isha

    def test_mecca_returns_valid_times(self):
        r = calculate(21.4225, 39.8262)
        assert r is not None
        d = r.as_dict()
        assert all(v is not None for v in d.values())

    def test_with_user_offsets(self):
        r = calculate(36.8065, 10.1815, offsets={"fajr": 5, "maghrib": -3})
        assert r is not None
        r_no = calculate(36.8065, 10.1815)
        assert r.fajr != r_no.fajr

    def test_specific_date(self):
        d = date(2025, 3, 15)
        r = calculate(36.8065, 10.1815, target_date=d)
        assert r is not None
        assert r.calc_date == d

    def test_different_madhab_hanafi_vs_shafi(self):
        r_shafi = calculate(36.8065, 10.1815, madhab="shafi")
        r_hanafi = calculate(36.8065, 10.1815, madhab="hanafi")
        assert r_shafi.asr != r_hanafi.asr

    def test_different_methods(self):
        r1 = calculate(36.8065, 10.1815, method_name="أم القرى (Umm Al-Qura)")
        r2 = calculate(36.8065, 10.1815, method_name="الهيئة المصرية للمساحة")
        assert r1 is not None
        assert r2 is not None

    def test_unknown_method_falls_back(self):
        r = calculate(36.8065, 10.1815, method_name="non_existent_method")
        assert r is not None

    def test_next_prayer_returns_valid_pair(self):
        r = calculate(36.8065, 10.1815)
        name, dt = r.next_prayer()
        assert isinstance(name, str)
        assert isinstance(dt, datetime)

    def test_as_dict_returns_same_on_repeated_calls(self):
        r = calculate(36.8065, 10.1815)
        assert r.as_dict() == r.as_dict()

    def test_remaining_positive(self):
        r = calculate(36.8065, 10.1815)
        rem = r.remaining()
        assert rem.total_seconds() > 0

    def test_offsets_produce_shifted_times(self):
        r = calculate(36.8065, 10.1815, offsets={"fajr": 10, "dhuhr": -5})
        r_base = calculate(36.8065, 10.1815)
        from datetime import timedelta
        assert abs((r.fajr - r_base.fajr).total_seconds() - 600) < 2
        assert abs((r.dhuhr - r_base.dhuhr).total_seconds() - (-300)) < 2

    def test_cached_result(self):
        from backend.prayer_calc import _calculate_cached
        r1 = _calculate_cached(36.8, 10.18, "2025-06-15", "وزارة الشؤون الدينية التونسية", "shafi", None, ())
        r2 = _calculate_cached(36.8, 10.18, "2025-06-15", "وزارة الشؤون الدينية التونسية", "shafi", None, ())
        assert r1 is r2
