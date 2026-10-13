from datetime import date
from backend.hijri import (
    gregorian_to_hijri,
    format_hijri,
    _hijri_leap,
    _hijri_leap_accum,
    _to_julian,
)


class TestHijriLeap:
    def test_leap_year_known(self):
        assert _hijri_leap(2) == 1
        assert _hijri_leap(5) == 1
        assert _hijri_leap(7) == 1
        assert _hijri_leap(29) == 1

    def test_non_leap_year_known(self):
        assert _hijri_leap(1) == 0
        assert _hijri_leap(3) == 0
        assert _hijri_leap(4) == 0
        assert _hijri_leap(30) == 0

    def test_30_year_cycle_has_11_leaps(self):
        leaps = sum(_hijri_leap(y) for y in range(1, 31))
        assert leaps == 11

    def test_leap_accum_start(self):
        assert _hijri_leap_accum(0) == 0
        assert _hijri_leap_accum(1) == 0

    def test_leap_accum_grows(self):
        assert _hijri_leap_accum(15) >= 4
        assert _hijri_leap_accum(30) == 11


class TestToJulian:
    def test_returns_float(self):
        assert isinstance(_to_julian(2025, 1, 1), float)

    def test_increasing_date(self):
        j1 = _to_julian(2025, 1, 1)
        j2 = _to_julian(2025, 1, 2)
        assert j2 > j1


class TestGregorianToHijri:
    def test_returns_tuple_of_ints(self):
        result = gregorian_to_hijri(date(2025, 1, 1))
        assert isinstance(result, tuple)
        assert len(result) == 3
        y, m, d = result
        assert isinstance(y, int)
        assert isinstance(m, int)
        assert isinstance(d, int)

    def test_valid_month_range(self):
        y, m, d = gregorian_to_hijri(date(2025, 6, 15))
        assert 1 <= m <= 12

    def test_valid_day_range(self):
        y, m, d = gregorian_to_hijri(date(2025, 6, 15))
        assert 1 <= d <= 30

    def test_consecutive_days(self):
        y1, m1, d1 = gregorian_to_hijri(date(2025, 3, 1))
        y2, m2, d2 = gregorian_to_hijri(date(2025, 3, 2))
        if y1 == y2 and m1 == m2:
            assert d2 == d1 + 1
        else:
            assert d1 in (29, 30)

    def test_offset_shifts_day(self):
        d = date.today()
        _, _, day1 = gregorian_to_hijri(d, offset_days=0)
        _, _, day2 = gregorian_to_hijri(d, offset_days=1)
        diff = day2 - day1
        assert diff == 1 or (day1 >= 29 and day2 == 1)


class TestGregorianToHijriAnchors:
    """Tabular-calendar anchor dates (arithmetic, not observational Umm al-Qura)."""

    def test_islamic_epoch(self):
        assert gregorian_to_hijri(date(622, 7, 19)) == (1, 1, 1)

    def test_24_ramadan_1420(self):
        assert gregorian_to_hijri(date(2000, 1, 1)) == (1420, 9, 24)

    def test_1_ramadan_1446(self):
        assert gregorian_to_hijri(date(2025, 3, 1)) == (1446, 9, 1)

    def test_no_off_by_one_at_month_start(self):
        y, m, d = gregorian_to_hijri(date(2025, 5, 29))
        assert (y, m, d) == (1446, 12, 1)
        y0, m0, d0 = gregorian_to_hijri(date(2025, 5, 28))
        assert (y0, m0, d0) == (1446, 11, 30)


class TestFormatHijri:
    def test_contains_hijri_marker(self):
        result = format_hijri(date(2025, 6, 15))
        assert "هـ" in result

    def test_returns_string(self):
        result = format_hijri(date(2025, 6, 15))
        assert isinstance(result, str)
        assert len(result) > 5
