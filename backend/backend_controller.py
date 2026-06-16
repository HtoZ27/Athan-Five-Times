"""
Backend Controller - Python-QML bridge for the Athan application.
"""

import logging
import os
import subprocess
import threading
from datetime import date, datetime, timedelta

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QMetaObject, Q_ARG, Qt

from .prayer_calc import calculate, PRAYER_ORDER, _resolve_timezone
from .audio import play_azan, stop_azan, set_volume, preload_audio
from .translations import get_athkar
from .settings import load as load_settings, save as save_settings, resolve_azan_path, set_autostart as _set_autostart
from .settings import invalidate_cache as invalidate_settings_cache
from .i18n import t, t_prayer, set_lang, format_date, country_name, city_name, credits_html, credits_title
from .translations import calc_method_name, madhab_name, timezone_name, theme_name, u
from ._constants import PRAYERS_WITH_AZAN, DARK_THEMES, LANGS, THEME_IDS, _display_key
from .prayer_calc import CALCULATION_METHODS, COUNTRY_CITIES, COUNTRIES, COUNTRY_METHODS
from .athkar_provider import AthkarProvider

logger = logging.getLogger(__name__)

# Cached static data to avoid repeated list creation
_COUNTRY_LIST_CACHE: list | None = None
_CALC_METHODS_CACHE: list | None = None
_MADHABS_CACHE: list | None = None
_LANGUAGES_CACHE: list | None = None
_TIMEZONES_CACHE: list | None = None
_THEMES_CACHE: list | None = None


class PrayerEngine(QObject):
    clockChanged = Signal(str)
    dateChanged = Signal()
    nextPrayerChanged = Signal()
    countdownChanged = Signal(str)
    preAlertChanged = Signal(str)
    azanPlayingChanged = Signal(bool)
    prayerTimesChanged = Signal()
    athkarShown = Signal(str, str, int, str, bool)
    languageChanged = Signal()
    trayInfoChanged = Signal(str, str, str)
    themeChanged = Signal(str)
    locationChanged = Signal()
    settingChanged = Signal(str)
    backgroundEnabledChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = load_settings()
        self._result = None
        self._cached_next = None
        self._notified_prayers = set()
        self._pre_notified = set()
        self._azan_playing = False
        self._stop_event = threading.Event()
        self._notified_date = None
        self._clock_text = ""
        self._countdown_text = "--:--:--"
        self._next_name = "--"
        self._pre_alert_text = ""
        self._gregorian_date = ""
        self._prayer_times_cache = None
        self._prayer_times_cache_key = None
        self._hijri_date = ""
        self._dnd_timer = None
        self._athkar_provider = AthkarProvider(self)

        # Initialize _azan_path with robust fallback chain
        self._azan_path = self._resolve_default_azan_path()
        self._scheduled_timer = None
        self._scheduled_next_prayer = None

        set_lang(self._settings.get("language", "ar"))
        self._setup_timers()
        QTimer.singleShot(0, self.recalculate)

    def _setup_timers(self):
        self._background_mode = False
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        sleep_mode = self._settings.get("sleep_mode", True)
        poll_interval = 300000 if sleep_mode else 60000
        self._prayer_timer = QTimer(self)
        self._prayer_timer.timeout.connect(self._check_prayer)
        self._prayer_timer.start(poll_interval)

        self._midnight_timer = QTimer(self)
        self._midnight_timer.setSingleShot(True)
        self._midnight_timer.timeout.connect(self.recalculate)
        self._schedule_midnight()

        if sleep_mode:
            self._schedule_next_prayer()

    @Slot(bool)
    def setBackgroundMode(self, bg: bool):
        self._background_mode = bg
        self._clock_timer.setInterval(30000 if bg else 1000)
        sleep_mode = self._settings.get("sleep_mode", True)
        poll_interval = 300000 if (sleep_mode or bg) else 60000
        self._prayer_timer.setInterval(poll_interval)

    @Slot(bool)
    def setAutostart(self, enabled: bool):
        _set_autostart(enabled)

    def _schedule_midnight(self):
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        secs = int((tomorrow - now).total_seconds())
        self._midnight_timer.stop()
        self._midnight_timer.start(secs * 1000 + 1500)

    def _update_clock(self):
        now = datetime.now()
        text = now.strftime("%H:%M:%S")
        if text != self._clock_text:
            self._clock_text = text
            self.clockChanged.emit(text)
        if not self._result:
            return
        dt_now = datetime.now()
        if self._cached_next is None or dt_now >= self._cached_next[1]:
            self._cached_next = self._result.next_prayer(dt_now)
            self.nextPrayerChanged.emit()
        self._update_countdown(dt_now)
        self._check_pre_azan(dt_now)
        self._update_tray_info()

    def _update_tray_info(self):
        try:
            info = self.getTrayInfo()
            self.trayInfoChanged.emit(
                info.get("next", ""),
                info.get("remaining", ""),
                self._pre_alert_text if not self._settings.get("silent_mode", False) else "",
            )
        except (AttributeError, KeyError, TypeError):
            pass

    def _update_countdown(self, now: datetime):
        if not self._cached_next:
            return
        name, dt = self._cached_next
        rem = dt - now
        if rem.total_seconds() > 0:
            h, r = divmod(int(rem.total_seconds()), 3600)
            m, s = divmod(r, 60)
            text = f"{h:02d}:{m:02d}:{s:02d}"
            if text != self._countdown_text:
                self._countdown_text = text
                self.countdownChanged.emit(text)
            if name != self._next_name:
                self._next_name = name
                self.nextPrayerChanged.emit()
        else:
            if self._countdown_text != "":
                self._countdown_text = ""
                self.countdownChanged.emit(t("countdown_now"))
            if name != self._next_name:
                self._next_name = name
                self.nextPrayerChanged.emit()

    def _check_pre_azan(self, now: datetime):
        if not self._settings.get("pre_azan_enabled", True) or self._settings.get("silent_mode", False):
            if self._pre_alert_text:
                self._pre_alert_text = ""
                self.preAlertChanged.emit("")
            return
        if not self._cached_next:
            return
        name, dt = self._cached_next
        if name == "sunrise":
            return
        mins_before = self._settings.get("pre_azan_minutes", 10)
        alert_time = dt - timedelta(minutes=mins_before)
        if alert_time <= now < dt and name not in self._pre_notified:
            self._pre_notified.add(name)
            self._pre_alert_text = t("pre_alert", mins=str(mins_before), prayer=t_prayer(_display_key(name)))
            self.preAlertChanged.emit(self._pre_alert_text)
        elif now > dt and self._pre_alert_text:
            self._pre_alert_text = ""
            self.preAlertChanged.emit("")

    def _check_prayer(self):
        if self._result is None:
            return
        # Use timezone-aware "today" based on settings timezone
        tz_name = self._settings.get("timezone")
        tz = _resolve_timezone(tz_name, self._settings.get("longitude", 0.0))
        now = datetime.now(tz) if tz else datetime.now()
        today = now.date()
        if self._notified_date is None:
            self._notified_date = today
        elif self._notified_date != today:
            self._notified_prayers.clear()
            self._pre_notified.clear()
            self._notified_date = today
        remaining = [k for k in PRAYERS_WITH_AZAN if k not in self._notified_prayers]
        if not remaining:
            return
        now_naive = now.replace(tzinfo=None)
        d = self._result.as_dict()
        for name in remaining:
            elapsed = (now_naive - d[name]).total_seconds()
            if 0 <= elapsed < 300:
                self._notified_prayers.add(name)
                self._trigger_azan(name)
                break
            elif elapsed >= 300:
                self._notified_prayers.add(name)

    def _trigger_azan(self, prayer_key: str):
        name = t_prayer(_display_key(prayer_key))
        logger.info("Prayer time reached: %s", name)
        silent_mode = self._settings.get("silent_mode", False)

        if not silent_mode:
            self._notify_os(name)

        if self._settings.get("dnd_enabled", True) and not silent_mode:
            self._enable_dnd(self._settings.get("dnd_duration", 20))

        if self._settings.get("azan_enabled", {}).get(prayer_key, True) and not silent_mode:
            audio_settings = self._settings.get("audio", {})
            audio_file = audio_settings.get(prayer_key, "") or audio_settings.get("default", "")
            if not audio_file:
                muezzins = self._settings.get("muezzins", {})
                audio_file = muezzins.get("افتراضي", "") or self._azan_path
            audio_file = resolve_azan_path(audio_file)
            if os.path.isfile(audio_file):
                self._stop_event.clear()
                self._set_azan_playing(True)
                play_azan(
                    audio_file,
                    fade_in=self._settings.get("fade_in", True),
                    fade_duration=self._settings.get("fade_in_duration", 3),
                    takbeer_only=self._settings.get("takbeer_only", False),
                    on_done=self._on_azan_done,
                    stop_flag=self._stop_event,
                )

        texts = get_athkar(prayer_key)
        if texts:
            is_dark = self._settings.get("theme", "dark") in DARK_THEMES
            dur = self._settings.get("athkar_popup_duration", 7) * 1000
            self.athkarShown.emit(prayer_key, t("athkar_after_prayer"), dur, "\n\n".join(texts[:2]), is_dark)

    def _notify_os(self, prayer_name: str):
        try:
            subprocess.Popen(
                ["notify-send", t("notif_prayer_title"),
                 t("notif_prayer_body", prayer=prayer_name), "-t", "10000"]
            )
        except (FileNotFoundError, PermissionError, OSError) as exc:
            logger.warning("Notification failed: %s", exc)

    @Slot(bool)
    def _set_azan_playing(self, playing: bool):
        self._azan_playing = playing
        self.azanPlayingChanged.emit(playing)
        if not playing and self._settings.get("sleep_mode", True):
            self._schedule_next_prayer()

    def _on_azan_done(self):
        QMetaObject.invokeMethod(self, "_set_azan_playing",
            Qt.ConnectionType.QueuedConnection, Q_ARG(bool, False))

    def _schedule_next_prayer(self):
        if not self._result:
            return
        now = datetime.now()
        remaining = [k for k in PRAYERS_WITH_AZAN if k not in self._notified_prayers]
        if not remaining:
            return
        d = self._result.as_dict()
        next_name = min(remaining, key=lambda k: d[k] if d[k] > now else datetime.max)
        next_time = d[next_name]
        if next_time <= now:
            return
        ms = int((next_time - now).total_seconds() * 1000)
        if self._scheduled_timer:
            self._scheduled_timer.stop()
            self._scheduled_timer.deleteLater()
        self._scheduled_timer = QTimer(self)
        self._scheduled_timer.setSingleShot(True)
        self._scheduled_timer.timeout.connect(self._on_scheduled_timeout)
        self._scheduled_next_prayer = next_name
        self._scheduled_timer.start(ms)

    @Slot()
    def _on_scheduled_timeout(self):
        if self._scheduled_next_prayer and self._scheduled_next_prayer not in self._notified_prayers:
            self._trigger_azan(self._scheduled_next_prayer)
            self._scheduled_next_prayer = None

    def _run_dnd_cmds(self, enable: bool):
        cmds = [
            ["dunstctl", "set-paused", "true" if enable else "false"],
            ["makoctl", "mode", "-a" if enable else "-r", "do-not-disturb"],
            ["gsettings", "set", "org.gnome.desktop.notifications", "show-banners", "false" if enable else "true"],
            ["xfconf-query", "-c", "xfce4-notifyd", "-p", "/do-not-disturb", "-s", "true" if enable else "false"],
            ["swaync-client", "-dnd-on" if enable else "-dnd-off"],
            ["qdbus", "org.kde.knotifications", "/Notify", "disableNotifications" if enable else "enableNotifications"],
            ["gsettings", "set", "org.cinnamon.desktop.notifications", "show-banners", "false" if enable else "true"],
            ["gsettings", "set", "org.mate.NotificationDaemon", "do-not-disturb", "true" if enable else "false"],
            ["lxqt-notificationd", "--disable" if enable else "--enable"],
        ]
        for cmd in cmds:
            try:
                subprocess.run(cmd, capture_output=True, timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
                pass

    def _enable_dnd(self, duration_minutes: int):
        try:
            subprocess.run(["notify-send", "-t", "3000", t("notif_dnd_title"), t("notif_dnd_body", mins=str(duration_minutes))], capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            pass
        threading.Thread(target=self._run_dnd_cmds, args=(True,), daemon=True).start()
        if self._dnd_timer:
            self._dnd_timer.stop()
            self._dnd_timer.deleteLater()
        self._dnd_timer = QTimer(self)
        self._dnd_timer.setSingleShot(True)
        self._dnd_timer.timeout.connect(self._disable_dnd)
        self._dnd_timer.start(duration_minutes * 60000)

    def _disable_dnd(self):
        self._dnd_timer = None
        threading.Thread(target=self._run_dnd_cmds, args=(False,), daemon=True).start()

    def cleanup(self):
        try:
            if hasattr(self, '_clock_timer') and self._clock_timer:
                self._clock_timer.stop()
                self._clock_timer = None
        except RuntimeError:
            pass
        try:
            if hasattr(self, '_prayer_timer') and self._prayer_timer:
                self._prayer_timer.stop()
                self._prayer_timer = None
        except RuntimeError:
            pass
        try:
            if hasattr(self, '_midnight_timer') and self._midnight_timer:
                self._midnight_timer.stop()
        except RuntimeError:
            pass
        try:
            if hasattr(self, '_dnd_timer') and self._dnd_timer:
                self._dnd_timer.stop()
                self._dnd_timer = None
        except RuntimeError:
            pass
        try:
            if hasattr(self, '_scheduled_timer') and self._scheduled_timer:
                self._scheduled_timer.stop()
                self._scheduled_timer = None
        except RuntimeError:
            pass
        self._stop_event.set()
        stop_azan()

    def __del__(self):
        try:
            self.cleanup()
        except (RuntimeError, AttributeError):
            pass

    def recalculate(self):
        s = self._settings
        self._result = calculate(
            s.get("latitude", 36.8), s.get("longitude", 10.18),
            method_name=s.get("method", "Tunisia"),
            madhab=s.get("madhab", "shafi"),
            tz_name=s.get("timezone", None),
            offsets=s.get("offsets", None),
        )
        if self._result is None:
            logger.warning("Prayer calculation failed")
            return
        self._cached_next = None
        self._prayer_times_cache = None
        self._prayer_times_cache_key = None
        self._schedule_midnight()
        today = date.today()
        date_part, hijri_part = format_date(today, s.get("hijri_day_offset", 0))
        self._gregorian_date = date_part
        self._hijri_date = hijri_part
        self.dateChanged.emit()
        now = datetime.now()
        cached = self._result.next_prayer(now)
        if cached and cached[0] not in ("sunrise",):
            self._athkar_provider.setPrayerAthkar(cached[0], t("athkar_after_prayer"))
        self._cached_next = cached
        self.nextPrayerChanged.emit()
        self._update_countdown(now)
        self._check_pre_azan(now)
        self._update_tray_info()
        today = now.date()
        if self._notified_date != today:
            self._notified_prayers.clear()
            self._pre_notified.clear()
            self._notified_date = today
        if self._settings.get("sleep_mode", True):
            self._schedule_next_prayer()
        self.prayerTimesChanged.emit()

    @Slot(result=str)
    def getNextPrayerName(self):
        if self._cached_next:
            return t_prayer(_display_key(self._cached_next[0]))
        return "--"

    @Slot(result=str)
    def getClockText(self):
        return self._clock_text

    @Slot(result=str)
    def getCountdownText(self):
        return self._countdown_text

    @Slot(result=str)
    def getGregorianDate(self):
        return self._gregorian_date

    @Slot(result=str)
    def getHijriDate(self):
        return self._hijri_date

    @Slot(result=str)
    def getLocationText(self):
        s = self._settings
        code = s.get("country", "")
        city = s.get("city", "")
        if code and city:
            return f"{city_name(city)}، {country_name(code)}"
        return ""

    @Slot(result=str)
    def getPreAlert(self):
        return self._pre_alert_text

    @Slot(result=QObject)
    def getAthkarProvider(self):
        return self._athkar_provider

    @Slot(result="QVariantList")
    def getPrayerTimes(self):
        if not self._result:
            return []
        # Cache key based on date and settings that affect display
        cache_key = (self._result.date_key if hasattr(self._result, 'date_key') else None,
                     self._settings.get("language"),
                     self._settings.get("time_format", "12h"))
        if self._prayer_times_cache is not None and self._prayer_times_cache_key == cache_key:
            return self._prayer_times_cache

        times = self._result.as_dict()
        result = []
        next_key = self._cached_next[0] if self._cached_next else ""
        for key in PRAYER_ORDER:
            result.append({
                "name": t_prayer(_display_key(key)),
                "time": times[key].strftime("%I:%M %p"),
                "key": key,
                "isNext": key == next_key,
            })
        self._prayer_times_cache = result
        self._prayer_times_cache_key = cache_key
        return result

    @Slot()
    def stopAzan(self):
        self._stop_event.set()
        stop_azan()
        self._set_azan_playing(False)

    @Slot(result=bool)
    def isAzanPlaying(self):
        return self._azan_playing

    @Slot(result="QVariant")
    def getSettings(self):
        return dict(self._settings)

    @Slot(str, result="QVariant")
    def getSetting(self, key: str):
        val = self._settings.get(key)
        if isinstance(val, (dict, list)):
            from copy import deepcopy
            return deepcopy(val)
        return val

    @Slot(str, result="QVariant")
    def getNestedSetting(self, key: str):
        keys = key.split(".")
        val = self._settings
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return None
        if isinstance(val, (dict, list)):
            from copy import deepcopy
            return deepcopy(val)
        return val

    def _update_settings_batch(self, updates: dict) -> dict:
        """Create a new settings dict with multiple updates applied atomically.
        Updates dict can contain nested keys with dot notation.
        """
        new_settings = dict(self._settings)
        for key, value in updates.items():
            if "." in key:
                parts = key.split(".")
                target = new_settings
                for part in parts[:-1]:
                    if part not in target:
                        target[part] = {}
                    target[part] = dict(target.get(part, {}))
                target[parts[-1]] = value
            else:
                new_settings[key] = value
        return new_settings

    def _update_setting_immutable(self, key: str, value) -> dict:
        """Create a new settings dict with the key updated (immutable pattern)."""
        return self._update_settings_batch({key: value})

    def _auto_update_coordinates(self):
        s = self._settings
        country = s.get("country")
        city = s.get("city")
        if country and country != "none" and city:
            cities = COUNTRY_CITIES.get(country, [])
            # Build city lookup dict for O(1) access
            city_map = {eng_name: (lat, lon) for eng_name, lat, lon in cities}
            if city in city_map:
                lat, lon = city_map[city]
                self._settings = self._update_settings_batch({"latitude": lat, "longitude": lon})
                return
            if cities:
                self._settings = self._update_settings_batch({"latitude": cities[0][1], "longitude": cities[0][2]})
                return

    def _apply_auto_coords(self, country: str, city: str, latitude: float, longitude: float,
                          timezone: str | None = None, clear_custom: bool = True) -> None:
        """Apply auto-detected coordinates with common logic."""
        updates = {
            "country": country,
            "city": city,
            "latitude": latitude,
            "longitude": longitude,
        }
        if timezone:
            updates["timezone"] = timezone
        if clear_custom:
            updates["custom_coords"] = False
        self._settings = self._update_settings_batch(updates)
        self.recalculate()
        self.locationChanged.emit()

    @Slot()
    def resetToAutoCoordinates(self):
        from .location import detect_async

        def _on_result(loc):
            self._pending_location = loc
            QMetaObject.invokeMethod(self, "_process_auto_location",
                                     Qt.ConnectionType.QueuedConnection)

        self._pending_location = None
        detect_async(_on_result)

    @Slot()
    def _process_auto_location(self):
        loc = self._pending_location
        self._pending_location = None
        if loc:
            self._apply_auto_coords(
                loc.get("country_code", "TN"),
                loc.get("city", "Tunis"),
                loc.get("latitude", 36.8065),
                loc.get("longitude", 10.1815),
                loc.get("timezone"),
            )
            # Auto-save
            try:
                save_settings(self._settings)
            except (OSError, TypeError, ValueError) as exc:
                logger.error("Failed to save after auto-location: %s", exc)
            return

        country = self._settings.get("country")
        city = self._settings.get("city")
        if country and country != "none":
            cities = COUNTRY_CITIES.get(country, [])
            for eng_name, lat, lon in cities:
                if eng_name == city:
                    self._apply_auto_coords(country, city, lat, lon, clear_custom=True)
                    return
            if cities:
                self._apply_auto_coords(
                    country, cities[0][0], cities[0][1], cities[0][2], clear_custom=True
                )
                return

        self._apply_auto_coords("TN", "Tunis", 36.8065, 10.1815, "Africa/Tunis", True)

    def _save_theme(self, theme_code: str, emit_signal: bool = True) -> None:
        """Internal method to save theme setting.

        Args:
            theme_code: Theme code to save
            emit_signal: Whether to emit themeChanged signal
        """
        if theme_code not in THEME_IDS:
            logger.warning(f"Invalid theme: {theme_code}, must be one of {THEME_IDS}")
            return
        self._settings = self._update_setting_immutable("theme", theme_code)
        try:
            save_settings(self._settings)
            logger.info("Theme saved: %s", theme_code)
        except (OSError, TypeError, ValueError) as exc:
            logger.error("Failed to save theme: %s", exc)
        if emit_signal:
            self.themeChanged.emit(theme_code)

    @Slot()
    def commitSettings(self):
        from .audio import clear_cache
        clear_cache()
        old_lang = getattr(self, '_stored_old_lang', self._settings.get("language", "ar"))
        old_theme = getattr(self, '_stored_old_theme', self._settings.get("theme", "dark"))
        _set_autostart(self._settings.get("autostart", False))
        try:
            save_settings(self._settings)
            logger.info("Settings saved successfully (theme=%s)", self._settings.get("theme"))
        except (OSError, TypeError, ValueError) as exc:
            logger.error("Failed to save settings: %s", exc)
        invalidate_settings_cache()
        new_lang = self._settings.get("language", "ar")
        if new_lang != old_lang:
            set_lang(new_lang)
            self.languageChanged.emit()
        new_theme = self._settings.get("theme", "dark")
        if new_theme != old_theme:
            self.themeChanged.emit(new_theme)
        set_volume(self._settings.get("volume", 1.0))
        self.recalculate()
        self.locationChanged.emit()
        sleep_mode = self._settings.get("sleep_mode", True)
        self._prayer_timer.setInterval(300000 if sleep_mode else 60000)

    @Slot(str)
    def saveTheme(self, theme_code: str):
        """Save theme directly without full commit logic."""
        self._save_theme(theme_code, emit_signal=True)

    @Slot()
    def storeSettingsSnapshot(self):
        self._stored_old_lang = self._settings.get("language", "ar")
        self._stored_old_theme = self._settings.get("theme", "dark")

    @Slot(str, "QVariant")
    def updateSetting(self, key: str, value):
        # Resolve current value for dot-notation keys (e.g. "azan_enabled.fajr")
        if "." in key:
            parts = key.split(".")
            cur = self._settings
            for p in parts:
                if isinstance(cur, dict):
                    cur = cur.get(p)
                else:
                    cur = None
                    break
            if cur is not None and cur == value:
                return
        elif key in self._settings and self._settings[key] == value:
            return
        # Handle theme validation and persistence
        if key == "theme":
            if value not in THEME_IDS:
                logger.warning(f"Invalid theme: {value}, must be one of {THEME_IDS}")
                return
            # Update internal settings and persist to JSON
            self._settings = self._update_setting_immutable("theme", value)
            try:
                save_settings(self._settings)
                logger.info("Theme saved via updateSetting: %s", value)
            except (OSError, TypeError, ValueError) as exc:
                logger.error("Failed to save theme: %s", exc)
            # Emit signals for theme change
            self.themeChanged.emit(value)
            self.settingChanged.emit(key)
            return
        # Handle validation/clamping for lat/lon in batch to avoid double dict creation
        updates = {key: value}
        if key == "latitude":
            try:
                value = float(value)
                if value < -90 or value > 90:
                    logger.warning("Invalid latitude %s, clamping to [-90, 90]", value)
                    value = max(-90, min(90, value))
                updates[key] = value
            except (ValueError, TypeError):
                return
        elif key == "longitude":
            try:
                value = float(value)
                if value < -180 or value > 180:
                    logger.warning("Invalid longitude %s, clamping to [-180, 180]", value)
                    value = max(-180, min(180, value))
                updates[key] = value
            except (ValueError, TypeError):
                return
        self._settings = self._update_settings_batch(updates)
        if key in ("country", "city") and not self._settings.get("custom_coords", False):
            self._auto_update_coordinates()
        if key in ("method", "madhab", "country", "city", "latitude", "longitude", "timezone"):
            self.recalculate()
            self.locationChanged.emit()
        elif key == "volume":
            set_volume(value)
        elif key == "background_enabled":
            self.backgroundEnabledChanged.emit(value)
        elif key in ("language", "time_format"):
            self._prayer_times_cache = None
            self._prayer_times_cache_key = None
        self.settingChanged.emit(key)

    @Slot(result="QVariantList")
    def getCountryList(self):
        global _COUNTRY_LIST_CACHE
        if _COUNTRY_LIST_CACHE is None:
            items = []
            for code in COUNTRIES:
                items.append({"code": code, "name": country_name(code)})
            items.sort(key=lambda x: x["name"])
            _COUNTRY_LIST_CACHE = items
        return _COUNTRY_LIST_CACHE

    @Slot(str, result="QVariantList")
    def getCitiesForCountry(self, code: str):
        items = []
        for eng_name, lat, lon in COUNTRY_CITIES.get(code, []):
            items.append({"name": city_name(eng_name), "engName": eng_name, "lat": lat, "lon": lon})
        return items

    @Slot(result="QVariantList")
    def getCalcMethods(self):
        global _CALC_METHODS_CACHE
        if _CALC_METHODS_CACHE is None:
            _CALC_METHODS_CACHE = [
                {"display": calc_method_name(k), "key": k}
                for k in CALCULATION_METHODS
            ]
        return _CALC_METHODS_CACHE

    @Slot(str, result="QString")
    def getDefaultMethod(self, country_code: str):
        return COUNTRY_METHODS.get(country_code, "")

    @Slot(result="QVariantList")
    def getMadhabs(self):
        global _MADHABS_CACHE
        if _MADHABS_CACHE is None:
            _MADHABS_CACHE = [
                {"display": madhab_name("shafi"), "key": "shafi"},
                {"display": madhab_name("hanafi"), "key": "hanafi"},
            ]
        return _MADHABS_CACHE

    @Slot(result="QVariantList")
    def getLanguages(self):
        global _LANGUAGES_CACHE
        if _LANGUAGES_CACHE is None:
            lang_names = {
                "ar": "العربية",
                "en": "English",
                "fr": "Français",
                "es": "Español",
                "es_la": "Español (Latinoamérica)",
                "it": "Italiano",
                "de": "Deutsch",
                "ru": "Русский",
                "tr": "Türkçe",
                "pa": "ਪੰਜਾਬੀ",
                "hi": "हिन्दी",
                "ur": "اردو",
                "tk": "Türkmençe",
                "ps": "پښتو",
                "id": "Bahasa Indonesia",
                "ms": "Bahasa Melayu",
                "so": "Soomaali",
            }
            _LANGUAGES_CACHE = [{"code": code, "name": lang_names.get(code, code)} for code in LANGS]
        return _LANGUAGES_CACHE

    @Slot()
    def clearCaches(self):
        global _COUNTRY_LIST_CACHE, _CALC_METHODS_CACHE, _MADHABS_CACHE
        global _TIMEZONES_CACHE, _THEMES_CACHE
        _COUNTRY_LIST_CACHE = None
        _CALC_METHODS_CACHE = None
        _MADHABS_CACHE = None
        _TIMEZONES_CACHE = None
        _THEMES_CACHE = None

    @Slot(result="QVariantList")
    def getThemes(self):
        global _THEMES_CACHE
        if _THEMES_CACHE is None:
            _THEMES_CACHE = [{"code": code, "name": theme_name(code)} for code in THEME_IDS]
        return _THEMES_CACHE

    def getTrayInfo(self):
        if not self._result or not self._cached_next:
            return {"next": "", "remaining": ""}
        now = datetime.now()
        name, dt = self._cached_next
        rem = dt - now
        if rem.total_seconds() > 0:
            h, r = divmod(int(rem.total_seconds()), 3600)
            m, s = divmod(r, 60)
            remaining = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            remaining = t("countdown_now")
        return {"next": t_prayer(_display_key(name)), "remaining": remaining}

    @Slot(result=str)
    def getCreditsHtml(self):
        return credits_html()

    @Slot(result=str)
    def getCreditsTitle(self):
        return credits_title()

    @Slot(result=str)
    def getLanguage(self):
        return self._settings.get("language", "ar")

    @Slot(result=bool)
    def isRtl(self):
        lang = self._settings.get("language", "ar")
        return lang in ("ar", "ur", "ps", "pa")

    @Slot(str)
    def previewAudio(self, path: str):
        resolved = resolve_azan_path(path)
        if os.path.isfile(resolved):
            self._stop_event.set()
            stop_azan()
            self._stop_event.clear()
            self._set_azan_playing(True)
            play_azan(resolved, fade_in=False, stop_flag=self._stop_event,
                      on_done=self._on_azan_done)

    @Slot()
    def stopPreview(self):
        self._stop_event.set()
        stop_azan()
        self._set_azan_playing(False)

    @Slot(result="QVariantList")
    def getMuezzins(self):
        muezzins = self._settings.get("muezzins", {})
        result = []
        for name, path in muezzins.items():
            if not path and name == "افتراضي":
                continue
            display_name = u(name) if name == "افتراضي" else name
            result.append({"name": display_name, "path": path})
        return result

    @Slot(str, str)
    def addMuezzin(self, name: str, path: str):
        new_muezzins = dict(self._settings.get("muezzins", {}))
        new_muezzins[name] = path
        self._settings = dict(self._settings)
        self._settings["muezzins"] = new_muezzins

    @Slot(str)
    def removeMuezzin(self, name: str):
        new_muezzins = dict(self._settings.get("muezzins", {}))
        new_muezzins.pop(name, None)
        self._settings = dict(self._settings)
        self._settings["muezzins"] = new_muezzins

    @Slot(str)
    def setDefaultMuezzin(self, path: str):
        from .audio import clear_cache
        clear_cache()
        new_audio = dict(self._settings.get("audio", {}))
        new_audio["default"] = path
        self._settings = dict(self._settings)
        self._settings["audio"] = new_audio
        save_settings(self._settings)
        invalidate_settings_cache()
        self._azan_path = resolve_azan_path(path)

    @Slot(str, str)
    def setPrayerAudio(self, prayer_key: str, path: str):
        new_audio = dict(self._settings.get("audio", {}))
        new_audio[prayer_key] = path
        self._settings = dict(self._settings)
        self._settings["audio"] = new_audio
        save_settings(self._settings)
        invalidate_settings_cache()

    @Slot(result=str)
    def openAudioFileDialog(self):
        from PySide6.QtWidgets import QFileDialog, QApplication
        try:
            parent = QApplication.activeWindow()
            path, _ = QFileDialog.getOpenFileName(
                parent, "اختر ملفًا صوتيًا", "",
                "Audio Files (*.mp3 *.wav *.ogg *.flac)")
            if path:
                path = path.replace("file://", "")
            return path or ""
        except Exception as exc:
            logger.error("File dialog failed: %s", exc)
            return ""

    @Slot(str, result=str)
    def getPrayerAudio(self, prayer_key: str):
        audio = self._settings.get("audio", {})
        path = audio.get(prayer_key, "")
        if not path:
            path = audio.get("default", "")
        if not path:
            muezzins = self._settings.get("muezzins", {})
            path = muezzins.get("افتراضي", "")
            if not path and muezzins:
                path = next(iter(muezzins.values()))
        return path

    @Slot(result="QVariantList")
    def getOffsetKeys(self):
        return list(PRAYERS_WITH_AZAN)

    @Slot(str, result=int)
    def getOffset(self, prayer_key: str):
        return self._settings.get("offsets", {}).get(prayer_key, 0)

    @Slot(str, int)
    def setOffset(self, prayer_key: str, value: int):
        new_offsets = dict(self._settings.get("offsets", {}))
        new_offsets[prayer_key] = value
        self._settings = dict(self._settings)
        self._settings["offsets"] = new_offsets
        save_settings(self._settings)
        invalidate_settings_cache()
        self.recalculate()

    @Slot(result="QVariantList")
    def getAzanEnabledList(self):
        azan_enabled = self._settings.get("azan_enabled", {})
        result = []
        for key in PRAYERS_WITH_AZAN:
            result.append({"key": key, "enabled": azan_enabled.get(key, True)})
        return result

    @Slot(str, bool)
    def setAzanEnabled(self, prayer_key: str, enabled: bool):
        new_azan = dict(self._settings.get("azan_enabled", {}))
        new_azan[prayer_key] = enabled
        self._settings = dict(self._settings)
        self._settings["azan_enabled"] = new_azan
        save_settings(self._settings)
        invalidate_settings_cache()

    @Slot(result=bool)
    def preloadAudio(self):
        muezzins = self._settings.get("muezzins", {})
        default_key = next(iter(muezzins), "افتراضي")
        default_audio = muezzins.get(default_key, "")
        if default_audio:
            preload_audio(resolve_azan_path(default_audio))
        return True

    @Slot(result="QVariantList")
    def getTimezones(self):
        global _TIMEZONES_CACHE
        if _TIMEZONES_CACHE is None:
            common = [
                ("Africa/Tunis", "تونس (أفريقيا/تونس)"),
                ("Africa/Cairo", "القاهرة (أفريقيا/القاهرة)"),
                ("Africa/Casablanca", "الدار البيضاء (أفريقيا/الدار البيضاء)"),
                ("Africa/Algiers", "الجزائر (أفريقيا/الجزائر)"),
                ("Africa/Tripoli", "طرابلس (أفريقيا/طرابلس)"),
                ("Africa/Khartoum", "الخرطوم (أفريقيا/الخرطوم)"),
                ("Africa/Mogadishu", "مقديشو (أفريقيا/مقديشو)"),
                ("Asia/Riyadh", "الرياض (آسيا/الرياض)"),
                ("Asia/Jeddah", "جدة (آسيا/جدة)"),
                ("Asia/Dubai", "دبي (آسيا/دبي)"),
                ("Asia/Abu_Dhabi", "أبو ظبي (آسيا/أبو ظبي)"),
                ("Asia/Doha", "الدوحة (آسيا/الدوحة)"),
                ("Asia/Kuwait", "الكويت (آسيا/الكويت)"),
                ("Asia/Bahrain", "المنامة (آسيا/البحرين)"),
                ("Asia/Muscat", "مسقط (آسيا/مسقط)"),
                ("Asia/Amman", "عمان (آسيا/عمان)"),
                ("Asia/Beirut", "بيروت (آسيا/بيروت)"),
                ("Asia/Damascus", "دمشق (آسيا/دمشق)"),
                ("Asia/Baghdad", "بغداد (آسيا/بغداد)"),
                ("Asia/Jerusalem", "القدس (آسيا/القدس)"),
                ("Asia/Tehran", "طهران (آسيا/طهران)"),
                ("Asia/Karachi", "كراتشي (آسيا/كراتشي)"),
                ("Asia/Dhaka", "دكا (آسيا/دكا)"),
                ("Asia/Jakarta", "جاكرتا (آسيا/جاكرتا)"),
                ("Asia/Kuala_Lumpur", "كوالالمبور (آسيا/كوالالمبور)"),
                ("Asia/Singapore", "سنغافورة (آسيا/سنغافورة)"),
                ("Europe/London", "لندن (أوروبا/لندن)"),
                ("Europe/Paris", "باريس (أوروبا/باريس)"),
                ("Europe/Berlin", "برلين (أوروبا/برلين)"),
                ("Europe/Moscow", "موسكو (أوروبا/موسكو)"),
                ("Europe/Istanbul", "إسطنبول (أوروبا/إسطنبول)"),
                ("America/New_York", "نيويورك (أمريكا/نيويورك)"),
                ("America/Los_Angeles", "لوس أنجلوس (أمريكا/لوس أنجلوس)"),
                ("America/Chicago", "شيكاغو (أمريكا/شيكاغو)"),
                ("America/Toronto", "تورنتو (أمريكا/تورنتو)"),
                ("UTC", "توقيت عالمي منسق (UTC)"),
            ]
            _TIMEZONES_CACHE = [{"code": code, "name": timezone_name(code, name)} for code, name in common]
        return _TIMEZONES_CACHE

    @Slot()
    def resetAllSettings(self):
        from .settings import DEFAULT_SETTINGS, save as save_settings, discover_builtin_muezzins, resolve_azan_path
        new_settings = dict(DEFAULT_SETTINGS)
        builtin = discover_builtin_muezzins()
        merged_muezzins = dict(new_settings.get("muezzins", {}))
        merged_muezzins.update(builtin)
        default_azan = os.path.join(os.path.dirname(__file__), "assets", "muezzins", "قطامي.mp3")
        if os.path.isfile(default_azan):
            merged_muezzins["افتراضي"] = default_azan
        merged_muezzins = {k: resolve_azan_path(v) for k, v in merged_muezzins.items()}
        new_settings["muezzins"] = merged_muezzins
        merged_audio = dict(new_settings.get("audio", {}))
        if not merged_audio.get("default"):
            merged_audio["default"] = default_azan
        merged_audio = {k: resolve_azan_path(v) for k, v in merged_audio.items()}
        new_settings["audio"] = merged_audio
        self._settings = new_settings
        save_settings(self._settings)
        invalidate_settings_cache()
        self.recalculate()

    @Slot(result=str)
    def exportSettings(self):
        import json
        from datetime import datetime
        import os
        from .settings import SETTINGS_FILE
        try:
            export_dir = os.path.join(os.path.dirname(SETTINGS_FILE), "exports")
            os.makedirs(export_dir, exist_ok=True)
            fname = f"prayer_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            fpath = os.path.join(export_dir, fname)
            # Atomic write: write to temp file then rename
            tmp = fpath + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            os.replace(tmp, fpath)
            return fpath
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("Export failed: %s", exc)
            return ""

    def _resolve_default_azan_path(self) -> str:
        """Resolve the default azan path with a robust fallback chain.
        Fallback chain:
        1. audio.default from settings
        2. muezzins['افتراضي'] (default muezzin)
        3. First available muezzin from settings
        4. Built-in default azan file (قطامي.mp3)
        """
        # 1. Try audio.default from settings
        audio = self._settings.get("audio", {})
        path = audio.get("default", "")
        if path:
            resolved = resolve_azan_path(path)
            if resolved:
                return resolved

        # 2. Try muezzins['افتراضي']
        muezzins = self._settings.get("muezzins", {})
        path = muezzins.get("افتراضي", "")
        if path:
            resolved = resolve_azan_path(path)
            if resolved:
                return resolved

        # 3. First available muezzin from settings
        if muezzins:
            for path in muezzins.values():
                resolved = resolve_azan_path(path)
                if resolved:
                    return resolved

        # 4. Built-in default azan file
        default_azan = os.path.join(os.path.dirname(__file__), "assets", "muezzins", "قطامي.mp3")
        if os.path.isfile(default_azan):
            return default_azan

        return ""

    @Slot(str)
    def importSettings(self, path: str):
        import json
        from .settings import save as save_settings, validate_and_coerce, _run_migrations, DEFAULT_SETTINGS
        try:
            # Validate file size (max 1MB)
            file_size = os.path.getsize(path)
            if file_size > 1024 * 1024:
                logger.warning("Import file too large: %d bytes", file_size)
                return

            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)

            if not isinstance(imported, dict):
                logger.warning("Imported settings are not a dict")
                return

            # Validate against schema - reject unknown top-level keys
            schema_keys = set(DEFAULT_SETTINGS.keys())
            imported_keys = set(imported.keys())
            unknown_keys = imported_keys - schema_keys
            if unknown_keys:
                logger.warning("Import contains unknown keys: %s", unknown_keys)
                return

            validated = validate_and_coerce(imported)
            validated = _run_migrations(validated)

            merged = dict(self._settings)
            merged.update(validated)
            self._settings = merged
            save_settings(self._settings)
            invalidate_settings_cache()
            self.recalculate()
            logger.info("Settings imported successfully from %s", path)
        except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.warning("Import failed: %s", exc)

    @Slot(str, result=str)
    def translate(self, key: str) -> str:
        """Translate a key via Python's i18n system (for QML, replaces qsTr)."""
        from .i18n import t
        return t(key)

    @Slot(str, result=str)
    def translatePrayer(self, key: str) -> str:
        """Translate a prayer key via Python's i18n system."""
        from .i18n import t_prayer
        return t_prayer(key)
