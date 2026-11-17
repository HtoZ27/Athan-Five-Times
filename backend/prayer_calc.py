"""Prayer time calculation.

The engine is a faithful port of the reference "الوقت الدقيق" (Salati)
implementation, which is itself a port of PrayTimes.js with an 11-slot
per-method parameter table.  Keeping the same formulas, offsets, rounding
and high-latitude rules is what makes the output agree with the reference
application minute by minute.

The public API (``calculate`` / ``PrayerTimesResult``) is unchanged; the
only additions are the optional ``city_name``, ``country_code`` and
``altitude`` arguments used to apply the reference's official city tables.
"""

import functools
import logging
import math
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 11-slot method table, copied from the reference parameter map.
# Slots:
#   0 fajr angle
#   1 maghrib mode (1 = minutes after sunset, 0 = angle)
#   2 maghrib value (minutes or degrees)
#   3 isha mode (1 = minutes after maghrib, 0 = angle)
#   4 isha value (minutes or degrees)
#   5 fajr adjustment (minutes)
#   6 sunrise adjustment (minutes)
#   7 dhuhr adjustment (minutes)
#   8 asr adjustment (minutes)
#   9 maghrib adjustment (minutes)
#  10 isha adjustment (minutes)
_METHOD_PARAMS: Dict[str, Tuple[float, ...]] = {
    "mwl": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "jafari": (16, 0, 4, 0, 14, 0, 0, 0, 0, 0, 0),
    "custom": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "none": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "morocco": (19.09, 0, 0, 0, 17, 0, -2, 5, 0, 3, 0),
    "azrou": (19.1, 0, 0, 0, 17, 0, -1, 5, 0, 1, 0),
    "algeria": (18, 1, 3, 0, 17, 0, 0, 0, 0, 0, 0),
    "sudan": (18.12, 0, 0, 0, 17.88, 0, 3, 3, 0, -4, 0),
    "makkah": (18.5, 1, 0, 1, 90, 0, 0, 0, 0, 0, 0),
    "egypt": (19.5, 1, 0, 0, 17.5, 0, 0, 0, 0, 0, 0),
    "karachi": (18, 1, 0, 0, 18, 0, 0, 0, 0, 0, 0),
    "tehran": (17.7, 0, 4.5, 0, 14, 0, 0, 0, 0, 0, 0),
    "tunisia": (18, 1, 1, 0, 18, -1, 0, 7, 0, 0, 1),
    "turkey": (18, 0, 0, 0, 16.93, 0, -6, 6, 4, 5, 0),
    "malaysia": (20, 1, 0, 0, 18, 0, 0, 1, 0, 0, 0),
    "malaysia2": (20, 1, 0, 0, 18.46, 0, 0, 3, 2, 1, 0),
    "indonesia": (20, 1, 0, 0, 18, 2, -2, 2, 2, 2, 2),
    "palestine": (20.11, 0, 0, 0, 17.9, 0, -5, 0, 0, 4, 0),
    "oman": (18, 1, 5, 0, 18, 0, 0, 5, 5, 0, 1),
    "omanMuscat": (17.74, 0, 0, 0, 18.229, 0, 1, 6, 6, 6, 0),
    "kazakhstan": (14.97, 0, 0, 0, 14.96, 0, 0, 5, 5, 0, 0),
    "tajikistan": (18, 1, 0, 0, 18, 0, 0, 0, 0, 0, 0),
    "emirates": (18.5, 1, 2, 0, 18.5, 1, -4, 2, 0, 0, -3),
    "jordan": (18.12, 0, 0, 0, 17.975, 0, 0, 0, 0, 1, 0),
    "kuwait": (18, 1, 0, 0, 17.5, 0, 0, 0, 0, 0, 0),
    "qatar": (18, 1, 0, 1, 90, 0, 0, 0, 0, 2, 0),
    "libya": (18.3, 0, 0, 0, 18.35, 0, 0, 4, 0, 4, 0),
    "syria": (19.5, 1, 0, 0, 17.5, 0, 0, 0, 0, 0, 0),
    "iraq": (18, 0, 0, 0, 17, 0, 0, 5, 3, 2, 0),
    "maldives": (19, 1, 0, 0, 19, 0, -1, 4, 1, 1, 1),
    "moscow": (16, 0, 0, 0, 15.1, 0, 0, 1, 1, 1, 2),
    "blackburn": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "london": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "birmingham": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "aachen": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "munchen": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "potsdam": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "nurnberg": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "austria": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "belgium": (18, 0, 0, 0, 18, 0, 0, 0, 0, 0, 0),
    "luxembourg": (18, 1, 0, 0, 17, 0, 0, 0, 0, 0, 0),
    "czech": (12.04, 0, 0, 0, 12.04, 0, 0, 5, 0, -2, 0),
    "switzerland": (17.99, 0, 0, 1, 100, 1, 4, 0, 0, -4, 0),
    "fribourg": (18.01, 0, 0, 1, 100, 1, 5, 0, 0, -5, 0),
    "uoif": (12, 1, 0, 0, 12, -5, 0, 5, 0, 4, 5),
    "paris": (12, 1, 0, 0, 12, -5, 0, 5, 0, 4, 5),
    "toulouse": (12, 1, 0, 0, 12, -5, 0, 5, 0, 4, 5),
    "lyon": (12, 1, 0, 0, 12, -5, 0, 5, 0, 4, 5),
    "orleans": (15, 0, 0, 0, 12.34, 0, 0, 5, 0, 0, 0),
    "isna": (15, 1, 0, 0, 15, 0, 0, 0, 0, 0, 0),
    "montreal": (15, 1, 0, 0, 15, 0, 0, 0, 0, 0, 0),
    "windsor": (15, 1, 0, 0, 15, 0, 0, 0, 0, 0, 0),
    "calgary": (15, 1, 0, 0, 15, 0, 0, 0, 0, 0, 0),
    "mississauga": (15, 1, 0, 0, 15, 0, 0, 0, 0, 0, 0),
    "southkorea": (18, 1, 0, 0, 18, 1, -1, 0, 0, 0, -6),
    "rotterdam": (15, 1, 0, 0, 15, 0, 0, 0, 0, 0, 0),
    "dordrecht": (15, 1, 0, 0, 15, 0, 0, 0, 0, 0, 0),
    "eindhoven": (15, 1, 0, 0, 15, 0, 0, 0, 0, 0, 0),
}

# Arabic (localized) method names -> reference parameter key.
_METHOD_KEYS: Dict[str, str] = {
    "رابطة العالم الإسلامي (MWL)": "mwl",
    "أم القرى (Umm Al-Qura)": "makkah",
    "الهيئة المصرية للمساحة": "egypt",
    "جامعة العلوم الإسلامية كراتشي": "karachi",
    "الجمعية الإسلامية لأمريكا الشمالية (ISNA)": "isna",
    "طهران": "tehran",
    "إندونيسيا (وزارة الشؤون الدينية)": "indonesia",
    "ماليزيا (JAKIM)": "malaysia2",
    "جنوب شرق آسيا (JAKIM)": "malaysia",
    "سنغافورة (MUIS)": "malaysia",
    "وزارة الشؤون الدينية التونسية": "tunisia",
    "الجزائر": "algeria",
    "المغرب": "morocco",
    "ليبيا": "libya",
    "موريتانيا": "egypt",
    "السودان": "sudan",
    "سوريا (وزارة الأوقاف)": "syria",
    "العراق": "iraq",
    "فلسطين (وزارة الأوقاف)": "palestine",
    "ديانة تركيا (Diyanet)": "turkey",
    "روسيا (اتحاد المسلمين)": "moscow",
    "اتحاد المنظمات الإسلامية في فرنسا (UOIF)": "uoif",
    "الهيئة العامة للشؤون الإسلامية (الإمارات)": "emirates",
    "وزارة الأوقاف القطرية": "qatar",
    "وزارة الأوقاف الكويتية": "kuwait",
    "اليمن": "makkah",
    "مخصص": "custom",
    # Additional reference presets used by the country table.
    "الأردن (وزارة الأوقاف)": "jordan",
    "كازاخستان": "kazakhstan",
    "سلطنة عمان": "oman",
    "جزر المالديف": "maldives",
    "بلجيكا": "belgium",
    "سويسرا": "switzerland",
    "التشيك": "czech",
    "كوريا الجنوبية": "southkorea",
    "لوكسمبورغ": "luxembourg",
}

# Legacy English aliases (old settings files and programmatic callers).
_METHOD_ALIASES: Dict[str, str] = {
    "Tunisia": "وزارة الشؤون الدينية التونسية",
    "Algeria": "الجزائر",
    "Morocco": "المغرب",
    "Libya": "ليبيا",
    "Sudan": "السودان",
    "Syria": "سوريا (وزارة الأوقاف)",
    "Iraq": "العراق",
    "Palestine": "فلسطين (وزارة الأوقاف)",
    "Turkey": "ديانة تركيا (Diyanet)",
    "Russia": "روسيا (اتحاد المسلمين)",
    "France": "اتحاد المنظمات الإسلامية في فرنسا (UOIF)",
    "Emirates": "الهيئة العامة للشؤون الإسلامية (الإمارات)",
    "Qatar": "وزارة الأوقاف القطرية",
    "Kuwait": "وزارة الأوقاف الكويتية",
    "Yemen": "اليمن",
    "Jordan": "الأردن (وزارة الأوقاف)",
    "Kazakhstan": "كازاخستان",
    "Oman": "سلطنة عمان",
    "Maldives": "جزر المالديف",
    "Belgium": "بلجيكا",
    "Switzerland": "سويسرا",
    "Czechia": "التشيك",
    "South Korea": "كوريا الجنوبية",
    "Luxembourg": "لوكسمبورغ",
    "Mauritania": "موريتانيا",
}

# Methods whose default high-latitude rule is "middle of the night".
_MIDNIGHT_METHODS = frozenset({"uoif", "moscow"})

# Methods/countries for which the reference applies the altitude correction
# to sunrise and sunset.
_ALTITUDE_METHODS = frozenset(
    {
        "iraq",
        "morocco",
        "tunisia",
        "jordan",
        "orleans",
        "sudan",
        "belgium",
        "kazakhstan",
        "palestine",
        "czech",
        "switzerland",
    }
)
_ALTITUDE_COUNTRIES = frozenset({"PS", "IL", "CZ", "CH"})

_CALCULATION_METHODS: dict | None = None
_COUNTRY_DATA: tuple | None = None
_OFFSETS_CACHE: dict[int, tuple] = {}
_OFFSETS_LOCK = threading.Lock()

PRAYER_ORDER: list = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
OFFSET_KEYS = {"fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"}
SUNRISE_ANGLE = 0.833


def _method_spec(key: str) -> dict:
    p = _METHOD_PARAMS[key]
    spec = {
        "key": key,
        "params": p,
        "fajr_angle": p[0],
        "fajr_offset": p[5],
        "sunrise_offset": p[6],
        "dhuhr_offset": p[7],
        "asr_offset": p[8],
        "maghrib_offset": p[9],
        "isha_offset": p[10],
        "high_lats": "middle_of_night" if key in _MIDNIGHT_METHODS else "angle_based",
    }
    if p[1] == 1:
        spec["maghrib_interval"] = p[2]
    else:
        spec["maghrib_angle"] = p[2]
    if p[3] == 1:
        spec["isha_interval"] = p[4]
    else:
        spec["isha_angle"] = p[4]
    return spec


def _get_calc_methods() -> Dict[str, dict]:
    global _CALCULATION_METHODS
    if _CALCULATION_METHODS is None:
        _CALCULATION_METHODS = {name: _method_spec(key) for name, key in _METHOD_KEYS.items()}
    return _CALCULATION_METHODS


def _get_method_key(method_name: str) -> str | None:
    name = _METHOD_ALIASES.get(method_name, method_name)
    return _METHOD_KEYS.get(name)


def _get_methods_for(name: str) -> dict | None:
    return _get_calc_methods().get(name)


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


# ---------------------------------------------------------------------------
# PrayTimes-compatible solar engine
# ---------------------------------------------------------------------------

_DEG = math.pi / 180.0


def _sin(deg: float) -> float:
    return math.sin(deg * _DEG)


def _cos(deg: float) -> float:
    return math.cos(deg * _DEG)


def _tan(deg: float) -> float:
    return math.tan(deg * _DEG)


def _asin(x: float) -> float:
    return math.degrees(math.asin(x)) if -1.0 <= x <= 1.0 else float("nan")


def _acos(x: float) -> float:
    return math.degrees(math.acos(x)) if -1.0 <= x <= 1.0 else float("nan")


def _acot(x: float) -> float:
    return math.degrees(math.atan2(1.0, x))


def _fix_angle(angle: float) -> float:
    return angle - 360.0 * math.floor(angle / 360.0)


def _fix_hour(hour: float) -> float:
    return hour - 24.0 * math.floor(hour / 24.0)


def _julian_date(year: int, month: int, day: int) -> float:
    if month <= 2:
        year -= 1
        month += 12
    fl = math.floor(year / 100.0)
    return (
        math.floor((year + 4716) * 365.25)
        + math.floor((month + 1) * 30.6001)
        + day
        + (2 - fl + math.floor(fl / 4.0))
        - 1524.5
    )


def _sun_position(julian: float) -> tuple[float, float]:
    """Return (declination, equation of time) for a Julian date.

    Both values are in degrees/hours respectively, matching the reference
    implementation (``m6.a.q``).
    """
    d = julian - 2451545.0
    g = _fix_angle(357.529 + 0.98560028 * d)
    q = _fix_angle(280.459 + 0.98564736 * d)
    sun_lon = _fix_angle(q + 1.915 * _sin(g) + 0.02 * _sin(2 * g))
    e = 23.439 - 0.00000036 * d
    declination = _asin(_sin(e) * _sin(sun_lon))
    right_ascension = math.degrees(math.atan2(_cos(e) * _sin(sun_lon), _cos(sun_lon))) / 15.0
    equation = q / 15.0 - _fix_hour(right_ascension)
    return declination, equation


class _SolarEngine:
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        self.julian = 0.0

    def mid_day(self, portion: float) -> float:
        return _fix_hour(12.0 - _sun_position(self.julian + portion)[1])

    def sun_angle_time(self, angle: float, portion: float) -> float:
        declination = _sun_position(self.julian + portion)[0]
        noon = self.mid_day(portion)
        numerator = -_sin(angle) - _sin(declination) * _sin(self.latitude)
        denominator = _cos(declination) * _cos(self.latitude)
        if denominator == 0:
            return float("nan")
        offset = _acos(numerator / denominator) / 15.0
        if angle > 90:
            offset = -offset
        return noon + offset

    def asr_time(self, factor: float, portion: float) -> float:
        declination = _sun_position(self.julian + portion)[0]
        angle = -_acot(factor + _tan(abs(self.latitude - declination)))
        return self.sun_angle_time(angle, portion)


def _high_lat_fraction(rule: str, angle: float) -> float:
    if rule == "middle_of_night":
        return 0.5
    if rule == "one_seventh":
        return 0.14286
    if rule == "angle_based":
        return angle / 60.0
    return 0.0


def _compute_raw(
    latitude: float,
    longitude: float,
    target_date: date,
    params: Tuple[float, ...],
    asr_factor: float,
    high_lats: str,
    altitude: float = 0.0,
    altitude_correction: bool = False,
) -> list[float]:
    """Return seven local-mean-solar times: fajr, sunrise, dhuhr, asr,
    sunset, maghrib, isha.  ``nan`` is returned for impossible sun angles.
    """
    engine = _SolarEngine(latitude, longitude)
    engine.julian = (
        _julian_date(target_date.year, target_date.month, target_date.day) - longitude / 360.0
    )
    p = params
    if altitude_correction and altitude > 0:
        rise_set_angle = 0.833 + 0.0347 * math.sqrt(altitude)
    else:
        rise_set_angle = 0.833
    portions = [
        5.0 / 24.0,
        6.0 / 24.0,
        12.0 / 24.0,
        13.0 / 24.0,
        18.0 / 24.0,
        18.0 / 24.0,
        18.0 / 24.0,
    ]
    fajr = engine.sun_angle_time(180.0 - p[0], portions[0])
    sunrise = engine.sun_angle_time(180.0 - rise_set_angle, portions[1])
    dhuhr = engine.mid_day(portions[2])
    asr = engine.asr_time(asr_factor, portions[3])
    sunset = engine.sun_angle_time(rise_set_angle, portions[4])
    isha_angle_time = engine.sun_angle_time(p[4], portions[6])

    fajr += p[5] / 60.0
    sunrise += p[6] / 60.0
    dhuhr += p[7] / 60.0
    asr += p[8] / 60.0
    maghrib = sunset + p[9] / 60.0
    if p[1] == 1:
        maghrib += p[2] / 60.0
    if p[3] == 1:
        isha = maghrib + p[4] / 60.0
    else:
        isha = isha_angle_time + p[10] / 60.0

    if high_lats != "none":
        # The reference computes the night from the already-tuned sunrise
        # and, when a clamp triggers, adds the fajr/isha tune once more.
        night = _fix_hour(sunrise - sunset)
        fajr_portion = _high_lat_fraction(high_lats, p[0]) * night
        if math.isnan(fajr) or _fix_hour(sunrise - fajr) > fajr_portion:
            fajr = sunrise - fajr_portion + p[5] / 60.0
        isha_angle = p[4] if p[3] == 0 else 18.0
        isha_portion = _high_lat_fraction(high_lats, isha_angle) * night
        if math.isnan(isha) or _fix_hour(isha - maghrib) > isha_portion:
            isha = maghrib + isha_portion + p[10] / 60.0

    return [fajr, sunrise, dhuhr, asr, sunset, maghrib, isha]


# ---------------------------------------------------------------------------
# Time zone helpers
# ---------------------------------------------------------------------------

_TIMEZONE_ALIASES = {
    "Asia/Jeddah": "Asia/Riyadh",
    "Asia/Abu_Dhabi": "Asia/Dubai",
    "Asia/Doha": "Asia/Qatar",
}


def _resolve_timezone(tz_name: str | None, longitude: float) -> timezone | None:
    if tz_name:
        tz_name = _TIMEZONE_ALIASES.get(tz_name, tz_name)
        try:
            from zoneinfo import ZoneInfo

            return ZoneInfo(tz_name)
        except (KeyError, OSError, TypeError):
            logger.warning("ZoneInfo not found for '%s', falling back to longitude offset", tz_name)
    hours = round(longitude / 15)
    return timezone(timedelta(hours=hours))


def _utc_hour_to_local_dt(
    utc_hour: float,
    target_date: date,
    tz: timezone | None,
) -> datetime:
    """Convert an absolute UTC hour to the displayed local minute.

    The reference adds 30 seconds to the solar time and then floors the
    hour and minute.  Doing that on the full-precision value (rather than
    rounding to the nearest second first) is what keeps the output
    identical minute by minute.
    """
    dt = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        tzinfo=timezone.utc,
    ) + timedelta(hours=utc_hour)
    if tz is not None:
        dt = dt.astimezone(tz)
    dt += timedelta(seconds=30)
    return dt.replace(second=0, microsecond=0, tzinfo=None)


# ---------------------------------------------------------------------------
# Public result object
# ---------------------------------------------------------------------------


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
        for name, when in self._ordered_prayers():
            if name == "sunrise":
                continue
            if when > now:
                return name, when
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


# ---------------------------------------------------------------------------
# Calculation
# ---------------------------------------------------------------------------


def _normalise_city(value: str | None) -> str:
    if not value:
        return ""
    import re
    import unicodedata

    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", stripped.lower())


@functools.lru_cache(maxsize=256)
def _calculate_cached(
    lat_key: str,
    lon_key: str,
    target_date_iso: str,
    method_name: str,
    madhab: str,
    tz_name: str | None,
    offsets_tuple: tuple,
    city_key: str = "",
    country_code: str = "",
    altitude: float = 0.0,
) -> Optional[PrayerTimesResult]:
    try:
        target_date = date.fromisoformat(target_date_iso)
        latitude = float(lat_key)
        longitude = float(lon_key)
        tz = _resolve_timezone(tz_name, longitude)

        static = None
        if city_key and country_code:
            try:
                from .prayer_static_tables import lookup

                static = lookup(country_code, city_key, target_date)
            except ImportError:  # pragma: no cover - optional data module
                static = None

        method_key = _get_method_key(method_name)
        if static is not None:
            method_key, _deltas, altitude = static
        if method_key is None:
            logger.warning("Unknown method '%s', falling back to أم القرى", method_name)
            method_key = "makkah"

        params = _METHOD_PARAMS[method_key]
        high_lats = "middle_of_night" if method_key in _MIDNIGHT_METHODS else "angle_based"
        altitude_correction = method_key in _ALTITUDE_METHODS or country_code in _ALTITUDE_COUNTRIES
        asr_factor = 2.0 if madhab == "hanafi" else 1.0

        raw = _compute_raw(
            latitude,
            longitude,
            target_date,
            params,
            asr_factor,
            high_lats,
            altitude=altitude,
            altitude_correction=altitude_correction,
        )
        if any(math.isnan(value) for value in raw):
            return None

        local = [_utc_hour_to_local_dt(value - longitude / 15.0, target_date, tz) for value in raw]
        # raw indices: 0 fajr, 1 sunrise, 2 dhuhr, 3 asr, 4 sunset, 5 maghrib, 6 isha
        times = {
            "fajr": local[0],
            "sunrise": local[1],
            "dhuhr": local[2],
            "asr": local[3],
            "maghrib": local[5],
            "isha": local[6],
        }

        if static is not None:
            deltas = static[1]
            for index, key in enumerate(PRAYER_ORDER):
                times[key] = times[key] + timedelta(minutes=deltas[index])

        result = PrayerTimesResult(
            fajr=times["fajr"],
            sunrise=times["sunrise"],
            dhuhr=times["dhuhr"],
            asr=times["asr"],
            maghrib=times["maghrib"],
            isha=times["isha"],
            calc_date=target_date,
        )

        offsets = dict(offsets_tuple) if offsets_tuple else {}
        if offsets:
            result = result.with_offsets(offsets)

        return result

    except (ImportError, ValueError, AttributeError, KeyError, TypeError, OverflowError):
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
    city_name: Optional[str] = None,
    country_code: Optional[str] = None,
    altitude: float = 0.0,
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
        _normalise_city(city_name),
        (country_code or "").upper(),
        float(altitude or 0.0),
    )
