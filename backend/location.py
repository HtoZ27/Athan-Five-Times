"""
Auto-location via IP geolocation.
Uses ip-api.com (plain HTTP: the free tier rejects HTTPS), retry, and fallback.
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

# Disk cache for auto-detected location (ported from original prayer_app:
# 24h TTL under XDG_CACHE_HOME/prayer-times/location.json). Avoids hitting
# the network on every cold start and works offline while fresh.
_CACHE_TTL = 86400


def _cache_file() -> Path:
    return Path(
        os.environ.get("XDG_CACHE_HOME", Path("~/.cache").expanduser()),
        "prayer-times",
        "location.json",
    )


def _get_cached_location() -> dict | None:
    """Return cached auto-location if fresher than _CACHE_TTL, else None."""
    try:
        cache = _cache_file()
        if cache.is_file():
            with cache.open(encoding="utf-8") as f:
                payload = json.load(f)
            if (
                isinstance(payload, dict)
                and time.time() - float(payload.get("timestamp", 0)) < _CACHE_TTL
                and isinstance(payload.get("data"), dict)
            ):
                return payload["data"]
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        logger.debug("Failed to read cached location: %s", exc)
    return None


def _save_location_cache(data: dict) -> None:
    """Persist a successful auto-detection result to disk."""
    try:
        cache = _cache_file()
        cache.parent.mkdir(parents=True, exist_ok=True)
        with cache.open("w", encoding="utf-8") as f:
            json.dump({"timestamp": time.time(), "data": data}, f)
    except (OSError, ValueError, TypeError) as exc:
        logger.debug("Failed to save location cache: %s", exc)


def clear_location_cache() -> None:
    """Drop the cached auto-location (call on manual city/country change)."""
    try:
        _cache_file().unlink(missing_ok=True)
    except OSError as exc:
        logger.debug("Failed to clear location cache: %s", exc)


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
    cached = _get_cached_location()
    if cached:
        logger.info("Using cached auto-location")
        return cached
    result = _try_ip_api(retries)
    if result:
        _save_location_cache(result)
        return result
    result = _try_fallback()
    if result:
        _save_location_cache(result)
        return result
    result = _try_ipinfo()
    if result:
        _save_location_cache(result)
        return result
    result = _try_ipwho()
    if result:
        _save_location_cache(result)
        return result
    result = _try_geojs()
    if result:
        _save_location_cache(result)
    return result


def _try_ip_api(retries: int) -> dict | None:
    for attempt in range(retries + 1):
        try:
            req = Request(
                "http://ip-api.com/json/", headers={"User-Agent": "AthanFiveTimes/0.3.16b"}
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
        req = Request("https://ipapi.co/json/", headers={"User-Agent": "AthanFiveTimes/0.3.16b"})
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
            headers={"User-Agent": "AthanFiveTimes/0.3.16b"},
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


def _try_ipwho() -> dict | None:
    """Fourth provider (ipwho.is, HTTPS, keyless, generous free tier)."""
    try:
        req = Request(
            "https://ipwho.is/",
            headers={"User-Agent": "AthanFiveTimes/0.3.16b"},
        )
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if not data.get("success"):
            return None
        country = data.get("country", "")
        try:
            lat, lon = float(data.get("latitude", 0.0)), float(data.get("longitude", 0.0))
        except (ValueError, TypeError):
            return None
        if (lat == 0.0 and lon == 0.0) or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None
        tz = data.get("timezone", "")
        if isinstance(tz, dict):
            tz = tz.get("id", "")
        return {
            "city": data.get("city", ""),
            "country": country,
            "country_code": (data.get("country_code") or "").upper(),
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
        }
    except (URLError, ValueError, AttributeError, KeyError, OSError) as exc:
        logger.warning("ipwho geolocation failed: %s", exc)
    return None


def _try_geojs() -> dict | None:
    """Fifth provider (geojs.io, HTTPS, keyless)."""
    try:
        req = Request(
            "https://get.geojs.io/v1/ip/geo.json",
            headers={"User-Agent": "AthanFiveTimes/0.3.16b"},
        )
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        code = (data.get("country_code") or "").upper()
        if not code:
            return None
        try:
            lat, lon = float(data.get("latitude", 0.0)), float(data.get("longitude", 0.0))
        except (ValueError, TypeError):
            return None
        if (lat == 0.0 and lon == 0.0) or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None
        return {
            "city": data.get("city", ""),
            "country": data.get("country", ""),
            "country_code": code,
            "latitude": lat,
            "longitude": lon,
            "timezone": data.get("timezone", ""),
        }
    except (URLError, ValueError, AttributeError, KeyError, OSError) as exc:
        logger.warning("geojs geolocation failed: %s", exc)
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
