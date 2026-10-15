"""
Translation manager — loads language files from JSON and provides lookup.
"""

import json
import logging
import os
from datetime import date
from functools import lru_cache

logger = logging.getLogger(__name__)

_PACKAGE_DIR = os.path.dirname(os.path.dirname(__file__))
_LANG_DIR = os.path.join(_PACKAGE_DIR, "translations")

_CURRENT: dict = {}
_CURRENT_CODE: str = "ar"
_FALLBACK_CACHE: dict | None = None
_EN_CACHE: dict | None = None

FALLBACK = "ar"


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
        if _CURRENT_CODE != FALLBACK:
            _FALLBACK_CACHE.pop("cities", None)
    return _FALLBACK_CACHE


def _get_english() -> dict:
    """English strings as last-resort fallback for non-Arabic UI.

    Keys missing from both the current language and Arabic (e.g. newly
    added settings labels) render in English instead of Arabic text.
    """
    global _EN_CACHE
    if _EN_CACHE is None:
        _EN_CACHE = _load_file("en")
    return _EN_CACHE


def current_code() -> str:
    return _CURRENT_CODE


def load(code: str):
    global _CURRENT, _CURRENT_CODE, _FALLBACK_CACHE
    _CURRENT = _load_file(code)
    _CURRENT_CODE = code if _CURRENT else FALLBACK
    if not _CURRENT:
        _CURRENT = _load_file(FALLBACK)
    if _CURRENT_CODE == FALLBACK:
        _FALLBACK_CACHE = _CURRENT
    elif _FALLBACK_CACHE is not None and "cities" in _FALLBACK_CACHE:
        _FALLBACK_CACHE.pop("cities")


def _get_dict() -> dict:
    return _CURRENT if _CURRENT else _get_fallback()


def u(key: str, **kwargs: str) -> str:
    """Look up a UI string in the current language."""
    d = _get_dict().get("ui", {})
    val = d.get(key)
    if val is None:
        val = _get_fallback().get("ui", {}).get(key)
    if val is None and _CURRENT_CODE not in (FALLBACK, "en"):
        val = _get_english().get("ui", {}).get(key)
    if val is None:
        val = key
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
    """Return athkar list for a given prayer/morning/evening key.

    Compat layer over the structured library (backend/adhkar_repo.py):
    same list[str] shape as before, sourced from assets/adhkar/ so the
    flat per-language copies can be deleted without breaking callers.
    """
    try:
        from ..adhkar_repo import get_structured_texts

        texts = get_structured_texts(prayer_key)
        if texts:
            return texts
    except Exception as exc:
        logger.warning("Adhkar library fallback for %s: %s", prayer_key, exc)
    d = _get_dict().get("athkar", {})
    val = d.get(prayer_key)
    if val is None:
        val = _get_fallback().get("athkar", {}).get(prayer_key, [])
    if isinstance(val, str):
        val = [val]
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


def _calendar(key: str, default: list | None = None) -> list:
    d = _get_dict().get("calendar", {})
    val = d.get(key)
    if not val:
        val = _get_fallback().get("calendar", {}).get(key, default or [])
    return list(val)


def day_name(weekday: int) -> str:
    """0=Monday … 6=Sunday → localized day name."""
    names = _calendar("days")
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


def country_name(code: str) -> str:
    """Return the translated name of a country (ISO code)."""
    return _country_name_cached(code, current_code())


@lru_cache(maxsize=4199)
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


def calc_method_name(key: str) -> str:
    """Return the translated display name of a calculation method."""
    d = _get_dict().get("calc_methods", {})
    val = d.get(key)
    if val is None:
        val = _get_fallback().get("calc_methods", {}).get(key, key)
    return val


def city_name(name: str) -> str:
    """Return the translated name of a city (English key).

    City translations are only stored in ar.json. For non-Arabic languages
    the English name itself is returned, avoiding ~3.7 MB of duplicated data
    in every translation file.
    """
    return _city_name_cached(name, current_code())


@lru_cache(maxsize=8192)
def _city_name_cached(name: str, _lang: str) -> str:
    if _lang == FALLBACK:
        d = _get_dict().get("cities", {})
        return d.get(name, name)
    return name


def theme_name(key: str) -> str:
    """Return the translated display name of a theme code."""
    d = _get_dict().get("themes", {})
    val = d.get(key)
    if val is None:
        val = _get_fallback().get("themes", {}).get(key, key)
    return val


def madhab_name(key: str) -> str:
    """Return the translated display name of a madhab."""
    d = _get_dict().get("madhab", {})
    val = d.get(key)
    if val is None:
        val = _get_fallback().get("madhab", {}).get(key, key)
    return val


def timezone_name(code: str, display: str) -> str:
    """Return the translated timezone display name."""
    d = _get_dict().get("timezones", {})
    val = d.get(code)
    if val is None:
        val = _get_fallback().get("timezones", {}).get(code, display)
    return val


def format_date(d: "date", offset_days: int = 0) -> tuple[str, str]:
    """Return (gregorian_line, hijri_line) localized to current language."""
    from ..hijri import gregorian_to_hijri

    wd = day_name(d.weekday())
    greg = f"{wd}، {d.day} {greg_month_name(d.month)} {d.year}"
    y, m, day_ = gregorian_to_hijri(d, offset_days)
    hijri = f"{day_} {hijri_month_name(m)} {y} هـ"
    return greg, hijri
