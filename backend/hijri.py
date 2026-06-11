"""
Hijri (Islamic) calendar date calculation.
Uses the Umm Al-Qura calendar approximation.
"""

import math
from datetime import date
from typing import Tuple


MONTH_NAMES = [
    "محرم", "صفر", "ربيع الأول", "ربيع الثاني",
    "جمادى الأولى", "جمادى الآخرة", "رجب", "شعبان",
    "رمضان", "شوال", "ذو القعدة", "ذو الحجة",
]

DAY_NAMES = [
    "الأحد", "الإثنين", "الثلاثاء", "الأربعاء",
    "الخميس", "الجمعة", "السبت",
]


def gregorian_to_hijri(d: date, offset_days: int = 0) -> Tuple[int, int, int]:
    """Convert a Gregorian date to (year, month, day) in the Hijri calendar."""
    y, m, day = d.year, d.month, d.day

    # Approximate conversion using the tabular Islamic calendar
    # Each Hijri year = 354.367 days
    julian_day = _to_julian(y, m, day)

    # Islamic epoch (1 Muharram 1 AH) = July 16, 622 CE (Julian)
    islamic_epoch = 1948439.5

    hijri_day = math.floor(julian_day - islamic_epoch) + offset_days
    hijri_year = math.floor((30 * hijri_day + 10646) / 10631)
    hijri_month = min(
        12,
        math.ceil((hijri_day - (29 * (hijri_year - 1) + _hijri_leap(hijri_year - 1) * 354)) / 29.5)
    )

    # Refine month and day
    hijri_days_in_year = 354 + _hijri_leap(hijri_year)
    day_of_year = hijri_day - (hijri_year - 1) * 354 - _hijri_leap_accum(hijri_year - 1)
    day_of_year = max(1, min(day_of_year, hijri_days_in_year))

    month_day_acc = 0
    for i in range(12):
        month_length = 30 if i % 2 == 0 else 29
        if i == 11 and _hijri_leap(hijri_year):
            month_length = 30
        if day_of_year <= month_day_acc + month_length:
            hijri_month = i + 1
            hijri_day = day_of_year - month_day_acc
            break
        month_day_acc += month_length
    else:
        hijri_month = 12
        hijri_day = day_of_year - month_day_acc

    hijri_day = max(1, hijri_day)

    return hijri_year, hijri_month, hijri_day


def format_hijri(d: date) -> str:
    """Return the Hijri date as a formatted string."""
    y, m, day = gregorian_to_hijri(d)
    return f"{day} {MONTH_NAMES[m-1]} {y} هـ"


def format_full(d: date) -> str:
    """Return full date string with weekday, Gregorian, and Hijri."""
    weekday = DAY_NAMES[(d.weekday() + 1) % 7]
    greg_str = d.strftime("%d %B %Y")
    hijri_str = format_hijri(d)
    return f"{weekday}، {greg_str}\n{hijri_str}"


def _hijri_leap(year: int) -> int:
    """Return 1 if the Hijri year is leap (355 days), else 0."""
    return 1 if (11 * year + 14) % 30 < 11 else 0


def _hijri_leap_accum(year: int) -> int:
    """Accumulated leap days up to (but not including) the given year."""
    return (year * 11 + 14) // 30


def _to_julian(y: int, m: int, d: int) -> float:
    """Convert Gregorian date to Julian day number."""
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    B = 2 - A + A // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5
