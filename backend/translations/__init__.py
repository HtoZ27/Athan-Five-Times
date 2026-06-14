"""
Translation manager — loads language files from JSON and provides lookup.
"""

import json
import logging
import os
from functools import lru_cache
logger = logging.getLogger(__name__)

_PACKAGE_DIR = os.path.dirname(os.path.dirname(__file__))
_LANG_DIR = os.path.join(_PACKAGE_DIR, "translations")

_CURRENT: dict = {}
_CURRENT_CODE: str = "ar"
_FALLBACK_CACHE: dict | None = None

from .._constants import LANGS
FALLBACK = "ar"


@lru_cache(maxsize=len(LANGS))
def _load_file(code: str) -> dict:
    path = os.path.join(_LANG_DIR, f"{code}.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return {}


def _get_fallback() -> dict:
    global _FALLBACK_CACHE
    if _FALLBACK_CACHE is None:
        _FALLBACK_CACHE = _load_file(FALLBACK)
    return _FALLBACK_CACHE


def current_code() -> str:
    return _CURRENT_CODE


def load(code: str):
    global _CURRENT, _CURRENT_CODE
    _CURRENT = _load_file(code)
    _CURRENT_CODE = code if _CURRENT else FALLBACK
    if not _CURRENT:
        _CURRENT = _load_file(FALLBACK)


def _get_dict() -> dict:
    return _CURRENT if _CURRENT else _get_fallback()


def u(key: str, **kwargs: str) -> str:
    """Look up a UI string in the current language."""
    d = _get_dict().get("ui", {})
    val = d.get(key)
    if val is None:
        fallback = _get_fallback().get("ui", {}).get(key)
        val = fallback if fallback is not None else key
    if kwargs:
        try:
            val = val.format(**kwargs)
        except KeyError as e:
            logger.warning("Missing format key %s for '%s'", e, key)
    return val


def prayer_name(key: str) -> str:
    """Look up a prayer name in the current language."""
    d = _get_dict().get("prayer_names", {})
    val = d.get(key)
    if val is None:
        val = _get_fallback().get("prayer_names", {}).get(key, key)
    return val


def get_athkar(prayer_key: str) -> list[str]:
    """Return athkar list for a given prayer/morning/evening key."""
    d = _get_dict().get("athkar", {})
    val = d.get(prayer_key)
    if val is None:
        val = _get_fallback().get("athkar", {}).get(prayer_key, [])
    return list(val)


def credits_html() -> str:
    """Return the credits/about HTML for the current language."""
    d = _get_dict().get("credits", {})
    html = d.get("html")
    if not html:
        html = _get_fallback().get("credits", {}).get("html", "")
    return html


def credits_title() -> str:
    """Return the credits/about dialog title."""
    d = _get_dict().get("credits", {})
    title = d.get("title")
    if not title:
        title = _get_fallback().get("credits", {}).get("title", "")
    return title


# ── Date formatting with localization ────────────────────────────────

def _calendar(key: str, default: list | None = None) -> list:
    d = _get_dict().get("calendar", {})
    val = d.get(key)
    if not val:
        val = _get_fallback().get("calendar", {}).get(key, default or [])
    return list(val)


def day_name(weekday: int) -> str:
    """0=Monday … 6=Sunday → localized day name."""
    names = _calendar("days")
    # Python weekday: Mon=0 … Sun=6 → Islamic: Sun=0 … Sat=6
    idx = (weekday + 1) % 7
    return names[idx] if idx < len(names) else ""


def greg_month_name(month: int) -> str:
    """1=January … 12=December → localized month name."""
    names = _calendar("months_gregorian")
    return names[month - 1] if 1 <= month <= len(names) else ""


def hijri_month_name(month: int) -> str:
    """1=Muharram … 12=Dhu al-Hijjah → localized Hijri month name."""
    names = _calendar("months_hijri")
    return names[month - 1] if 1 <= month <= len(names) else ""


# ── Country / City name lookup ────────────────────────────────────────

def country_name(code: str) -> str:
    """Return the translated name of a country (ISO code)."""
    return _country_name_cached(code, current_code())


@lru_cache(maxsize=512)
def _country_name_cached(code: str, _lang: str) -> str:
    d = _get_dict().get("countries", {})
    val = d.get(code)
    if val is None:
        val = _get_fallback().get("countries", {}).get(code)
    if val is None:
        try:
            from ..countries_data import COUNTRIES
            val = COUNTRIES.get(code, code)
        except Exception:
            val = code
    return val


def city_name(name: str) -> str:
    """Return the translated name of a city (English key)."""
    return _city_name_cached(name, current_code())


@lru_cache(maxsize=512)
def _city_name_cached(name: str, _lang: str) -> str:
    d = _get_dict().get("cities", {})
    val = d.get(name)
    if val is None:
        val = _get_fallback().get("cities", {}).get(name)
    if val is None:
        val = name
    return val


def format_date(d: "date", offset_days: int = 0) -> tuple[str, str]:
    """Return (gregorian_line, hijri_line) localized to current language."""
    from ..hijri import gregorian_to_hijri
    wd = day_name(d.weekday())
    greg = f"{wd}، {d.day} {greg_month_name(d.month)} {d.year}"
    y, m, day_ = gregorian_to_hijri(d, offset_days)
    hijri = f"{day_} {hijri_month_name(m)} {y} هـ"
    return greg, hijri
