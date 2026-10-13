"""
Auto-location via IP geolocation.
Uses ip-api.com with HTTPS, retry, and fallback.
"""

import json
import logging
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

COUNTRY_TZ = {
    "Tunisia": "Africa/Tunis",
    "تونس": "Africa/Tunis",
    "Egypt": "Africa/Cairo",
    "مصر": "Africa/Cairo",
    "Saudi Arabia": "Asia/Riyadh",
    "السعودية": "Asia/Riyadh",
    "Algeria": "Africa/Algiers",
    "الجزائر": "Africa/Algiers",
    "Morocco": "Africa/Casablanca",
    "المغرب": "Africa/Casablanca",
    "Libya": "Africa/Tripoli",
    "ليبيا": "Africa/Tripoli",
    "Turkey": "Europe/Istanbul",
    "تركيا": "Europe/Istanbul",
    "France": "Europe/Paris",
    "فرنسا": "Europe/Paris",
    "Germany": "Europe/Berlin",
    "ألمانيا": "Europe/Berlin",
    "United Kingdom": "Europe/London",
    "US": "America/New_York",
    "Canada": "America/Toronto",
    "Qatar": "Asia/Qatar",
    "قطر": "Asia/Qatar",
    "UAE": "Asia/Dubai",
    "الإمارات": "Asia/Dubai",
    "Kuwait": "Asia/Kuwait",
    "الكويت": "Asia/Kuwait",
    "Oman": "Asia/Muscat",
    "عمان": "Asia/Muscat",
    "Bahrain": "Asia/Bahrain",
    "البحرين": "Asia/Bahrain",
    "Iraq": "Asia/Baghdad",
    "العراق": "Asia/Baghdad",
    "Jordan": "Asia/Amman",
    "الأردن": "Asia/Amman",
    "Lebanon": "Asia/Beirut",
    "لبنان": "Asia/Beirut",
    "Syria": "Asia/Damascus",
    "سوريا": "Asia/Damascus",
    "Palestine": "Asia/Gaza",
    "فلسطين": "Asia/Gaza",
    "Yemen": "Asia/Aden",
    "اليمن": "Asia/Aden",
    "Sudan": "Africa/Khartoum",
    "السودان": "Africa/Khartoum",
    "Malaysia": "Asia/Kuala_Lumpur",
    "Indonesia": "Asia/Jakarta",
    "Pakistan": "Asia/Karachi",
    "India": "Asia/Kolkata",
    "Bangladesh": "Asia/Dhaka",
    "Iran": "Asia/Tehran",
    "إيران": "Asia/Tehran",
}

_COUNTRY_REV: dict | None = None


def _country_code(english_name: str) -> str:
    global _COUNTRY_REV
    if _COUNTRY_REV is None:
        from .countries_data import COUNTRIES

        _COUNTRY_REV = {v: k for k, v in COUNTRIES.items()}
    return _COUNTRY_REV.get(english_name, "")


def clear_country_rev_cache():
    global _COUNTRY_REV
    _COUNTRY_REV = None


def detect() -> dict | None:
    """Detect location via IP geolocation (HTTPS, with fallback).
    Warning: This is a blocking call that can take up to 30s.
    Prefer detect_async() for non-blocking operation.
    """
    return _detect_sync()


def _detect_sync(retries: int = 1) -> dict | None:
    result = _try_ip_api(retries)
    if result:
        return result
    result = _try_fallback()
    if result:
        return result
    return _try_ipinfo()


def _try_ip_api(retries: int) -> dict | None:
    for attempt in range(retries + 1):
        try:
            req = Request(
                "https://ip-api.com/json/", headers={"User-Agent": "AthanFiveTimes/0.3.3b"}
            )
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data.get("status") == "success":
                city = data.get("city", "")
                country = data.get("country", "")
                tz = data.get("timezone", "") or COUNTRY_TZ.get(country, "")
                lat = data.get("lat", 0.0)
                lon = data.get("lon", 0.0)
                if lat == 0.0 and lon == 0.0:
                    logger.warning("Invalid coordinates from IP API")
                    if attempt < retries:
                        time.sleep(2)
                        continue
                    return None
                return {
                    "city": city,
                    "country": country,
                    "country_code": _country_code(country),
                    "latitude": lat,
                    "longitude": lon,
                    "timezone": tz,
                }
        except (URLError, ValueError, AttributeError, KeyError, OSError):
            logger.warning("IP geolocation attempt %d failed", attempt + 1)
            if attempt < retries:
                time.sleep(2)
    return None


def _try_fallback() -> dict | None:
    """Fallback using ipapi.co (HTTPS)."""
    try:
        req = Request("https://ipapi.co/json/", headers={"User-Agent": "AthanFiveTimes/0.3.3b"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("error"):
            return None
        country = data.get("country_name", "")
        try:
            lat, lon = float(data.get("latitude", 0.0)), float(data.get("longitude", 0.0))
        except (ValueError, TypeError):
            return None
        if (lat == 0.0 and lon == 0.0) or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None
        return {
            "city": data.get("city", ""),
            "country": country,
            "country_code": data.get("country_code", "").upper(),
            "latitude": lat,
            "longitude": lon,
            "timezone": data.get("timezone", ""),
        }
    except (URLError, ValueError, AttributeError, KeyError, OSError) as exc:
        logger.warning("Fallback geolocation failed: %s", exc)
    return None


def _try_ipinfo() -> dict | None:
    """Third provider (ipinfo.io, HTTPS, keyless basic tier)."""
    try:
        req = Request(
            "https://ipinfo.io/json",
            headers={"User-Agent": "AthanFiveTimes/0.3.3b"},
        )
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        code = (data.get("country") or "").upper()
        try:
            lat_s, _, lon_s = data.get("loc", "").partition(",")
            lat, lon = float(lat_s), float(lon_s)
        except (ValueError, TypeError, AttributeError):
            return None
        if (lat == 0.0 and lon == 0.0) or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None
        return {
            "city": data.get("city", ""),
            "country": "",
            "country_code": code,
            "latitude": lat,
            "longitude": lon,
            "timezone": data.get("timezone", ""),
        }
    except (URLError, ValueError, AttributeError, KeyError, OSError) as exc:
        logger.warning("ipinfo geolocation failed: %s", exc)
    return None


_detect_lock = threading.Lock()
_detect_running = False


def detect_async(callback) -> None:
    """Non-blocking location detection with callback (daemon thread)."""
    global _detect_running
    with _detect_lock:
        if _detect_running:
            logger.debug("Location detection already in progress, skipping")
            return
        _detect_running = True

    def _worker():
        global _detect_running
        try:
            result = _detect_sync()
            try:
                callback(result)
            except (RuntimeError, ValueError, AttributeError) as exc:
                logger.warning("Location callback failed: %s", exc)
        finally:
            with _detect_lock:
                _detect_running = False

    threading.Thread(target=_worker, daemon=True).start()
