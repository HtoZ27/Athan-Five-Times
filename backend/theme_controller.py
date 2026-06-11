"""
Theme Controller - Simple, reliable theme management.
Single source of truth: settings via settings.py (shared with PrayerEngine).
"""

import logging
import os
from PySide6.QtCore import QObject, Signal, Property, Slot, Qt
from PySide6.QtGui import QGuiApplication

from .settings import load as load_settings, save as save_settings

logger = logging.getLogger(__name__)

THEMES = ["auto", "light", "dark", "ottoman_gold", "catppuccin_mocha", "catppuccin_latte"]

# Path to the shared JSON settings file
SETTINGS_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")),
    "athan-five-times",
)
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")


class ThemeController(QObject):
    """Theme controller with JSON settings persistence (shared with PrayerEngine)."""
    
    themeChanged = Signal(str)  # emits user theme
    resolvedThemeChanged = Signal(str)  # emits resolved theme for UI binding
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_theme = self._load_user_theme()
        self._resolved_cache = self._compute_resolved()
        self._last_resolved_emit = self._resolved_cache
        self._connect_system_theme()
    
    def _load_user_theme(self) -> str:
        """Load user's theme choice from shared settings via cache."""
        try:
            data = load_settings()
            theme = data.get("theme", "auto")
            if theme in THEMES:
                return theme
        except Exception as e:
            logger.warning(f"Failed to load theme: {e}")
        return "auto"

    def _save_user_theme(self, theme: str):
        """Save user's theme choice to shared settings via cache."""
        try:
            data = load_settings()
            data["theme"] = theme
            save_settings(data)
        except Exception as e:
            logger.error(f"Failed to save theme: {e}")
    
    def _detect_system_theme(self) -> str:
        """Detect system theme (light/dark) - Qt5/Qt6 compatible."""
        try:
            hints = QGuiApplication.styleHints()
            # Qt6: colorScheme() returns Qt.ColorScheme enum
            if hasattr(Qt, 'ColorScheme'):
                scheme = hints.colorScheme()
                if scheme == Qt.ColorScheme.Dark:
                    return "dark"
                return "light"
            # Qt5 fallback: isDarkTheme()
            if hasattr(hints, 'isDarkTheme'):
                return "dark" if hints.isDarkTheme() else "light"
        except (AttributeError, RuntimeError):
            pass
        return "light"
    
    def _compute_resolved(self) -> str:
        """Compute resolved theme (never 'auto')."""
        if self._user_theme == "auto":
            return self._detect_system_theme()
        return self._user_theme
    
    def _connect_system_theme(self):
        try:
            hints = QGuiApplication.styleHints()
            hints.colorSchemeChanged.connect(self._on_system_theme_changed)
        except Exception:
            pass

    def _on_system_theme_changed(self):
        if self._user_theme == "auto":
            self._update_resolved_cache()

    def _update_resolved_cache(self):
        """Update resolved cache and emit signal if changed (Anti-Spam Gate)."""
        new_resolved = self._compute_resolved()
        if new_resolved != self._resolved_cache:
            self._resolved_cache = new_resolved
        # Anti-Spam Gate: فقط إذا تغيرت القيمة النهائية
        if new_resolved != self._last_resolved_emit:
            self._last_resolved_emit = new_resolved
            self.resolvedThemeChanged.emit(new_resolved)
    
    @Property(str, notify=themeChanged)
    def theme(self) -> str:
        """User's theme choice (auto/light/dark/ottoman_gold)."""
        return self._user_theme
    
    @Property(str, notify=resolvedThemeChanged)
    def resolvedTheme(self) -> str:
        """Resolved theme for UI rendering (never 'auto')."""
        return self._resolved_cache
    
    @Slot(str)
    def setTheme(self, theme_id: str):
        """Set user's theme choice."""
        if theme_id not in THEMES:
            logger.warning(f"Invalid theme: {theme_id}")
            return
        if theme_id == self._user_theme:
            return
        self._user_theme = theme_id
        self._save_user_theme(theme_id)
        self._update_resolved_cache()
        self.themeChanged.emit(self._user_theme)
        logger.info(f"Theme changed to: {theme_id} (resolved: {self._resolved_cache})")
    
    @Slot()
    def toggleTheme(self):
        """Toggle between light and dark."""
        current = self.resolvedTheme
        if current in ("dark", "ottoman_gold"):
            self.setTheme("light")
        else:
            self.setTheme("dark")
    
    @Slot(bool)
    def setAutoTheme(self, auto: bool):
        if auto:
            self.setTheme("auto")

    def cleanup(self):
        try:
            hints = QGuiApplication.styleHints()
            hints.colorSchemeChanged.disconnect(self._on_system_theme_changed)
        except Exception:
            pass

    def __del__(self):
        self.cleanup()