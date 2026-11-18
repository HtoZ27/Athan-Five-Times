"""
Auto-location via IP geolocation.
Uses ip-api.com (plain HTTP: the free tier rejects HTTPS), retry, and fallback.
"""

import json
import logging
import math
import os
import re
import threading
import time

try:
    import pytz

    _PYTZ_AVAILABLE = True
except Exception:
    pytz = None
    _PYTZ_AVAILABLE = False
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


def _parse_zone_coord(token: str) -> tuple[float, float] | None:
    """Parse a ``zone.tab`` coordinate (``+DDMM[SS]+DDDMM[SS]``)."""
    match = re.fullmatch(
        r"([+-])(\d{2})(\d{2})(\d{2})?([+-])(\d{3})(\d{2})(\d{2})?",
        token.strip(),
    )
    if not match:
        return None
    lat_sign, lat_d, lat_m, lat_s, lon_sign, lon_d, lon_m, lon_s = match.groups()
    latitude = int(lat_d) + int(lat_m) / 60 + (int(lat_s) / 3600 if lat_s else 0)
    longitude = int(lon_d) + int(lon_m) / 60 + (int(lon_s) / 3600 if lon_s else 0)
    if lat_sign == "-":
        latitude = -latitude
    if lon_sign == "-":
        longitude = -longitude
    return latitude, longitude


_ZONE_TAB_CACHE: dict[str, list[tuple[str, float | None, float | None]]] | None = None


def _zone_rows() -> dict[str, list[tuple[str, float | None, float | None]]]:
    """Parse the system zone tables into ``{country_code: [(zone, lat, lon)]}``.

    Both ``zone.tab`` and ``zone1970.tab`` are merged, and every row's
    comma-separated country list is split: a row such as ``SA,AQ,KW,YE``
    belongs to all four countries, not to a literal ``"SA,AQ,KW,YE"`` key.
    """
    global _ZONE_TAB_CACHE
    if _ZONE_TAB_CACHE is not None:
        return _ZONE_TAB_CACHE
    table: dict[str, list[tuple[str, float | None, float | None]]] = {}
    seen: set[tuple[str, str]] = set()
    for filename in ("zone.tab", "zone1970.tab"):
        path = Path("/usr/share/zoneinfo") / filename
        try:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    if not line or line.startswith("#"):
                        continue
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) < 3:
                        continue
                    zone = parts[2].strip()
                    if not zone:
                        continue
                    point = _parse_zone_coord(parts[1]) if len(parts) > 1 else None
                    lat, lon = point if point else (None, None)
                    for raw in parts[0].split(","):
                        code = raw.strip().upper()
                        if not code or (code, zone) in seen:
                            continue
                        seen.add((code, zone))
                        table.setdefault(code, []).append((zone, lat, lon))
        except OSError:
            continue
    _ZONE_TAB_CACHE = table
    return table


def _zones_by_country() -> dict[str, list[str]]:
    """Return ``{country_code: [zone names]}`` from the system tables."""
    return {code: [row[0] for row in rows] for code, rows in _zone_rows().items()}


def _zone_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Squared equirectangular distance — enough to pick a country zone."""
    dlat = lat1 - lat2
    dlon = (lon1 - lon2) * math.cos(math.radians((lat1 + lat2) / 2))
    return dlat * dlat + dlon * dlon


def _nearest_zone(
    rows: list[tuple[str, float | None, float | None]],
    latitude=None,
    longitude=None,
) -> str:
    """Pick the zone nearest the given coordinates (else the first row)."""
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0][0]
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return rows[0][0]
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return rows[0][0]
    # The app treats (0, 0) as "no fix" (see _apply_auto_coords); keep the
    # table's representative zone instead of matching a far-off capital.
    if lat == 0.0 and lon == 0.0:
        return rows[0][0]
    best: tuple[float, str] | None = None
    for zone, zlat, zlon in rows:
        if zlat is None or zlon is None:
            continue
        distance = _zone_distance(lat, lon, zlat, zlon)
        if best is None or distance < best[0]:
            best = (distance, zone)
    return best[1] if best else rows[0][0]


def _longitude_zone(longitude) -> str:
    """Best-effort fixed-offset zone for coordinates without a country zone."""
    try:
        lon = float(longitude)
    except (TypeError, ValueError):
        return "UTC"
    if not -180 <= lon <= 180:
        return "UTC"
    hours = max(-12, min(14, round(lon / 15)))
    if hours == 0:
        return "UTC"
    # IANA's Etc/GMT signs are inverted: Etc/GMT-3 == UTC+3.
    return f"Etc/GMT{'-' if hours > 0 else '+'}{abs(hours)}"


def _tz_for_country_code(code: str, latitude=None, longitude=None) -> str:
    """Resolve an IANA timezone from an ISO country code.

    Preference order: pytz's country map (when installed, single zone) and the
    system zone tables.  When the country spans several zones and coordinates
    are supplied, the nearest zone wins instead of the first table row.
    """
    if not code:
        return ""
    code = code.upper()
    if _PYTZ_AVAILABLE:
        try:
            zones = list(pytz.country_timezones.get(code, []))
        except Exception:
            zones = []
        if zones:
            table = _zone_rows().get(code)
            if table:
                return _nearest_zone(table, latitude, longitude)
            return _nearest_zone([(zone, None, None) for zone in zones], latitude, longitude)
    return _nearest_zone(_zone_rows().get(code, []), latitude, longitude)


def _tz_for_country(name: str, code: str = "", latitude=None, longitude=None) -> str:
    """Resolve a timezone from an ISO code, then a country name.

    With coordinates the result is never empty: an unknown country falls back
    to its longitude-derived offset, so callers can always replace a stale
    foreign timezone instead of keeping it.
    """
    tz = _tz_for_country_code(code, latitude, longitude)
    if tz:
        return tz
    if not code and name:
        derived = _country_code(name)
        if derived:
            tz = _tz_for_country_code(derived, latitude, longitude)
            if tz:
                return tz
        tz = COUNTRY_TZ.get(name, "")
        if tz:
            return tz
    return _longitude_zone(longitude) if longitude is not None else ""


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
                "http://ip-api.com/json/", headers={"User-Agent": "AthanFiveTimes/0.3.19b"}
            )
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data.get("status") == "success":
                city = data.get("city", "")
                country = data.get("country", "")
                code = (data.get("countryCode") or "").upper()
                lat = data.get("lat", 0.0)
                lon = data.get("lon", 0.0)
                tz = data.get("timezone", "") or _tz_for_country(country, code, lat, lon)
                if lat == 0.0 and lon == 0.0:
                    logger.warning("Invalid coordinates from IP API")
                    if attempt < retries:
                        time.sleep(2)
                        continue
                    return None
                return {
                    "city": city,
                    "country": country,
                    "country_code": code or _country_code(country),
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
        req = Request("https://ipapi.co/json/", headers={"User-Agent": "AthanFiveTimes/0.3.19b"})
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
            headers={"User-Agent": "AthanFiveTimes/0.3.19b"},
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
            headers={"User-Agent": "AthanFiveTimes/0.3.19b"},
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
        code = (data.get("country_code") or "").upper()
        if not tz:
            tz = _tz_for_country(country, code, lat, lon)
        return {
            "city": data.get("city", ""),
            "country": country,
            "country_code": code,
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
            headers={"User-Agent": "AthanFiveTimes/0.3.19b"},
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
        tz = data.get("timezone", "") or _tz_for_country(data.get("country", ""), code, lat, lon)
        return {
            "city": data.get("city", ""),
            "country": data.get("country", ""),
            "country_code": code,
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
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
