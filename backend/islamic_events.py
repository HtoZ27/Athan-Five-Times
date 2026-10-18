"""
Islamic (Hijri) calendar events for the desktop prayer app.

Provides a list of notable Islamic events for a given Hijri date, mirroring
the event set shipped in the reference prayer app (Salatuk): Hijri new year,
Ashura, White Days, first 10 of Rajab, Mid-Sha'ban, Ramadan countdown,
second/last 10 of Ramadan, Mid-Ramadan, plus the standard Eids, Hajj days
(Tarwiyah, Arafah, sacrifice day and Tashriq days).
"""

from __future__ import annotations

from datetime import date
from typing import List

from .hijri import gregorian_to_hijri, _hijri_leap


_HIJRI_MONTH_NAMES = {
    1: "محرم",
    2: "صفر",
    3: "ربيع الأول",
    4: "ربيع الثاني",
    5: "جمادى الأولى",
    6: "جمادى الثانية",
    7: "رجب",
    8: "شعبان",
    9: "رمضان",
    10: "شوال",
    11: "ذو القعدة",
    12: "ذو الحجة",
}


def _month_length(year: int, month: int) -> int:
    if month % 2 == 1:  # odd months have 30
        return 30
    if month == 12 and _hijri_leap(year):
        return 30
    return 29


def _day_of_year(year: int, month: int, day: int) -> int:
    doy = day
    for m in range(1, month):
        doy += _month_length(year, m)
    return doy


def _ramadan_start_doy(year: int) -> int:
    """Day-of-year of 1 Ramadan in the given Hijri year."""
    return _day_of_year(year, 9, 1)


def _days_until_ramadan(year: int, month: int, day: int) -> int:
    """Days from (year,month,day) to the start of Ramadan (this or next year)."""
    ram_start = _ramadan_start_doy(year)
    cur = _day_of_year(year, month, day)
    if cur <= ram_start:
        return ram_start - cur
    # next year
    year_len = 354 + _hijri_leap(year)
    return (year_len - cur) + _ramadan_start_doy(year + 1)


def events_for_date(d: date) -> List[str]:
    """Return a list of Islamic event names (Arabic) for the given Gregorian date."""
    y, m, day = gregorian_to_hijri(d)
    events: List[str] = []

    # Fixed (month, day) events
    if m == 1 and day == 1:
        events.append("ذكرى الهجرة النبوية — فاتح السنة الهجرية")
    if m == 1 and day == 10:
        events.append("عاشوراء")
    if m == 7 and 1 <= day <= 10:
        events.append("العشر الأوائل من رجب")
    if m == 8 and day == 14:
        events.append("ليلة النصف من شعبان")
    if m == 9 and day == 14:
        events.append("ليلة النصف من رمضان")
    if m == 9 and day == 15:
        events.append("النصف من رمضان")
    if m == 9 and 11 <= day <= 20:
        events.append("العشر الثانية من رمضان")
    if m == 9 and 21 <= day <= 30:
        events.append("العشر الأواخر من رمضان")
    if m == 12 and 1 <= day <= 10:
        events.append("العشر الأوائل من ذي الحجة")
    if m == 9 and day in (21, 23, 27, 29):
        events.append("ليلة القدر")
    if m == 10 and day == 1:
        events.append("عيد الفطر — أول أيام العيد")
    if m == 10 and day == 2:
        events.append("عيد الفطر — ثاني أيام العيد")
    if m == 12 and day == 8:
        events.append("يوم التروية")
    if m == 12 and day == 9:
        events.append("يوم عرفة")
    if m == 12 and day == 10:
        events.append("عيد الأضحى — يوم النحر")
    if m == 12 and day == 11:
        events.append("أيام التشريق — اليوم الأول")
    if m == 12 and day == 12:
        events.append("أيام التشريق — اليوم الثاني")
    if m == 12 and day == 13:
        events.append("أيام التشريق — اليوم الثالث")
    # White Days (13-15 of every month)
    if day in (13, 14, 15):
        events.append("الأيام البيض")

    # Ramadan countdown (1..10 days before Ramadan)
    if m != 9:
        du = _days_until_ramadan(y, m, day)
        if 1 <= du <= 10:
            events.append("باقي %d %s على رمضان" % (du, "يوم" if du == 1 else "أيام"))

    return events


def events_for_today() -> List[str]:
    from datetime import date as _d

    return events_for_date(_d.today())


def primary_event(d: date = None) -> str:
    """Return the most important event for the date, or ''."""
    from datetime import date as _d

    evs = events_for_date(d or _d.today())
    # prefer non-countdown events
    for e in evs:
        if not e.startswith("باقي"):
            return e
    return evs[0] if evs else ""


if __name__ == "__main__":
    from datetime import date as _d

    print(events_for_date(_d.today()))
