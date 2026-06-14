"""
Main entry point for QML-based Athan Five Times Prayer Application.
"""

import sys
import os
import logging
import gc

# Memory optimizations
os.environ["GTK_MODULES"] = ""
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
os.environ.setdefault("QT_QPA_PLATFORMTHEME", "qt5ct")
os.environ["QT_ACCESSIBILITY"] = "0"
os.environ["QT_QUICK_CONTROLS_STYLE"] = "Fusion"

from PySide6.QtCore import QUrl, QTimer, Qt
from PySide6.QtGui import QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtQuickControls2 import QQuickStyle

from .settings import load as load_settings, save as save_settings, APP_VERSION
from .location import detect_async
from .i18n import t, set_lang
from .backend_controller import PrayerEngine
from .theme_controller import ThemeController
from .audio import set_volume

# Memory profiler اختياري (لتشغيله: python -m backend.memory_profiler)
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
            for fname in sorted(os.listdir(fonts_dir)):
                if fname.lower().endswith(".ttf"):
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
        # Initialize tray-related attributes early to avoid AttributeError
        self._tray = None
        self._tray_original_icon = QIcon()
        self._azan_flash_timer = QTimer()
        self._azan_flash_timer.setInterval(500)
        self._azan_flash_timer.timeout.connect(self._toggle_tray_icon)
        self._tray_icon_visible = True
        self._engine = QQmlApplicationEngine()
        self._engine.addImportPath(QML_DIR)

        # Register Theme singleton from QML file
        qmlRegisterSingletonType(QUrl.fromLocalFile(os.path.join(QML_DIR, "Theme.qml")), "Theme", 1, 0, "Theme")

        self._theme_controller = ThemeController()
        self._prayer_engine = PrayerEngine()

        ctx = self._engine.rootContext()
        ctx.setContextProperty("prayerEngine", self._prayer_engine)
        ctx.setContextProperty("backendController", self._prayer_engine)
        ctx.setContextProperty("themeController", self._theme_controller)
        ctx.setContextProperty("appVersion", APP_VERSION)

        # Connect theme changes both ways
        self._prayer_engine.themeChanged.connect(self._on_prayer_theme_changed)
        self._theme_controller.themeChanged.connect(self._prayer_engine.saveTheme)

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
        self._prayer_engine.languageChanged.connect(self._on_language_changed)

        # Connect azanPlayingChanged signal immediately for tray flash
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
            country_code = loc.get("country_code", "")

            result = dict(settings)
            result["country"] = loc.get("country_code", "TN") or "TN"
            result["latitude"] = lat
            result["longitude"] = lon

            from .prayer_calc import COUNTRY_CITIES, COUNTRY_METHODS
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
            logger.info("Auto-located: %s/%s (%.4f, %.4f) %s", country_code, result["city"], lat, lon, tz)
            result["first_run"] = False
            save_settings(result)

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
        self._prayer_engine.preloadAudio()
        root = self._engine.rootObjects()
        if root:
            try:
                root[0].closing.connect(self._save_window_geometry)
            except (AttributeError, RuntimeError):
                pass
        # Note: trayInfoChanged is connected in _setup_tray (not here) to avoid duplicate

    def _setup_tray(self):
        try:
            from PySide6.QtWidgets import QSystemTrayIcon, QMenu
            from PySide6.QtGui import QAction
            if not QSystemTrayIcon.isSystemTrayAvailable():
                logger.info("System tray not available")
                return
            # Use SVG icon for proper transparency (avoids black background on some trays)
            icon_path = os.path.join(ASSETS_DIR, "kaaba.svg")
            tray_icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()
            if tray_icon.isNull():
                icon_path = os.path.join(ASSETS_DIR, "kaaba.png")
                tray_icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()
            self._tray = QSystemTrayIcon(tray_icon, self._app)
            self._tray.setToolTip(t("app_name"))
            menu = QMenu()
            menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            show_act = menu.addAction(t("tray_show"))
            show_act.triggered.connect(self._show_window)
            menu.addSeparator()
            self._tray_info_act = QAction(t("tray_loading"), menu)
            self._tray_info_act.setEnabled(False)
            menu.addAction(self._tray_info_act)
            self._tray_pre_act = QAction("", menu)
            self._tray_pre_act.setEnabled(False)
            menu.addAction(self._tray_pre_act)
            menu.addSeparator()
            quit_act = menu.addAction(t("tray_quit"))
            quit_act.triggered.connect(self._quit)
            self._tray.setContextMenu(menu)
            self._tray.show()
            self._tray.activated.connect(self._on_tray_activated)
            self._tray.messageClicked.connect(self._show_window)
            self._prayer_engine.trayInfoChanged.connect(self._on_tray_info_changed)
            # Note: azanPlayingChanged is connected in __init__ for immediate tray flash support
            self._tray_original_icon = tray_icon
        except (AttributeError, RuntimeError, OSError) as exc:
            logger.warning("Could not create tray: %s", exc)

    def _on_tray_info_changed(self, next_name, remaining, pre_text):
        try:
            if hasattr(self, '_tray_info_act') and self._tray_info_act:
                self._tray_info_act.setText(t("tray_next", name=next_name, remaining=remaining))
                self._tray.setToolTip(t("tray_tooltip", name=next_name, remaining=remaining))
            if hasattr(self, '_tray_pre_act') and self._tray_pre_act:
                self._tray_pre_act.setText(pre_text)
                self._tray_pre_act.setVisible(bool(pre_text))
        except (AttributeError, RuntimeError):
            pass

    def _on_language_changed(self):
        self._app.setApplicationName(t("app_name"))
        root = self._engine.rootObjects()
        if root:
            try:
                root[0].retranslate()
            except (AttributeError, RuntimeError):
                pass

    def _on_azan_playing_changed(self, playing: bool):
        # Tray might not be initialized yet, guard against that
        if not hasattr(self, '_tray') or self._tray is None:
            return
        if playing:
            self._tray_icon_visible = True
            self._azan_flash_timer.start()
        else:
            self._azan_flash_timer.stop()
            self._tray.setIcon(self._tray_original_icon)

    def _toggle_tray_icon(self):
        if not hasattr(self, '_tray') or self._tray is None:
            return
        self._tray_icon_visible = not self._tray_icon_visible
        self._tray.setIcon(self._tray_original_icon if self._tray_icon_visible else QIcon())

    def _show_window(self):
        root = self._engine.rootObjects()
        if root:
            root[0].show()
            root[0].raise_()
            root[0].requestActivate()

    def _on_tray_activated(self, reason):
        from PySide6.QtWidgets import QSystemTrayIcon
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick,
                      QSystemTrayIcon.ActivationReason.MiddleClick):
            self._show_window()

    def _quit(self):
        self._azan_flash_timer.stop()
        self._prayer_engine.stopAzan()
        # Disconnect signals to prevent stale callbacks during teardown
        try: self._prayer_engine.themeChanged.disconnect()
        except (RuntimeError, TypeError): pass
        try: self._theme_controller.themeChanged.disconnect()
        except (RuntimeError, TypeError): pass
        try: self._prayer_engine.languageChanged.disconnect()
        except (RuntimeError, TypeError): pass
        try: self._prayer_engine.azanPlayingChanged.disconnect()
        except (RuntimeError, TypeError): pass
        try: self._prayer_engine.trayInfoChanged.disconnect()
        except (RuntimeError, TypeError): pass
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
    parser.add_argument("--profile-interval", type=float, default=5.0, help="Memory profiling interval (seconds)")
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
