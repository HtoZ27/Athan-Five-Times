"""
Main entry point for QML-based Athan Five Times Prayer Application.
"""

import sys
import os
import logging
import gc

os.environ["GTK_MODULES"] = ""
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
os.environ.setdefault("QT_QPA_PLATFORMTHEME", "gtk3")
os.environ["QT_ACCESSIBILITY"] = "0"
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Fusion"


def apply_render_env():
    """Apply the render backend/loop setting before Qt initializes.

    Reads the stored settings lightly (no engine needed). An explicit user
    export always wins; invalid values silently fall back to auto.
    """
    try:
        import json

        with open(SETTINGS_FILE, encoding="utf-8") as f:
            stored = json.load(f)
    except (OSError, ValueError):
        stored = {}
    backend = str(stored.get("render_backend", "auto")).lower()
    if os.environ.get("QT_QUICK_BACKEND") is None and backend == "software":
        os.environ["QT_QUICK_BACKEND"] = "software"
    loop = str(stored.get("render_loop", "auto")).lower()
    if os.environ.get("QSG_RENDER_LOOP") is None and loop in ("threaded", "basic"):
        os.environ["QSG_RENDER_LOOP"] = loop


from PySide6.QtCore import QUrl, QTimer, Qt, QLockFile
from PySide6.QtGui import QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtQuickControls2 import QQuickStyle

from .settings import load as load_settings, save as save_settings, APP_VERSION
from .settings import SETTINGS_FILE
from .location import detect_async
from .i18n import t, set_lang
from .l10n import LanguageManager
from .backend_controller import PrayerEngine
from .theme_controller import ThemeController
from .audio import set_volume

apply_render_env()

try:
    from .memory_profiler import start_profiling, stop_profiling

    _MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    _MEMORY_PROFILER_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QML_DIR = os.path.join(BASE_DIR, "qml")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


def should_hide_to_tray(tray_available: bool, tray_visible: bool) -> bool:
    """Hide-to-tray only when the tray can actually host the icon.

    On desktops without a tray (plain Wayland/GNOME) or with the tray
    icon disabled, hiding would strand the app with no window and no
    icon — minimize instead.
    """
    return bool(tray_available and tray_visible)


class QmlAthanApp:
    def __init__(self, argv, azan_path):
        QQuickStyle.setStyle("Fusion")
        self._app = QApplication(argv)
        self._app.setDesktopFileName("com.azanprayer.app")
        self._app.setQuitOnLastWindowClosed(False)

        icon_path = os.path.join(ASSETS_DIR, "kaaba.svg")
        if os.path.isfile(icon_path):
            self._app.setWindowIcon(QIcon(icon_path))

        fonts_dir = os.path.join(ASSETS_DIR, "fonts")
        if os.path.isdir(fonts_dir):
            wanted = ("cairo", "ibmplexsansarabic")
            for fname in sorted(os.listdir(fonts_dir)):
                if fname.lower().endswith(".ttf") and fname.lower().replace("-", "").replace(
                    "_", ""
                ).startswith(wanted):
                    QFontDatabase.addApplicationFont(os.path.join(fonts_dir, fname))

        font = QFont("Cairo", 14)
        if not font.exactMatch():
            font = QFont("Sans", 14)
        self._app.setFont(font)

        settings = load_settings()
        if settings.get("first_run"):
            new_settings = dict(settings)
            new_settings["first_run"] = False
            new_settings["last_version"] = APP_VERSION
            save_settings(new_settings)
            settings = new_settings
            self._auto_configure(settings)
        else:
            set_lang(settings.get("language", "ar"))

        set_volume(settings.get("volume", 1.0))

        self._azan_path = azan_path
        self._tray = None
        self._tray_original_icon = QIcon()
        self._azan_flash_timer = QTimer()
        self._azan_flash_timer.setInterval(500)
        self._azan_flash_timer.timeout.connect(self._toggle_tray_icon)
        self._tray_icon_visible = True
        self._engine = QQmlApplicationEngine()
        self._engine.addImportPath(QML_DIR)

        from .settings import SETTINGS_DIR

        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
        except OSError:
            pass
        self._instance_lock = QLockFile(os.path.join(SETTINGS_DIR, "app.lock"))
        self._instance_lock.setStaleLockTime(30)
        if not self._instance_lock.tryLock(100):
            logger.warning("Another instance is already running — exiting")
            try:
                import subprocess

                subprocess.run(
                    ["notify-send", "-t", "3000", t("app_name"), "يعمل التطبيق بالفعل"],
                    capture_output=True,
                    timeout=5,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError, OSError):
                pass
            sys.exit(0)

        qmlRegisterSingletonType(
            QUrl.fromLocalFile(os.path.join(QML_DIR, "Theme.qml")), "Theme", 1, 0, "Theme"
        )

        self._theme_controller = ThemeController()
        self._prayer_engine = PrayerEngine()
        self._l10n = LanguageManager(initial_lang=settings.get("language", "ar"))

        ctx = self._engine.rootContext()
        ctx.setContextProperty("prayerEngine", self._prayer_engine)
        ctx.setContextProperty("backendController", self._prayer_engine)
        ctx.setContextProperty("themeController", self._theme_controller)
        ctx.setContextProperty("l10n", self._l10n)
        ctx.setContextProperty("appVersion", APP_VERSION)
        ctx.setContextProperty("trayAvailable", False)

        self._prayer_engine.themeChanged.connect(self._on_prayer_theme_changed)
        self._theme_controller.themeChanged.connect(self._prayer_engine.persistTheme)
        self._prayer_engine.settingChanged.connect(self._on_setting_changed)
        self._app.aboutToQuit.connect(self._hide_tray)
        self._l10n.languageChanged.connect(self._on_language_changed)

        qml_file = os.path.join(QML_DIR, "main.qml")
        if not os.path.isfile(qml_file):
            logger.error("QML file not found: %s", qml_file)
            sys.exit(1)

        self._engine.load(QUrl.fromLocalFile(qml_file))
        if not self._engine.rootObjects():
            logger.error("Failed to load QML")
            sys.exit(1)

        gc.collect()

        self._app.setApplicationName(t("app_name"))

        self._restore_window_geometry()

        self._prayer_engine.azanPlayingChanged.connect(self._on_azan_playing_changed)

        QTimer.singleShot(0, self._delayed_init)
        QTimer.singleShot(0, self._setup_tray)

    def _auto_configure(self, settings: dict):
        logger.info("First run – attempting auto-location…")

        def _on_location_detected(loc):
            if not loc:
                logger.info("Offline or location unavailable; using defaults (Tunis)")
                result = dict(settings)
                result["first_run"] = False
                save_settings(result)
                return

            lat, lon = loc["latitude"], loc["longitude"]
            city_ip = loc.get("city", "")
            tz = loc.get("timezone", "")
            country_code = (loc.get("country_code", "") or "TN").upper()

            from .prayer_calc import COUNTRY_CITIES, COUNTRY_METHODS, COUNTRIES

            if country_code not in COUNTRIES:
                logger.warning(
                    "Auto-location returned unknown country %r, using TN",
                    loc.get("country_code", ""),
                )
                country_code = "TN"

            result = dict(settings)
            result["country"] = country_code
            result["latitude"] = lat
            result["longitude"] = lon

            best_city, best_dist = None, float("inf")
            best_lat, best_lon = lat, lon
            import math

            cities = COUNTRY_CITIES.get(country_code, [])
            for eng_name, clat, clon in cities:
                d = math.hypot(lat - clat, lon - clon)
                if d < best_dist:
                    best_dist = d
                    best_city = eng_name
                    best_lat, best_lon = clat, clon
            if best_city and best_dist < 2:
                result["city"] = best_city
                result["latitude"] = best_lat
                result["longitude"] = best_lon
            else:
                result["city"] = city_ip
                result["latitude"] = best_lat
                result["longitude"] = best_lon
            result["timezone"] = tz
            method = COUNTRY_METHODS.get(country_code, "وزارة الشؤون الدينية التونسية")
            result["method"] = method
            logger.info(
                "Auto-located: %s/%s (%.4f, %.4f) %s", country_code, result["city"], lat, lon, tz
            )
            result["first_run"] = False
            save_settings(result)
            # Hand off to the GUI thread: direct engine calls from this
            # daemon thread would emit Qt signals off-thread.
            try:
                from PySide6.QtCore import QMetaObject

                engine = getattr(self, "_prayer_engine", None)
                if engine is not None:
                    QMetaObject.invokeMethod(
                        engine, "_apply_first_run_result", Qt.ConnectionType.QueuedConnection
                    )
            except (AttributeError, RuntimeError) as exc:
                logger.warning("Failed to apply auto-location live: %s", exc)

        detect_async(_on_location_detected)

    def _restore_window_geometry(self):
        root = self._engine.rootObjects()
        if not root:
            return
        settings = load_settings()
        geom = settings.get("window_geometry")
        if isinstance(geom, list) and len(geom) == 4:
            try:
                root[0].setGeometry(*geom)
            except (AttributeError, RuntimeError, ValueError) as exc:
                logger.debug("Could not restore window geometry: %s", exc)

    def _save_window_geometry(self):
        root = self._engine.rootObjects()
        if not root:
            return
        try:
            w = root[0]
            geom = [w.x(), w.y(), w.width(), w.height()]
            settings = load_settings()
            new_settings = dict(settings)
            new_settings["window_geometry"] = geom
            save_settings(new_settings)
        except (OSError, TypeError, ValueError, AttributeError) as exc:
            logger.debug("Could not save window geometry: %s", exc)

    def _delayed_init(self):
        root = self._engine.rootObjects()
        if root:
            try:
                root[0].closing.connect(self._save_window_geometry)
            except (AttributeError, RuntimeError):
                pass

    def _setup_tray(self):
        try:
            from PySide6.QtWidgets import QSystemTrayIcon, QMenu
            from PySide6.QtGui import QAction

            if not QSystemTrayIcon.isSystemTrayAvailable():
                logger.info("System tray not available")
                return
            tray_icon = QIcon()
            try:
                from PySide6.QtGui import QGuiApplication

                dpr = 1.0
                try:
                    screens = QGuiApplication.screens()
                    if screens:
                        dpr = screens[0].devicePixelRatio() or 1.0
                except (AttributeError, RuntimeError):
                    pass
                size = int(22 * dpr)
                avail = (16, 22, 24, 32, 48)
                pick = min(avail, key=lambda s: abs(s - size))
                for cand in (f"mosque-{pick}.png", "mosque-22.png"):
                    icon_path = os.path.join(ASSETS_DIR, "tray", cand)
                    if os.path.isfile(icon_path):
                        tray_icon = QIcon(icon_path)
                        break
            except (AttributeError, RuntimeError, OSError) as exc:
                logger.debug("Tray PNG probe failed: %s", exc)
            if tray_icon.isNull():
                icon_path = os.path.join(ASSETS_DIR, "kaaba.png")
                tray_icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()
            self._tray = QSystemTrayIcon(tray_icon, self._app)
            self._tray.setToolTip(t("app_name"))
            menu = QMenu()
            menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self._tray_show_act = menu.addAction(tray_icon, t("tray_show"))
            self._tray_show_act.triggered.connect(self._show_window)
            menu.addSeparator()
            self._tray_info_act = QAction(t("tray_loading"), menu)
            self._tray_info_act.setEnabled(False)
            menu.addAction(self._tray_info_act)
            self._tray_pre_act = QAction("", menu)
            self._tray_pre_act.setEnabled(False)
            menu.addAction(self._tray_pre_act)
            menu.addSeparator()
            self._tray_quit_act = menu.addAction(t("tray_quit"))
            self._tray_quit_act.triggered.connect(self._quit)
            self._tray.setContextMenu(menu)
            self._tray.show()
            try:
                show = self._prayer_engine.getSetting("show_tray")
                if show is None:
                    show = True
                if not show:
                    self._tray.hide()
            except (AttributeError, RuntimeError, TypeError):
                pass
            self._prayer_engine._tray_notify = self._tray_show_message
            self._refresh_tray_context()
            self._tray.activated.connect(self._on_tray_activated)
            self._tray.messageClicked.connect(self._show_window)
            self._prayer_engine.trayInfoChanged.connect(self._on_tray_info_changed)
            self._tray_original_icon = tray_icon
        except (AttributeError, RuntimeError, OSError) as exc:
            logger.warning("Could not create tray: %s", exc)

    def _tray_usable(self) -> bool:
        tray = getattr(self, "_tray", None)
        if tray is None:
            return False
        try:
            return bool(tray.isVisible())
        except (AttributeError, RuntimeError):
            return False

    def _refresh_tray_context(self):
        try:
            self._engine.rootContext().setContextProperty("trayAvailable", self._tray_usable())
        except (AttributeError, RuntimeError):
            pass

    def _hide_tray(self):
        try:
            if getattr(self, "_tray", None) is not None:
                self._tray.hide()
        except (AttributeError, RuntimeError):
            pass

    def _tray_show_message(self, title: str, body: str):
        if not self._tray_usable():
            return
        try:
            from PySide6.QtWidgets import QSystemTrayIcon

            self._tray.showMessage(title, body, QSystemTrayIcon.Information, 10000)
        except (AttributeError, RuntimeError, TypeError):
            pass

    def _on_setting_changed(self, key):
        if key == "show_tray" and getattr(self, "_tray", None):
            try:
                show = self._prayer_engine.getSetting("show_tray")
                self._tray.setVisible(bool(show) if show is not None else True)
                self._refresh_tray_context()
            except (AttributeError, RuntimeError, TypeError):
                pass

    def _on_tray_info_changed(self, next_name, remaining, pre_text):
        try:
            if hasattr(self, "_tray_info_act") and self._tray_info_act:
                self._tray_info_act.setText(t("tray_next", name=next_name, remaining=remaining))
                self._tray.setToolTip(t("tray_tooltip", name=next_name, remaining=remaining))
            if hasattr(self, "_tray_pre_act") and self._tray_pre_act:
                self._tray_pre_act.setText(pre_text)
                self._tray_pre_act.setVisible(bool(pre_text))
        except (AttributeError, RuntimeError):
            pass

    def _on_language_changed(self):
        self._app.setApplicationName(t("app_name"))
        self._retranslate_tray()
        self._prayer_engine.clearCaches()
        root = self._engine.rootObjects()
        if root:
            try:
                root[0].retranslate()
            except (AttributeError, RuntimeError):
                pass

    def _retranslate_tray(self):
        if not hasattr(self, "_tray") or self._tray is None:
            return
        try:
            self._tray.setToolTip(t("app_name"))
            if hasattr(self, "_tray_show_act") and self._tray_show_act:
                self._tray_show_act.setText(t("tray_show"))
            if hasattr(self, "_tray_quit_act") and self._tray_quit_act:
                self._tray_quit_act.setText(t("tray_quit"))
            if hasattr(self, "_tray_info_act") and self._tray_info_act:
                prayer_engine = getattr(self, "_prayer_engine", None)
                if prayer_engine:
                    info = (
                        prayer_engine.getTrayInfo()
                        if hasattr(prayer_engine, "getTrayInfo")
                        else None
                    )
                    if info and info.get("next"):
                        name = info["next"]
                        remaining = info.get("remaining", "")
                        self._tray_info_act.setText(t("tray_next", name=name, remaining=remaining))
                        self._tray.setToolTip(t("tray_tooltip", name=name, remaining=remaining))
                    else:
                        self._tray_info_act.setText(t("tray_loading"))
                else:
                    self._tray_info_act.setText(t("tray_loading"))
        except (AttributeError, RuntimeError):
            pass

    def _on_azan_playing_changed(self, playing: bool):
        if not hasattr(self, "_tray") or self._tray is None:
            return
        if playing:
            self._tray_icon_visible = True
            self._azan_flash_timer.start()
        else:
            self._azan_flash_timer.stop()
            self._tray.setIcon(self._tray_original_icon)

    def _toggle_tray_icon(self):
        if not hasattr(self, "_tray") or self._tray is None:
            return
        self._tray_icon_visible = not self._tray_icon_visible
        self._tray.setIcon(self._tray_original_icon if self._tray_icon_visible else QIcon())

    def _show_window(self):
        try:
            root = self._engine.rootObjects()
            if root:
                try:
                    root[0].showNormal()
                except (AttributeError, RuntimeError):
                    pass
                root[0].show()
                root[0].raise_()
                root[0].requestActivate()
        except (AttributeError, RuntimeError):
            pass

    def _on_tray_activated(self, reason):
        from PySide6.QtWidgets import QSystemTrayIcon

        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.MiddleClick,
        ):
            self._show_window()

    def _quit(self):
        self._azan_flash_timer.stop()
        self._prayer_engine.stopAzan()
        # Disconnect signals to prevent stale callbacks during teardown
        for obj, signal in (
            (self._prayer_engine, "themeChanged"),
            (self._theme_controller, "themeChanged"),
            (self._l10n, "languageChanged"),
            (self._prayer_engine, "languageChanged"),
            (self._prayer_engine, "azanPlayingChanged"),
            (self._prayer_engine, "trayInfoChanged"),
        ):
            try:
                getattr(obj, signal).disconnect()
            except (RuntimeError, TypeError):
                pass
        self._prayer_engine.cleanup()
        self._theme_controller.cleanup()
        root = self._engine.rootObjects()
        if root:
            root[0].close()
        self._app.quit()

    def _on_prayer_theme_changed(self, theme_id: str):
        """Update ThemeController when user changes theme in settings UI."""
        try:
            self._theme_controller.setTheme(theme_id)
        except (ValueError, RuntimeError, AttributeError) as exc:
            logger.warning("Theme change sync failed: %s", exc)

    def run(self):
        return self._app.exec()


AZAN_DEFAULT = os.path.join(ASSETS_DIR, "muezzins", "قطامي.mp3")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="أذان الأوقات الخمس – Athan Five Times App")
    parser.add_argument("--azan", default=AZAN_DEFAULT, help="Path to Azan MP3 file")
    parser.add_argument("--profile-memory", action="store_true", help="Enable memory profiling")
    parser.add_argument(
        "--profile-interval", type=float, default=5.0, help="Memory profiling interval (seconds)"
    )
    args = parser.parse_args()

    if args.profile_memory and _MEMORY_PROFILER_AVAILABLE:
        start_profiling(args.profile_interval)
        logger.info("Memory profiling enabled (interval: %.1fs)", args.profile_interval)

    if not os.path.isfile(args.azan):
        logger.warning("Azan file not found at '%s'. Audio disabled.", args.azan)
        args.azan = ""

    app = QmlAthanApp(sys.argv, args.azan)
    exit_code = app.run()

    if args.profile_memory and _MEMORY_PROFILER_AVAILABLE:
        stop_profiling()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
