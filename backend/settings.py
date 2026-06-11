"""
Persistent settings management using JSON.
Fully immutable: all functions return new dicts, never mutate inputs.
"""

from __future__ import annotations

import json
import os
import shutil
import logging
import threading
from dataclasses import dataclass, field, fields
from functools import lru_cache
from typing import Any, Dict, List, Optional, get_type_hints

logger = logging.getLogger(__name__)

SETTINGS_DIR: str = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")),
    "athan-five-times",
)
SETTINGS_FILE: str = os.path.join(SETTINGS_DIR, "settings.json")
SETTINGS_BACKUP: str = SETTINGS_FILE + ".bak"

from . import __version__
APP_VERSION: str = __version__

MUEZZINS_DIR: str = os.path.join(os.path.dirname(__file__), "assets", "muezzins")

_MUEZZIN_CACHE: dict | None = None
_SETTINGS_CACHE: dict | None = None
_SETTINGS_VERSION: int = 0
_SETTINGS_LOCK = threading.RLock()

SETTINGS_VERSION: int = 3

PRAYER_KEYS: tuple = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")


@dataclass
class SettingsSchema:
    country: str = "TN"
    city: str = "Tunis"
    latitude: float = 36.8065
    longitude: float = 10.1815
    method: str = "وزارة الشؤون الدينية التونسية"
    madhab: str = "shafi"
    language: str = "ar"
    timezone: str = "Africa/Tunis"
    offsets: Dict[str, int] = field(default_factory=lambda: {
        "fajr": 0, "sunrise": 0, "dhuhr": 0,
        "asr": 0, "maghrib": 0, "isha": 0,
    })
    hijri_day_offset: int = 0
    audio: Dict[str, str] = field(default_factory=lambda: {
        "fajr": "", "sunrise": "", "dhuhr": "",
        "asr": "", "maghrib": "", "isha": "",
        "default": "",
    })
    muezzins: Dict[str, str] = field(default_factory=dict)
    azan_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "fajr": True, "dhuhr": True,
        "asr": True, "maghrib": True, "isha": True,
    })
    pre_azan_minutes: int = 10
    pre_azan_enabled: bool = True
    fade_in: bool = True
    fade_in_duration: int = 3
    volume: float = 1.0
    takbeer_only: bool = False
    theme: str = "dark"
    dnd_enabled: bool = True
    dnd_from: int = 22
    dnd_to: int = 6
    dnd_duration: int = 20
    sleep_mode: bool = True
    silent_mode: bool = False
    first_run: bool = True
    last_version: str = ""
    athkar_popup_enabled: bool = True
    athkar_popup_duration: int = 300
    autostart: bool = False
    window_geometry: List[int] = field(default_factory=lambda: [100, 100, 800, 600])
    athkar_popup_delay: int = 600
    athkarCount: int = 33
    athkarMethod: str = "after_prayer"
    update_url: str = ""
    schema_version: int = SETTINGS_VERSION
    custom_coords: bool = False
    background_enabled: bool = True


def schema_to_dict() -> Dict[str, Any]:
    """Convert SettingsSchema defaults to a plain dict (immutable)."""
    schema = SettingsSchema()
    result: Dict[str, Any] = {}
    for f in fields(schema):
        val = getattr(schema, f.name)
        result[f.name] = _deep_freeze(val)
    return result


def _deep_freeze(val: Any) -> Any:
    """Deep-copy a value to prevent reference sharing (immutable pattern)."""
    if isinstance(val, dict):
        return {k: _deep_freeze(v) for k, v in val.items()}
    if isinstance(val, tuple):
        return tuple(_deep_freeze(v) for v in val)
    if isinstance(val, list):
        return [_deep_freeze(v) for v in val]
    return val


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge two dicts, returning a new dict (immutable)."""
    result = {}
    all_keys = set(base.keys()) | set(override.keys())
    for key in all_keys:
        if key in base and key in override:
            if isinstance(base[key], dict) and isinstance(override[key], dict):
                result[key] = _deep_merge(base[key], override[key])
            else:
                result[key] = _deep_freeze(override[key])
        elif key in base:
            result[key] = _deep_freeze(base[key])
        else:
            result[key] = _deep_freeze(override[key])
    return result


def _ensure_dict_defaults(data: dict, schema_defaults: dict) -> dict:
    """Ensure nested dict fields have all keys from defaults (immutable)."""
    result = {}
    for key, default_val in schema_defaults.items():
        if key not in data:
            result[key] = _deep_freeze(default_val)
        elif isinstance(default_val, dict) and isinstance(data.get(key), dict):
            merged = dict(default_val)
            merged.update(data[key])
            result[key] = merged
        else:
            result[key] = data[key]
    return result


def validate_and_coerce(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and coerce known keys against SettingsSchema; pass through unknown keys.
    Returns a new dict (immutable)."""
    schema = SettingsSchema()
    result: Dict[str, Any] = {}
    type_map = get_type_hints(SettingsSchema)
    schema_keys = set(type_map)
    for key, value in data.items():
        if key not in schema_keys:
            result[key] = _deep_freeze(value)
            continue
        expected = type_map[key]
        if expected is int:
            if not isinstance(value, int):
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    value = getattr(schema, key)
        elif expected is float:
            if not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    value = getattr(schema, key)
        elif expected is bool:
            if not isinstance(value, bool):
                if isinstance(value, (int, float)):
                    value = bool(value)
                elif isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                else:
                    value = getattr(schema, key)
        elif expected is str:
            if not isinstance(value, str):
                value = str(value) if value is not None else getattr(schema, key)
        elif getattr(expected, '__origin__', None) is dict:
            if not isinstance(value, dict):
                value = getattr(schema, key)
            else:
                value = _deep_freeze(value)
        elif getattr(expected, '__origin__', None) is list:
            if not isinstance(value, list):
                value = getattr(schema, key)
            else:
                value = _deep_freeze(value)
        result[key] = value
    for f in fields(schema):
        if f.name not in result:
            result[f.name] = _deep_freeze(getattr(schema, f.name))
    return result


def _validate_nested(settings: dict) -> dict:
    """Ensure nested structural requirements (azan_enabled, audio, offsets have all prayer keys)."""
    result = dict(settings)
    nested_defaults = [
        ("azan_enabled", {p: True for p in PRAYER_KEYS if p != "sunrise"}),
        ("offsets", {p: 0 for p in PRAYER_KEYS if p != "sunrise"}),
        ("audio", {p: "" for p in PRAYER_KEYS} | {"default": ""}),
    ]
    for key, default_val in nested_defaults:
        if key in result and isinstance(result[key], dict):
            merged = dict(default_val)
            merged.update(result[key])
            result[key] = merged
    return result


# ── Migration system ──────────────────────────────────────────────────

MIGRATIONS: Dict[int, Any] = {}


def _register_migration(from_version: int):
    """Decorator to register a settings migration function."""
    def decorator(func):
        MIGRATIONS[from_version] = func
        return func
    return decorator


@_register_migration(0)
def _migrate_v0_to_v1(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate from implicit version 0 to version 1 (immutable)."""
    result = dict(settings)
    schema_defaults = schema_to_dict()
    for key, default_value in schema_defaults.items():
        if key not in result:
            result[key] = default_value
        elif isinstance(default_value, dict) and isinstance(result.get(key), dict):
            result[key] = {**default_value, **result[key]}
    result["schema_version"] = 1
    return result


@_register_migration(1)
def _migrate_v1_to_v2(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate from version 1 to version 2."""
    result = dict(settings)
    schema_defaults = schema_to_dict()
    for key, default_value in schema_defaults.items():
        if key not in result:
            result[key] = default_value
    result["schema_version"] = 2
    return result


@_register_migration(2)
def _migrate_v2_to_v3(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate from version 2 to version 3.
    - Ensure azan_enabled has all prayer keys
    - Ensure audio has all prayer keys
    - Ensure offsets has all prayer keys
    - Add custom_coords if missing
    """
    result = dict(settings)
    schema_defaults = schema_to_dict()
    for key, default_value in schema_defaults.items():
        if key not in result:
            result[key] = default_value
        elif isinstance(default_value, dict) and isinstance(result.get(key), dict):
            merged = dict(default_value)
            merged.update(result[key])
            result[key] = merged
    result["schema_version"] = 3
    return result


def _run_migrations(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Run any pending migrations on the settings dict (immutable)."""
    current_version: int = settings.get("schema_version", 0)
    result = dict(settings)
    while current_version < SETTINGS_VERSION:
        migration = MIGRATIONS.get(current_version)
        if migration:
            logger.info("Running settings migration v%d -> v%d", current_version, current_version + 1)
            result = migration(result)
        current_version += 1
    return result


# ── Path resolution ───────────────────────────────────────────────────

_RESOLVE_CACHE: dict = {}
_RESOLVE_CACHE_ORDER: list = []
_RESOLVE_CACHE_MAX: int = 128
_RESOLVE_LOCK = threading.RLock()


def invalidate_resolve_cache():
    with _RESOLVE_LOCK:
        global _RESOLVE_CACHE, _RESOLVE_CACHE_ORDER
        _RESOLVE_CACHE = {}
        _RESOLVE_CACHE_ORDER = []


def _cache_put(path: str, resolved: str):
    with _RESOLVE_LOCK:
        global _RESOLVE_CACHE, _RESOLVE_CACHE_ORDER
        if len(_RESOLVE_CACHE) >= _RESOLVE_CACHE_MAX:
            oldest = _RESOLVE_CACHE_ORDER.pop(0)
            _RESOLVE_CACHE.pop(oldest, None)
        _RESOLVE_CACHE[path] = resolved
        _RESOLVE_CACHE_ORDER.append(path)


def resolve_azan_path(path: str) -> str:
    """Return a valid path to an azan audio file.
    Tries exact path, MUEZZINS_DIR, rename mapping, then first available.
    Uses bounded LRU cache to prevent RAM leak.
    """
    if not path:
        return ""
    with _RESOLVE_LOCK:
        if path in _RESOLVE_CACHE:
            return _RESOLVE_CACHE[path]
    if os.path.isfile(path):
        _cache_put(path, path)
        return path
    fname: str = os.path.basename(path)
    resolved: str = os.path.join(MUEZZINS_DIR, fname)
    if os.path.isfile(resolved):
        _cache_put(path, resolved)
        return resolved
    if not os.path.isdir(MUEZZINS_DIR):
        return path
    saved_no_ext: str = os.path.splitext(fname)[0].strip()
    for f in sorted(os.listdir(MUEZZINS_DIR)):
        if f.lower().endswith(".mp3"):
            candidate: str = os.path.join(MUEZZINS_DIR, f)
            if os.path.isfile(candidate):
                if f == fname or os.path.splitext(f)[0].strip() == saved_no_ext:
                    _cache_put(path, candidate)
                    return candidate
    rename_map: Dict[str, str] = {
        "azan": "قطامي",
        "Ahmad Nuyne3": "Ahmad Nuyne",
    }
    if saved_no_ext in rename_map:
        new_fname: str = rename_map[saved_no_ext] + ".mp3"
        candidate = os.path.join(MUEZZINS_DIR, new_fname)
        if os.path.isfile(candidate):
            _cache_put(path, candidate)
            return candidate
    for f in sorted(os.listdir(MUEZZINS_DIR)):
        if f.lower().endswith(".mp3"):
            candidate = os.path.join(MUEZZINS_DIR, f)
            if os.path.isfile(candidate):
                _cache_put(path, candidate)
                return candidate
    return path


def discover_builtin_muezzins() -> dict:
    global _MUEZZIN_CACHE
    if _MUEZZIN_CACHE is not None:
        return _MUEZZIN_CACHE
    result: Dict[str, str] = {}
    if os.path.isdir(MUEZZINS_DIR):
        for fname in sorted(os.listdir(MUEZZINS_DIR)):
            if fname.lower().endswith(".mp3"):
                name: str = fname[:-4]
                path: str = os.path.join(MUEZZINS_DIR, fname)
                result[name] = path
    _MUEZZIN_CACHE = result
    return result


def invalidate_muezzin_cache():
    global _MUEZZIN_CACHE
    _MUEZZIN_CACHE = None


DEFAULT_SETTINGS: Dict[str, Any] = schema_to_dict()


def load() -> Dict[str, Any]:
    global _SETTINGS_CACHE, _SETTINGS_VERSION
    with _SETTINGS_LOCK:
        if _SETTINGS_CACHE is not None and _SETTINGS_VERSION == SETTINGS_VERSION:
            return dict(_SETTINGS_CACHE)
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        merged: Dict[str, Any] = dict(DEFAULT_SETTINGS)
        if os.path.isfile(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved: Dict[str, Any] = json.load(f)
                merged = _deep_merge(DEFAULT_SETTINGS, saved)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load settings (%s), trying backup...", exc)
                if os.path.isfile(SETTINGS_BACKUP):
                    try:
                        with open(SETTINGS_BACKUP, "r", encoding="utf-8") as f:
                            saved = json.load(f)
                        merged = _deep_merge(DEFAULT_SETTINGS, saved)
                        logger.info("Settings restored from backup")
                    except (OSError, json.JSONDecodeError) as exc2:
                        logger.warning("Backup also failed (%s), using defaults", exc2)
        merged = _run_migrations(merged)
        merged = validate_and_coerce(merged)
        merged = _validate_nested(merged)
        builtin: Dict[str, str] = discover_builtin_muezzins()
        merged_muezzins: Dict[str, str] = dict(merged.get("muezzins", {}))
        for k, v in builtin.items():
            merged_muezzins[k] = v
        default_azan: str = os.path.join(os.path.dirname(__file__), "assets", "muezzins", "قطامي.mp3")
        if os.path.isfile(default_azan):
            merged_muezzins["افتراضي"] = default_azan
        merged_muezzins = {k: resolve_azan_path(v) for k, v in merged_muezzins.items()}
        merged_audio: Dict[str, str] = dict(merged.get("audio", {}))
        if not merged_audio.get("default"):
            merged_audio["default"] = default_azan
        merged_audio = {k: resolve_azan_path(v) for k, v in merged_audio.items()}
        final_settings = dict(merged)
        final_settings["muezzins"] = merged_muezzins
        final_settings["audio"] = merged_audio
        _SETTINGS_CACHE = final_settings
        _SETTINGS_VERSION = SETTINGS_VERSION
        return dict(final_settings)


def get_cached() -> Dict[str, Any]:
    """Return current cached settings without reloading (or load if needed)."""
    with _SETTINGS_LOCK:
        global _SETTINGS_CACHE
        if _SETTINGS_CACHE is None:
            return load()
        return _SETTINGS_CACHE


def invalidate_cache():
    with _SETTINGS_LOCK:
        global _SETTINGS_CACHE
        _SETTINGS_CACHE = None
    invalidate_muezzin_cache()
    invalidate_resolve_cache()


def save(settings: Dict[str, Any]) -> None:
    settings_copy = dict(settings)
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    if os.path.isfile(SETTINGS_FILE):
        try:
            shutil.copy2(SETTINGS_FILE, SETTINGS_BACKUP)
        except OSError as exc:
            logger.warning("Failed to backup settings: %s", exc)
    tmp: str = SETTINGS_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(settings_copy, f, ensure_ascii=False, indent=2)
        os.replace(tmp, SETTINGS_FILE)
        invalidate_cache()
        invalidate_resolve_cache()
    except (OSError, json.JSONEncodeError, TypeError, ValueError) as exc:
        logger.error("Failed to save settings: %s", exc)
        if os.path.isfile(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass


AUTOSTART_DIR: str = os.path.join(os.path.expanduser("~"), ".config", "autostart")
AUTOSTART_FILE: str = os.path.join(AUTOSTART_DIR, "athan-five-times.desktop")


def set_autostart(enabled: bool) -> None:
    """Create or remove the autostart .desktop entry."""
    if enabled:
        os.makedirs(AUTOSTART_DIR, exist_ok=True)
        base: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        script: str = os.path.join(base, "run.sh")
        if os.path.isfile(script):
            cmd: str = f"\"{script}\""
        else:
            cmd = f"python3 \"{os.path.join(base, 'prayer_app', '__main__.py')}\""
        icon_png: str = "/app/share/icons/hicolor/scalable/apps/com.azanprayer.app.svg"
        icon_local: str = os.path.join(os.path.dirname(__file__), "assets", "kaaba.svg")
        icon_path: str = icon_png if os.path.isfile(icon_png) else icon_local
        desktop: str = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name=أذان الأوقات الخمس\n"
            f"Exec={cmd}\n"
            f"Icon={icon_path}\n"
            "Comment=تطبيق أذان الأوقات الخمس\n"
            "Terminal=false\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
        with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
            f.write(desktop)
        try:
            os.chmod(AUTOSTART_FILE, 0o755)
        except OSError as exc:
            logger.warning("Could not set executable permission on autostart file: %s", exc)
    else:
        if os.path.isfile(AUTOSTART_FILE):
            os.remove(AUTOSTART_FILE)
