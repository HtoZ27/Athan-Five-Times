"""
Prayer time calculation using the adhan library.
Supports offsets, IANA timezones (DST), and multiple calculation methods.
"""

import functools
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
import logging
import math
import threading

logger = logging.getLogger(__name__)


_CALCULATION_METHODS: dict | None = None
_COUNTRY_DATA: tuple | None = None
_OFFSETS_CACHE: dict[int, tuple] = {}
_OFFSETS_LOCK = threading.Lock()


def _get_calc_methods() -> Dict[str, dict]:
    global _CALCULATION_METHODS
    if _CALCULATION_METHODS is None:
        import adhan.methods as methods

        _CALCULATION_METHODS = {
            "رابطة العالم الإسلامي (MWL)": methods.MUSLIM_WORLD_LEAGUE,
            "أم القرى (Umm Al-Qura)": methods.MAKKAH,
            "الهيئة المصرية للمساحة": methods.EGYPT,
            "جامعة العلوم الإسلامية كراتشي": methods.KARACHI,
            "الجمعية الإسلامية لأمريكا الشمالية (ISNA)": methods.ISNA,
            "طهران": methods.TEHRAN,
            "إندونيسيا (وزارة الشؤون الدينية)": {
                "fajr_angle": 20.0,
                "isha_angle": 18.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "ماليزيا (JAKIM)": {
                "fajr_angle": 20.0,
                "isha_angle": 18.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "سنغافورة (MUIS)": {
                "fajr_angle": 20.0,
                "isha_angle": 18.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "وزارة الشؤون الدينية التونسية": {
                "fajr_angle": 18.0,
                "isha_angle": 18.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "الجزائر": {
                "fajr_angle": 18.0,
                "isha_angle": 17.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "المغرب": {
                "fajr_angle": 19.0,
                "isha_angle": 17.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "ليبيا": {
                "fajr_angle": 18.5,
                "isha_angle": 17.5,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "موريتانيا": {
                "fajr_angle": 18.0,
                "isha_angle": 18.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "السودان": {
                "fajr_angle": 19.5,
                "isha_angle": 17.5,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "سوريا (وزارة الأوقاف)": {
                "fajr_angle": 19.5,
                "isha_angle": 17.5,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "العراق": {
                "fajr_angle": 17.5,
                "isha_angle": 17.5,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "فلسطين (وزارة الأوقاف)": {
                "fajr_angle": 17.5,
                "isha_angle": 17.5,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "ديانة تركيا (Diyanet)": {
                "fajr_angle": 18.0,
                "isha_angle": 17.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "روسيا (اتحاد المسلمين)": {
                "fajr_angle": 16.0,
                "isha_angle": 15.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "اتحاد المنظمات الإسلامية في فرنسا (UOIF)": {
                "fajr_angle": 12.0,
                "isha_angle": 12.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "الهيئة العامة للشؤون الإسلامية (الإمارات)": {
                "fajr_angle": 18.5,
                "isha_angle": 18.5,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
                "isha_interval": 90,
            },
            "وزارة الأوقاف القطرية": {
                "fajr_angle": 18.0,
                "isha_angle": 18.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "وزارة الأوقاف الكويتية": {
                "fajr_angle": 18.0,
                "isha_angle": 17.5,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "اليمن": {
                "fajr_angle": 18.2,
                "isha_angle": 18.2,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "طريقة فاروقي (باكستان/شمال الهند)": {
                "fajr_angle": 18.0,
                "isha_angle": 18.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
            "مخصص": {
                "fajr_angle": 18.0,
                "isha_angle": 17.0,
                "dhuhr_interval": 0,
                "maghrib_interval": 2,
            },
        }
    return _CALCULATION_METHODS


def clear_country_data():
    """Clear the cached country data to free memory."""
    global _COUNTRY_DATA
    _COUNTRY_DATA = None


def clear_calculation_cache():
    """Clear the LRU cached prayer calculations and offsets cache."""
    _calculate_cached.cache_clear()
    with _OFFSETS_LOCK:
        _OFFSETS_CACHE.clear()


def _get_country_data():
    global _COUNTRY_DATA
    if _COUNTRY_DATA is None:
        from .countries_data import (
            COUNTRY_METHODS,
            COUNTRIES,
            COUNTRY_CITIES,
        )

        _COUNTRY_DATA = (COUNTRY_METHODS, COUNTRIES, COUNTRY_CITIES)
    return _COUNTRY_DATA


def _get_methods_for(name: str) -> dict | None:
    return _get_calc_methods().get(name)


SUNRISE_ANGLE = 0.833

PRAYER_ORDER: list = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
OFFSET_KEYS = {"fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"}


def __getattr__(name):
    if name == "CALCULATION_METHODS":
        return _get_calc_methods()
    if name == "COUNTRY_METHODS":
        return _get_country_data()[0]
    if name == "COUNTRIES":
        return _get_country_data()[1]
    if name == "COUNTRY_CITIES":
        return _get_country_data()[2]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _utc_hour_to_local_dt(
    utc_hour: float,
    target_date: date,
    tz: timezone | None,
) -> datetime:
    total_seconds = int(round(utc_hour * 3600))
    days, remaining = divmod(total_seconds, 86400)
    h = remaining // 3600
    m = (remaining % 3600) // 60
    s = remaining % 60
    dt_utc = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        h,
        m,
        s,
        tzinfo=timezone.utc,
    ) + timedelta(days=days)
    if tz is None:
        return dt_utc.replace(tzinfo=None)
    return dt_utc.astimezone(tz).replace(tzinfo=None)


def _resolve_timezone(tz_name: str | None, longitude: float) -> timezone | None:
    if tz_name:
        try:
            from zoneinfo import ZoneInfo

            return ZoneInfo(tz_name)
        except (KeyError, OSError, TypeError):
            logger.warning("ZoneInfo not found for '%s', falling back to longitude offset", tz_name)
    hours = round(longitude / 15)
    return timezone(timedelta(hours=hours))


@dataclass
class PrayerTimesResult:
    fajr: datetime
    sunrise: datetime
    dhuhr: datetime
    asr: datetime
    maghrib: datetime
    isha: datetime
    calc_date: date

    def __post_init__(self):
        self._cached_dict: Optional[Dict[str, datetime]] = None

    def as_dict(self) -> Dict[str, datetime]:
        if self._cached_dict is None:
            self._cached_dict = {
                "fajr": self.fajr,
                "sunrise": self.sunrise,
                "dhuhr": self.dhuhr,
                "asr": self.asr,
                "maghrib": self.maghrib,
                "isha": self.isha,
            }
        return self._cached_dict

    def _ordered_prayers(self) -> list:
        return [(k, self.as_dict()[k]) for k in PRAYER_ORDER]

    def next_prayer(
        self, now: Optional[datetime] = None, tomorrow_fajr: Optional[datetime] = None
    ) -> Tuple[str, datetime]:
        if now is None:
            now = datetime.now()
        for name, time in self._ordered_prayers():
            if name == "sunrise":
                continue
            if time > now:
                return name, time
        if tomorrow_fajr is not None:
            return "fajr", tomorrow_fajr
        return "fajr", self.fajr + timedelta(days=1)

    def remaining(self, now: Optional[datetime] = None) -> timedelta:
        if now is None:
            now = datetime.now()
        _, t = self.next_prayer(now)
        if t > now:
            return t - now
        return timedelta(0)

    def with_offsets(self, offsets: Dict[str, int]):
        kwargs = {k: self.as_dict()[k] + timedelta(minutes=offsets.get(k, 0)) for k in PRAYER_ORDER}
        return PrayerTimesResult(**kwargs, calc_date=self.calc_date)


@functools.lru_cache(maxsize=128)
def _calculate_cached(
    lat_key: str,  # Rounded latitude as string key
    lon_key: str,  # Rounded longitude as string key
    target_date_iso: str,
    method_name: str,
    madhab: str,
    tz_name: str | None,
    offsets_tuple: tuple,
) -> Optional[PrayerTimesResult]:
    try:
        import adhan.calculations as calc
        import adhan.methods as methods

        target_date = date.fromisoformat(target_date_iso)
        latitude = float(lat_key)
        longitude = float(lon_key)
        tz = _resolve_timezone(tz_name, longitude)
        params = _get_methods_for(method_name)
        if params is None:
            logger.warning("Unknown method '%s', falling back to أم القرى", method_name)
            params = methods.MAKKAH
        eot_hours = math.degrees(calc.equation_of_time(target_date)) / 60.0

        zuhr_utc = 12.0 - (longitude / 15.0) - eot_hours
        zuhr = _utc_hour_to_local_dt(zuhr_utc, target_date, tz)

        sr_offset = calc.compute_time_at_sun_angle(target_date, latitude, SUNRISE_ANGLE)
        sunrise = _utc_hour_to_local_dt(zuhr_utc - abs(sr_offset), target_date, tz)

        fajr_angle = params.get("fajr_angle", 18.5)
        fajr_offset = calc.compute_time_at_sun_angle(target_date, latitude, fajr_angle)
        fajr = _utc_hour_to_local_dt(zuhr_utc - abs(fajr_offset), target_date, tz)

        multiplier = 2 if madhab == "hanafi" else 1
        asr_offset = calc.time_at_shadow_length(target_date, latitude, multiplier)
        asr = _utc_hour_to_local_dt(zuhr_utc + abs(asr_offset), target_date, tz)

        maghrib = _utc_hour_to_local_dt(zuhr_utc + abs(sr_offset), target_date, tz)

        dhuhr_adj = params.get("dhuhr_interval", params.get("dhuhr", 0))
        maghrib_adj = params.get("maghrib_interval", params.get("maghrib", 0))
        if dhuhr_adj:
            zuhr = zuhr + timedelta(minutes=dhuhr_adj)
        if maghrib_adj:
            maghrib = maghrib + timedelta(minutes=maghrib_adj)

        if "isha_interval" in params:
            isha = maghrib + timedelta(minutes=params["isha_interval"])
        else:
            isha_angle = params.get("isha_angle")
            if isha_angle is not None:
                isha_offset = calc.compute_time_at_sun_angle(target_date, latitude, isha_angle)
                isha = _utc_hour_to_local_dt(zuhr_utc + abs(isha_offset), target_date, tz)
            elif "isha_delay" in params:
                isha = maghrib + timedelta(hours=params["isha_delay"])
            else:
                isha = maghrib + timedelta(minutes=90)

        result = PrayerTimesResult(
            fajr=fajr,
            sunrise=sunrise,
            dhuhr=zuhr,
            asr=asr,
            maghrib=maghrib,
            isha=isha,
            calc_date=target_date,
        )

        offsets = dict(offsets_tuple) if offsets_tuple else {}
        if offsets:
            result = result.with_offsets(offsets)

        return result

    except (ImportError, ValueError, AttributeError, KeyError, TypeError):
        logger.exception("Prayer time calculation failed")
        return None


def calculate(
    latitude: float,
    longitude: float,
    target_date: Optional[date] = None,
    method_name: str = "ماليزيا (JAKIM)",
    madhab: str = "shafi",
    tz_name: Optional[str] = None,
    offsets: Optional[Dict[str, int]] = None,
) -> Optional[PrayerTimesResult]:
    lat_key = f"{latitude:.6f}"
    lon_key = f"{longitude:.6f}"

    if target_date is None:
        if tz_name:
            tz = _resolve_timezone(tz_name, longitude)
            target_date = datetime.now(tz).date()
        else:
            target_date = date.today()

    offsets_tuple = ()
    if offsets:
        offsets_key = tuple(sorted(offsets.items()))
        with _OFFSETS_LOCK:
            offsets_tuple = _OFFSETS_CACHE.get(offsets_key, offsets_key)
            if offsets_key not in _OFFSETS_CACHE:
                _OFFSETS_CACHE[offsets_key] = offsets_key
                if len(_OFFSETS_CACHE) > 32:
                    _OFFSETS_CACHE.pop(next(iter(_OFFSETS_CACHE)))

    return _calculate_cached(
        lat_key,
        lon_key,
        target_date.isoformat(),
        method_name,
        madhab,
        tz_name,
        offsets_tuple,
    )
