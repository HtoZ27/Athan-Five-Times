"""
Backend Controller - Python-QML bridge for the Athan application.
"""

import logging
import os
import subprocess
import threading
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, Signal, Slot, QTimer, QMetaObject, Q_ARG, Qt

from .prayer_calc import calculate, PRAYER_ORDER, _resolve_timezone
from .audio import play_azan, stop_azan, set_volume
from .translations import get_athkar
from .settings import (
    load as load_settings,
    save as save_settings,
    resolve_azan_path,
    set_autostart as _set_autostart,
)
from .settings import invalidate_cache as invalidate_settings_cache
from .i18n import (
    t,
    t_prayer,
    set_lang,
    format_date,
    country_name,
    city_name,
    credits_html,
    credits_title,
)
from .translations import calc_method_name, madhab_name, timezone_name, theme_name, u
from ._constants import PRAYERS_WITH_AZAN, DARK_THEMES, LANGS, LANG_NAMES, THEME_IDS, _display_key
from .prayer_calc import CALCULATION_METHODS
from .athkar_provider import AthkarProvider

logger = logging.getLogger(__name__)

_COUNTRY_LIST_CACHE: list | None = None
_CALC_METHODS_CACHE: list | None = None
_MADHABS_CACHE: list | None = None
_LANGUAGES_CACHE: list | None = None
_TIMEZONES_CACHE: list | None = None
_THEMES_CACHE: list | None = None

_COUNTRY_DATA_CACHE: tuple | None = None

# Serializes DND enable/disable command batches from racing daemon
# threads so a stale "disable" cannot interleave an "enable" sequence.
_DND_LOCK = threading.Lock()


def _ensure_country_data():
    global _COUNTRY_DATA_CACHE
    if _COUNTRY_DATA_CACHE is None:
        from .prayer_calc import _get_country_data

        _COUNTRY_DATA_CACHE = _get_country_data()
    return _COUNTRY_DATA_CACHE


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
    autoLocationStatus = Signal(str)
    settingChanged = Signal(str)
    backgroundEnabledChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = load_settings()
        self._result = None
        self._cached_next = None
        self._tomorrow_fajr = None
        self._tray_notify = None
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
        self._last_tray_info = ("", "", "")
        self._athkar_provider = AthkarProvider(self)

        self._azan_path = ""
        self._last_athkar_key = ""
        self._scheduled_timer = None
        self._recalc_timer = QTimer(self)
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.timeout.connect(self._do_recalc)
        self._recalc_pending = False
        self._recalc_location = False
        set_lang(self._settings.get("language", "ar"))
        self._setup_timers()
        QTimer.singleShot(0, self.recalculate)

    def _schedule_recalc(self, location_changed: bool = False):
        if location_changed:
            self._recalc_location = True
        if not self._recalc_pending:
            self._recalc_pending = True
            self._recalc_timer.start(150)

    def _do_recalc(self):
        self._recalc_pending = False
        self.recalculate()
        if getattr(self, "_recalc_location", False):
            self._recalc_location = False
            self.locationChanged.emit()

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
        self._settings = self._update_setting_immutable("autostart", bool(enabled))

    def _schedule_midnight(self):
        now = self._now()
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        secs = int((tomorrow - now).total_seconds())
        self._midnight_timer.stop()
        self._midnight_timer.start(secs * 1000 + 1500)

    def _update_clock(self):
        now = self._now()
        text = now.strftime("%H:%M:%S")
        if text != self._clock_text:
            self._clock_text = text
            self.clockChanged.emit(text)
        if not self._result:
            return
        try:
            if self._result.calc_date != now.date():
                self.recalculate()
                return
        except (AttributeError, TypeError):
            pass
        if self._cached_next is None or now >= self._cached_next[1]:
            self._cached_next = self._next_prayer(now)
            self.nextPrayerChanged.emit()
        self._update_countdown(now)
        self._check_pre_azan(now)
        self._update_tray_info()

    def _update_tray_info(self):
        try:
            info = self.getTrayInfo()
            next_text = info.get("next", "")
            remaining_text = info.get("remaining", "")
            pre_text = self._pre_alert_text if not self._settings.get("silent_mode", False) else ""
            if (next_text, remaining_text, pre_text) != self._last_tray_info:
                self._last_tray_info = (next_text, remaining_text, pre_text)
                self.trayInfoChanged.emit(next_text, remaining_text, pre_text)
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
        if not self._settings.get("pre_azan_enabled", True) or self._settings.get(
            "silent_mode", False
        ):
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
            self._pre_alert_text = t(
                "pre_alert", mins=str(mins_before), prayer=t_prayer(_display_key(name))
            )
            self.preAlertChanged.emit(self._pre_alert_text)
        elif now > dt and self._pre_alert_text:
            self._pre_alert_text = ""
            self.preAlertChanged.emit("")

    def _next_prayer(self, now):
        """Next prayer using the cached real tomorrow-fajr on wrap."""
        return self._result.next_prayer(now, tomorrow_fajr=getattr(self, "_tomorrow_fajr", None))

    def _now(self):
        """Current wall-clock time in the settings timezone (naive).

        All datetimes produced by PrayerResult are naive wall-clock in the
        settings zone, so every consumer (clock, countdown, tray, midnight
        rollover, scheduler, DND) must use this instead of datetime.now()
        to stay correct when the OS zone differs from the settings zone.
        """
        try:
            tz = _resolve_timezone(
                self._settings.get("timezone"), self._settings.get("longitude", 0.0)
            )
        except (ValueError, KeyError, TypeError):
            tz = None
        now = datetime.now(tz) if tz else datetime.now()
        return now.replace(tzinfo=None)

    def _check_prayer(self):
        if self._result is None:
            return
        now = self._now()
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
        d = self._result.as_dict()
        for name in remaining:
            elapsed = (now - d[name]).total_seconds()
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
            dnd_from = self._settings.get("dnd_from", 22)
            dnd_to = self._settings.get("dnd_to", 6)
            if self._in_dnd_time_range(dnd_from, dnd_to):
                self._enable_dnd(self._settings.get("dnd_duration", 20))

        if self._settings.get("azan_enabled", {}).get(prayer_key, True) and not silent_mode:
            audio_settings = self._settings.get("audio", {})
            audio_file = audio_settings.get(prayer_key, "") or audio_settings.get("default", "")
            if not audio_file:
                muezzins = self._settings.get("muezzins", {})
                if not self._azan_path:
                    self._azan_path = self._resolve_default_azan_path()
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

        if self._settings.get("athkar_popup_enabled", True):
            texts = get_athkar(prayer_key)
            if texts:
                is_dark = self._settings.get("theme", "dark") in DARK_THEMES
                dur = self._settings.get("athkar_popup_duration", 7) * 1000
                delay = self._settings.get("athkar_popup_delay", 60) * 1000
                if delay > 0:
                    QTimer.singleShot(
                        delay,
                        lambda pk=prayer_key, d=dur, txt=texts, dark=is_dark: self.athkarShown.emit(
                            pk, t("athkar_after_prayer"), d, "\n\n".join(txt[:2]), dark
                        ),
                    )
                else:
                    self.athkarShown.emit(
                        prayer_key, t("athkar_after_prayer"), dur, "\n\n".join(texts[:2]), is_dark
                    )

    def _notify_os(self, prayer_name: str):
        title = t("notif_prayer_title")
        body = t("notif_prayer_body", prayer=prayer_name)
        try:
            subprocess.Popen(["notify-send", title, body, "-t", "10000"])
        except (FileNotFoundError, PermissionError, OSError) as exc:
            logger.warning("Notification failed: %s", exc)
            notify = getattr(self, "_tray_notify", None)
            if callable(notify):
                try:
                    notify(title, body)
                except (AttributeError, RuntimeError, TypeError) as exc2:
                    logger.warning("Tray notification failed: %s", exc2)

    @Slot(bool)
    def _set_azan_playing(self, playing: bool):
        self._azan_playing = playing
        self.azanPlayingChanged.emit(playing)
        if not playing and self._settings.get("sleep_mode", True):
            self._schedule_next_prayer()

    def _on_azan_done(self):
        QMetaObject.invokeMethod(
            self, "_set_azan_playing", Qt.ConnectionType.QueuedConnection, Q_ARG(bool, False)
        )

    def _schedule_next_prayer(self):
        if not self._result:
            return
        now = self._now()
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
    def _apply_first_run_result(self):
        """Reload disk settings saved by first-run auto-location (GUI thread)."""
        try:
            from .settings import load as _reload_settings

            self._settings = _reload_settings()
            self.recalculate()
            self.locationChanged.emit()
        except (AttributeError, RuntimeError, OSError, ValueError) as exc:
            logger.warning("Failed to apply first-run location: %s", exc)

    @Slot()
    def _on_scheduled_timeout(self):
        name = self._scheduled_next_prayer
        self._scheduled_next_prayer = None
        if not name or name in self._notified_prayers or self._result is None:
            return
        try:
            prayer_dt = self._result.as_dict().get(name)
        except (AttributeError, KeyError, TypeError):
            prayer_dt = None
        if prayer_dt is not None:
            try:
                late = (self._now() - prayer_dt).total_seconds()
            except TypeError:
                late = 0
            if late > 60:
                self._notified_prayers.add(name)
                logger.info("Skipping late scheduled azan for %s (%.0fs late)", name, late)
                return
        self._notified_prayers.add(name)
        self._trigger_azan(name)

    def _send_dnd_notice(self, duration_minutes: int):
        try:
            subprocess.run(
                [
                    "notify-send",
                    "-t",
                    "3000",
                    t("notif_dnd_title"),
                    t("notif_dnd_body", mins=str(duration_minutes)),
                ],
                capture_output=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            pass

    def _run_dnd_cmds(self, enable: bool):
        with _DND_LOCK:
            self._run_dnd_cmds_locked(enable)

    def _run_dnd_cmds_locked(self, enable: bool):
        cmds = [
            ["dunstctl", "set-paused", "true" if enable else "false"],
            ["makoctl", "mode", "-a" if enable else "-r", "do-not-disturb"],
            [
                "gsettings",
                "set",
                "org.gnome.desktop.notifications",
                "show-banners",
                "false" if enable else "true",
            ],
            [
                "xfconf-query",
                "-c",
                "xfce4-notifyd",
                "-p",
                "/do-not-disturb",
                "-s",
                "true" if enable else "false",
            ],
            ["swaync-client", "-dnd-on" if enable else "-dnd-off"],
            [
                "qdbus",
                "org.kde.knotifications",
                "/Notify",
                "disableNotifications" if enable else "enableNotifications",
            ],
            [
                "gsettings",
                "set",
                "org.cinnamon.desktop.notifications",
                "show-banners",
                "false" if enable else "true",
            ],
            [
                "gsettings",
                "set",
                "org.mate.NotificationDaemon",
                "do-not-disturb",
                "true" if enable else "false",
            ],
            ["lxqt-notificationd", "--disable" if enable else "--enable"],
        ]
        for cmd in cmds:
            try:
                subprocess.run(cmd, capture_output=True, timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
                pass

    def _in_dnd_time_range(self, dnd_from: int, dnd_to: int) -> bool:
        now_hour = self._now().hour
        if dnd_from <= dnd_to:
            return dnd_from <= now_hour < dnd_to
        else:
            return now_hour >= dnd_from or now_hour < dnd_to

    def _enable_dnd(self, duration_minutes: int):
        threading.Thread(
            target=self._send_dnd_notice, args=(duration_minutes,), daemon=True
        ).start()
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
            if hasattr(self, "_clock_timer") and self._clock_timer:
                self._clock_timer.stop()
                self._clock_timer = None
        except RuntimeError:
            pass
        try:
            if hasattr(self, "_prayer_timer") and self._prayer_timer:
                self._prayer_timer.stop()
                self._prayer_timer = None
        except RuntimeError:
            pass
        try:
            if hasattr(self, "_midnight_timer") and self._midnight_timer:
                self._midnight_timer.stop()
        except RuntimeError:
            pass
        try:
            if hasattr(self, "_dnd_timer") and self._dnd_timer:
                self._dnd_timer.stop()
                self._dnd_timer = None
        except RuntimeError:
            pass
        try:
            if hasattr(self, "_scheduled_timer") and self._scheduled_timer:
                self._scheduled_timer.stop()
                self._scheduled_timer = None
        except RuntimeError:
            pass
        try:
            if hasattr(self, "_recalc_timer") and self._recalc_timer:
                self._recalc_timer.stop()
                self._recalc_timer = None
        except RuntimeError:
            pass
        self._stop_event.set()
        stop_azan()

    def recalculate(self):
        s = self._settings
        today = self._now().date()
        self._result = calculate(
            s.get("latitude", 36.8),
            s.get("longitude", 10.18),
            target_date=today,
            method_name=s.get("method", "Tunisia"),
            madhab=s.get("madhab", "shafi"),
            tz_name=s.get("timezone", None),
            offsets=s.get("offsets", None),
        )
        if self._result is None:
            logger.warning("Prayer calculation failed")
            self._cached_next = None
            self._tomorrow_fajr = None
            self._prayer_times_cache = None
            self._prayer_times_cache_key = None
            self._countdown_text = ""
            self._next_name = "--"
            self._gregorian_date = ""
            self._hijri_date = ""
            self.dateChanged.emit()
            self.nextPrayerChanged.emit()
            self.countdownChanged.emit("")
            self.prayerTimesChanged.emit()
            return
        self._cached_next = None
        self._prayer_times_cache = None
        self._prayer_times_cache_key = None
        self._schedule_midnight()
        today = self._now().date()
        try:
            tomorrow_res = calculate(
                s.get("latitude", 36.8),
                s.get("longitude", 10.18),
                target_date=today + timedelta(days=1),
                method_name=s.get("method", "Tunisia"),
                madhab=s.get("madhab", "shafi"),
                tz_name=s.get("timezone", None),
                offsets=s.get("offsets", None),
            )
            self._tomorrow_fajr = tomorrow_res.fajr if tomorrow_res else None
        except (ValueError, TypeError, KeyError, AttributeError):
            self._tomorrow_fajr = None
        date_part, hijri_part = format_date(today, s.get("hijri_day_offset", 0))
        self._gregorian_date = date_part
        self._hijri_date = hijri_part
        self.dateChanged.emit()
        now = self._now()
        cached = self._next_prayer(now)
        if cached and cached[0] not in ("sunrise",) and cached[0] != self._last_athkar_key:
            self._last_athkar_key = cached[0]
            self._athkar_provider.setPrayerAthkar(cached[0], t("athkar_after_prayer"))
        elif not cached or cached[0] in ("sunrise",):
            self._last_athkar_key = ""
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
    def getNextPrayerKey(self):
        if self._cached_next:
            return self._cached_next[0]
        return "fajr"

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
        next_key = self._cached_next[0] if self._cached_next else ""
        cache_key = (
            self._result.calc_date.isoformat(),
            self._settings.get("language"),
            self._settings.get("time_format", "12h"),
            next_key,
        )
        if self._prayer_times_cache is not None and self._prayer_times_cache_key == cache_key:
            return self._prayer_times_cache

        times = self._result.as_dict()
        result = []
        for key in PRAYER_ORDER:
            result.append(
                {
                    "name": t_prayer(_display_key(key)),
                    "time": times[key].strftime(
                        "%I:%M %p" if self._settings.get("time_format", "12h") == "12h" else "%H:%M"
                    ),
                    "key": key,
                    "isNext": key == next_key,
                }
            )
        self._prayer_times_cache = result
        self._prayer_times_cache_key = cache_key
        return result

    @Slot()
    def stopAzan(self):
        self._stop_event.set()
        stop_azan()
        self._set_azan_playing(False)

    @Slot()
    def quitApp(self):
        """Full application exit, wired to the window X button.

        Stops any playing azan, persists settings, then quits the event
        loop so the process terminates instead of hiding to the tray.
        """
        try:
            self.stopAzan()
        except (RuntimeError, AttributeError):
            pass
        try:
            save_settings(self._settings)
        except (OSError, TypeError, ValueError):
            pass
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                app.quit()
        except (RuntimeError, AttributeError):
            pass

    @Slot(result=bool)
    def isAzanPlaying(self):
        return self._azan_playing

    @Slot(result="QVariant")
    def getSettings(self):
        from copy import deepcopy

        return deepcopy(self._settings)

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
        Uses deepcopy for nested dicts to prevent shared mutable state.
        """
        from copy import deepcopy

        new_settings = dict(self._settings)
        for key, value in updates.items():
            if "." in key:
                parts = key.split(".")
                target = new_settings
                for part in parts[:-1]:
                    if part not in target:
                        target[part] = {}
                    target[part] = deepcopy(target.get(part, {}))
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
            _methods, _cntrs, _city_db = _ensure_country_data()
            cities = _city_db.get(country, [])
            city_map = {eng_name: (lat, lon) for eng_name, lat, lon in cities}
            if city in city_map:
                lat, lon = city_map[city]
                self._settings = self._update_settings_batch({"latitude": lat, "longitude": lon})
                return
            if cities:
                logger.warning("City %r not in database, using first city of %s", city, country)
                self._settings = self._update_settings_batch(
                    {"latitude": cities[0][1], "longitude": cities[0][2]}
                )
                return

    def _apply_auto_coords(
        self,
        country: str,
        city: str,
        latitude: float,
        longitude: float,
        timezone: str | None = None,
        clear_custom: bool = True,
    ) -> bool:
        """Apply auto-detected coordinates with common logic.

        Returns False (leaving existing settings untouched) when the
        country code is empty or unknown — this keeps raw codes and
        garbage out of the settings and the UI.
        """
        _methods, cntrs, _city_db = _ensure_country_data()
        if not country or country not in cntrs:
            logger.warning("Ignoring auto-location with unknown country: %r", country)
            return False
        try:
            lat_f, lon_f = float(latitude), float(longitude)
        except (ValueError, TypeError):
            logger.warning("Ignoring auto-location with bad coords: %r/%r", latitude, longitude)
            return False
        if (
            (lat_f == 0.0 and lon_f == 0.0)
            or not (-90 <= lat_f <= 90)
            or not (-180 <= lon_f <= 180)
        ):
            logger.warning("Ignoring auto-location out of range: %r/%r", latitude, longitude)
            return False
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
        return True

    @Slot()
    def resetToAutoCoordinates(self):
        from .location import detect_async

        def _on_result(loc):
            self._pending_location = loc
            QMetaObject.invokeMethod(
                self, "_process_auto_location", Qt.ConnectionType.QueuedConnection
            )

        self._pending_location = None
        self.autoLocationStatus.emit("detecting")
        detect_async(_on_result)

    @Slot()
    def _process_auto_location(self):
        loc = self._pending_location
        self._pending_location = None
        if loc:
            ok = self._apply_auto_coords(
                loc.get("country_code", "SA"),
                loc.get("city", "Mecca"),
                loc.get("latitude", 21.4225),
                loc.get("longitude", 39.8262),
                loc.get("timezone"),
            )
            if ok:
                try:
                    save_settings(self._settings)
                except (OSError, TypeError, ValueError) as exc:
                    logger.error("Failed to save after auto-location: %s", exc)
                self.autoLocationStatus.emit("success")
                return
            logger.warning("Auto-location rejected, falling back to saved city")
        self.autoLocationStatus.emit("failed")

        country = self._settings.get("country")
        city = self._settings.get("city")
        if country and country != "none":
            _methods, _cntrs, _city_db = _ensure_country_data()
            cities = _city_db.get(country, [])
            for eng_name, lat, lon in cities:
                if eng_name == city:
                    self._apply_auto_coords(country, city, lat, lon, clear_custom=True)
                    return
            if cities:
                self._apply_auto_coords(
                    country, cities[0][0], cities[0][1], cities[0][2], clear_custom=True
                )
                return

        self._apply_auto_coords("SA", "Mecca", 21.4225, 39.8262, "Asia/Riyadh", True)

    def _save_theme(self, theme_code: str, emit_signal: bool = True) -> None:
        """Internal method to save theme setting.

        Args:
            theme_code: Theme code to save
            emit_signal: Whether to emit themeChanged signal
        """
        if theme_code not in THEME_IDS:
            logger.warning("Invalid theme: %s, must be one of %s", theme_code, THEME_IDS)
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
        old_lang = getattr(self, "_stored_old_lang", None)
        old_theme = getattr(self, "_stored_old_theme", None)
        if old_lang is None:
            old_lang = self._settings.get("language", "ar")
        if old_theme is None:
            old_theme = self._settings.get("theme", "dark")
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
            self._clear_display_caches()
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

    def persistTheme(self, theme_code: str) -> None:
        """Save theme to disk without emitting signals (signal-safe sync from ThemeController)."""
        if theme_code not in THEME_IDS:
            logger.warning("Invalid theme: %s, must be one of %s", theme_code, THEME_IDS)
            return
        self._settings = self._update_setting_immutable("theme", theme_code)
        try:
            save_settings(self._settings)
            logger.info("Theme persisted: %s", theme_code)
        except (OSError, TypeError, ValueError) as exc:
            logger.error("Failed to persist theme: %s", exc)

    @Slot()
    def storeSettingsSnapshot(self):
        from copy import deepcopy

        self._settings_snapshot = deepcopy(self._settings)
        self._stored_old_lang = self._settings.get("language", "ar")
        self._stored_old_theme = self._settings.get("theme", "dark")

    @Slot()
    def restoreSettingsSnapshot(self):
        if hasattr(self, "_settings_snapshot") and self._settings_snapshot:
            old_lang = self._settings_snapshot.get("language", "ar")
            old_theme = self._settings_snapshot.get("theme", "dark")
            self._settings = self._settings_snapshot
            self._settings_snapshot = None
            try:
                _set_autostart(bool(self._settings.get("autostart", False)))
            except (OSError, TypeError, ValueError, PermissionError) as exc:
                logger.warning("Failed to revert autostart file: %s", exc)
            try:
                from .i18n import set_lang

                set_lang(old_lang)
            except (ImportError, ValueError, AttributeError) as exc:
                logger.warning("Failed to revert language: %s", exc)
            self.themeChanged.emit(old_theme)
            self.languageChanged.emit()
            self._clear_display_caches()
            try:
                set_volume(self._settings.get("volume", 1.0))
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                logger.warning("Failed to revert volume: %s", exc)
            self.settingChanged.emit("show_tray")
            self.recalculate()
            self.locationChanged.emit()
            # Persist the reverted state so immediately-written settings
            # (offsets, theme) do not keep cancelled values on disk.
            try:
                save_settings(self._settings)
            except (OSError, TypeError, ValueError) as exc:
                logger.error("Failed to save after restore: %s", exc)

    @Slot(str, "QVariant")
    def updateSetting(self, key: str, value):
        try:
            from PySide6.QtQml import QJSValue

            if isinstance(value, QJSValue):
                value = value.toVariant()
        except (ImportError, AttributeError, RuntimeError):
            pass
        if key == "country":
            _methods, _cntrs, _db = _ensure_country_data()
            if not value or value not in _cntrs:
                logger.warning("Ignoring unknown country code: %r", value)
                return
        elif key == "city" and value:
            _methods, _cntrs, _db = _ensure_country_data()
            known = {eng for eng, _, _ in _db.get(self._settings.get("country", ""), [])}
            if known and value not in known:
                logger.warning(
                    "Ignoring unknown city for %s: %r", self._settings.get("country"), value
                )
                return
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
        if key == "theme":
            if value not in THEME_IDS:
                logger.warning("Invalid theme: %s, must be one of %s", value, THEME_IDS)
                return
            self._settings = self._update_setting_immutable("theme", value)
            try:
                save_settings(self._settings)
                logger.info("Theme saved via updateSetting: %s", value)
            except (OSError, TypeError, ValueError) as exc:
                logger.error("Failed to save theme: %s", exc)
            self.themeChanged.emit(value)
            self.settingChanged.emit(key)
            return
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
            from .location import clear_location_cache

            clear_location_cache()
            self._auto_update_coordinates()
        if key in ("country", "city", "latitude", "longitude", "timezone"):
            self._schedule_recalc(location_changed=True)
        elif key in ("method", "madhab", "hijri_day_offset"):
            self._schedule_recalc()
        elif key == "volume":
            set_volume(value)
        elif key == "background_enabled":
            self.backgroundEnabledChanged.emit(value)
        elif key in ("language", "time_format"):
            self._prayer_times_cache = None
            self._prayer_times_cache_key = None
            if key == "time_format":
                self.prayerTimesChanged.emit()
        if key in ("pre_azan_minutes", "pre_azan_enabled"):
            self._pre_notified.clear()
        self.settingChanged.emit(key)

    @Slot(result="QVariantList")
    def getCountryList(self):
        global _COUNTRY_LIST_CACHE
        if _COUNTRY_LIST_CACHE is None:
            _methods, _cntrs, _city_db = _ensure_country_data()
            items = []
            for code in _cntrs:
                items.append({"code": code, "name": country_name(code)})
            items.sort(key=lambda x: x["name"])
            _COUNTRY_LIST_CACHE = items
        return _COUNTRY_LIST_CACHE

    @Slot(str, result="QVariantList")
    def getCitiesForCountry(self, code: str):
        _methods, _cntrs, _city_db = _ensure_country_data()
        items = []
        for eng_name, lat, lon in _city_db.get(code, []):
            items.append(
                {
                    "name": city_name(eng_name),
                    "engName": eng_name,
                    "lat": lat,
                    "lon": lon,
                    "countryCode": code,
                }
            )
        return items

    @Slot(str, result="QVariantList")
    def getCityNamesForCountry(self, code: str):
        _methods, _cntrs, _city_db = _ensure_country_data()
        items = []
        for eng_name, lat, lon in _city_db.get(code, []):
            items.append({"name": city_name(eng_name), "engName": eng_name, "countryCode": code})
        return items

    @Slot(str, str, int, int, result="QVariant")
    def searchCitiesPaginated(
        self, country_code: str, query: str = "", offset: int = 0, limit: int = 50
    ):
        _methods, _cntrs, _city_db = _ensure_country_data()
        cities = _city_db.get(country_code, [])
        if query:
            lower = query.lower()
            matched = []
            for eng_name, lat, lon in cities:
                if lower in eng_name.lower() or lower in city_name(eng_name).lower():
                    matched.append((eng_name, lat, lon))
            cities = matched
        total = len(cities)
        page = cities[offset : offset + limit]
        items = [
            {"name": city_name(eng_name), "engName": eng_name, "countryCode": country_code}
            for eng_name, lat, lon in page
        ]
        return {"items": items, "total": total, "offset": offset, "limit": limit}

    @Slot(str, str, result="QVariant")
    def getCityCoords(self, country_code: str, city_eng_name: str):
        _methods, _cntrs, _city_db = _ensure_country_data()
        for eng_name, lat, lon in _city_db.get(country_code, []):
            if eng_name == city_eng_name:
                return {"lat": lat, "lon": lon}
        return None

    @Slot(result="QVariantList")
    def getCalcMethods(self):
        global _CALC_METHODS_CACHE
        if _CALC_METHODS_CACHE is None:
            _CALC_METHODS_CACHE = [
                {"display": calc_method_name(k), "key": k} for k in CALCULATION_METHODS
            ]
        return _CALC_METHODS_CACHE

    @Slot(str, result="QString")
    def getDefaultMethod(self, country_code: str):
        _methods, _cntrs, _city_db = _ensure_country_data()
        return _methods.get(country_code, "")

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
            _LANGUAGES_CACHE = [
                {"code": code, "name": LANG_NAMES.get(code, code)} for code in LANGS
            ]
        return _LANGUAGES_CACHE

    @Slot()
    def clearCaches(self):
        global _COUNTRY_LIST_CACHE, _CALC_METHODS_CACHE, _MADHABS_CACHE
        global _TIMEZONES_CACHE, _THEMES_CACHE, _COUNTRY_DATA_CACHE
        global _LANGUAGES_CACHE
        _COUNTRY_LIST_CACHE = None
        _CALC_METHODS_CACHE = None
        _MADHABS_CACHE = None
        _TIMEZONES_CACHE = None
        _THEMES_CACHE = None
        _COUNTRY_DATA_CACHE = None
        _LANGUAGES_CACHE = None
        self._prayer_times_cache = None
        self._prayer_times_cache_key = None
        self._clear_trans_caches()
        from .prayer_calc import clear_country_data as _clear_cd

        _clear_cd()
        from .prayer_calc import clear_calculation_cache as _clear_calc

        _clear_calc()
        from .location import clear_country_rev_cache

        clear_country_rev_cache()

    @Slot(result="QVariantList")
    def getThemes(self):
        global _THEMES_CACHE
        if _THEMES_CACHE is None:
            _THEMES_CACHE = [{"code": code, "name": theme_name(code)} for code in THEME_IDS]
        return _THEMES_CACHE

    def getTrayInfo(self):
        if not self._result or not self._cached_next:
            return {"next": "", "remaining": ""}
        now = self._now()
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
        if not resolved or not os.path.isfile(resolved):
            logger.warning("Preview requested for missing audio file: %r", path)
            return
        self._stop_event.set()
        stop_azan()
        self._stop_event.clear()
        self._set_azan_playing(True)
        play_azan(resolved, fade_in=False, stop_flag=self._stop_event, on_done=self._on_azan_done)

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
        removed = [k for k in (self._settings.get("removed_muezzins", []) or []) if k != name]
        self._settings = dict(self._settings)
        self._settings["muezzins"] = new_muezzins
        self._settings["removed_muezzins"] = removed

    def _resolve_muezzin_key(self, name: str) -> str:
        """Map a display name (possibly translated, e.g. 'Default') back
        to the stored settings key (e.g. 'افتراضي')."""
        muezzins = self._settings.get("muezzins", {})
        if name in muezzins:
            return name
        for key in muezzins:
            if key == "افتراضي" and u(key) == name:
                return key
        return name

    @Slot(str)
    def removeMuezzin(self, name: str):
        from .settings import discover_builtin_muezzins

        key = self._resolve_muezzin_key(name)
        new_muezzins = dict(self._settings.get("muezzins", {}))
        new_muezzins.pop(key, None)
        removed = list(self._settings.get("removed_muezzins", []) or [])
        if key in discover_builtin_muezzins() or key == "افتراضي":
            if key not in removed:
                removed.append(key)
        self._settings = dict(self._settings)
        self._settings["muezzins"] = new_muezzins
        self._settings["removed_muezzins"] = removed

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
                parent, "اختر ملفًا صوتيًا", "", "Audio Files (*.mp3 *.wav *.ogg *.flac)"
            )
            if path:
                path = path.removeprefix("file://")
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
        self.prayerTimesChanged.emit()

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

    @Slot(result="QVariantList")
    def getTimezones(self):
        global _TIMEZONES_CACHE
        if _TIMEZONES_CACHE is None:
            common = [
                ("Africa/Tunis", "تونس"),
                ("Africa/Cairo", "القاهرة"),
                ("Africa/Casablanca", "الدار البيضاء"),
                ("Africa/Algiers", "الجزائر"),
                ("Africa/Tripoli", "طرابلس"),
                ("Africa/Khartoum", "الخرطوم"),
                ("Africa/Mogadishu", "مقديشو"),
                ("Asia/Riyadh", "الرياض"),
                ("Asia/Jeddah", "جدة"),
                ("Asia/Dubai", "دبي"),
                ("Asia/Abu_Dhabi", "أبو ظبي"),
                ("Asia/Doha", "الدوحة"),
                ("Asia/Kuwait", "الكويت"),
                ("Asia/Bahrain", "المنامة"),
                ("Asia/Muscat", "مسقط"),
                ("Asia/Amman", "عمان"),
                ("Asia/Beirut", "بيروت"),
                ("Asia/Damascus", "دمشق"),
                ("Asia/Baghdad", "بغداد"),
                ("Asia/Jerusalem", "القدس"),
                ("Asia/Tehran", "طهران"),
                ("Asia/Karachi", "كراتشي"),
                ("Asia/Dhaka", "دكا"),
                ("Asia/Jakarta", "جاكرتا"),
                ("Asia/Kuala_Lumpur", "كوالالمبور"),
                ("Asia/Singapore", "سنغافورة"),
                ("Europe/London", "لندن"),
                ("Europe/Paris", "باريس"),
                ("Europe/Berlin", "برلين"),
                ("Europe/Moscow", "موسكو"),
                ("Europe/Istanbul", "إسطنبول"),
                ("America/New_York", "نيويورك"),
                ("America/Los_Angeles", "لوس أنجلوس"),
                ("America/Chicago", "شيكاغو"),
                ("America/Toronto", "تورنتو"),
                ("UTC", "توقيت عالمي منسق (UTC)"),
            ]
            _TIMEZONES_CACHE = [
                {"code": code, "name": timezone_name(code, name)} for code, name in common
            ]
        return _TIMEZONES_CACHE

    @Slot()
    def resetAllSettings(self):
        from .settings import (
            DEFAULT_SETTINGS,
            save as save_settings,
            discover_builtin_muezzins,
            resolve_azan_path,
        )

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
        from .settings import SETTINGS_FILE

        try:
            export_dir = os.path.join(os.path.dirname(SETTINGS_FILE), "exports")
            os.makedirs(export_dir, exist_ok=True)
            fname = f"prayer_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            fpath = os.path.join(export_dir, fname)
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
        audio = self._settings.get("audio", {})
        path = audio.get("default", "")
        if path:
            resolved = resolve_azan_path(path)
            if resolved:
                return resolved

        muezzins = self._settings.get("muezzins", {})
        path = muezzins.get("افتراضي", "")
        if path:
            resolved = resolve_azan_path(path)
            if resolved:
                return resolved

        if muezzins:
            for path in muezzins.values():
                resolved = resolve_azan_path(path)
                if resolved:
                    return resolved

        default_azan = os.path.join(os.path.dirname(__file__), "assets", "muezzins", "قطامي.mp3")
        if os.path.isfile(default_azan):
            return default_azan

        return ""

    @Slot(str)
    def importSettings(self, path: str):
        import json
        from .settings import (
            save as save_settings,
            validate_and_coerce,
            _run_migrations,
            DEFAULT_SETTINGS,
        )

        try:
            file_size = os.path.getsize(path)
            if file_size > 1024 * 1024:
                logger.warning("Import file too large: %d bytes", file_size)
                return

            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)

            if not isinstance(imported, dict):
                logger.warning("Imported settings are not a dict")
                return

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

    _TRANS_CACHE: dict[str, str] = {}
    _TRANS_PRAYER_CACHE: dict[str, str] = {}
    _TRANS_CACHE_MAX = 500

    @classmethod
    def _clear_trans_caches(cls):
        cls._TRANS_CACHE.clear()
        cls._TRANS_PRAYER_CACHE.clear()

    def _clear_display_caches(self):
        """Clear every language-dependent display cache.

        Covers translation caches, localized list caches and this
        instance's prayer-times cache. Used on language switch (commit),
        settings restore (cancel) and manual cache clearing.
        """
        self._clear_trans_caches()
        global \
            _COUNTRY_LIST_CACHE, \
            _CALC_METHODS_CACHE, \
            _MADHABS_CACHE, \
            _THEMES_CACHE, \
            _TIMEZONES_CACHE
        _COUNTRY_LIST_CACHE = None
        _CALC_METHODS_CACHE = None
        _MADHABS_CACHE = None
        _THEMES_CACHE = None
        _TIMEZONES_CACHE = None
        self._prayer_times_cache = None
        self._prayer_times_cache_key = None

    @Slot(str, result=str)
    def translate(self, key: str) -> str:
        from .i18n import current_code

        k = f"{current_code()}:{key}"
        cached = self._TRANS_CACHE.get(k)
        if cached is not None:
            return cached
        from .i18n import t

        result = t(key)
        if len(self._TRANS_CACHE) >= self._TRANS_CACHE_MAX:
            self._TRANS_CACHE.clear()
        self._TRANS_CACHE[k] = result
        return result

    @Slot(str, result=str)
    def translatePrayer(self, key: str) -> str:
        from .i18n import current_code

        k = f"p:{current_code()}:{key}"
        cached = self._TRANS_PRAYER_CACHE.get(k)
        if cached is not None:
            return cached
        from .i18n import t_prayer

        result = t_prayer(key)
        if len(self._TRANS_PRAYER_CACHE) >= self._TRANS_CACHE_MAX:
            self._TRANS_PRAYER_CACHE.clear()
        self._TRANS_PRAYER_CACHE[k] = result
        return result
