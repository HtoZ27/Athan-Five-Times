"""Tray icon assets, menu strings and show_tray setting."""

import glob
import json
import os

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_app = QApplication.instance() or QApplication([])

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets", "tray")
TRANS = os.path.join(os.path.dirname(__file__), "..", "backend", "translations")


class TestTrayAssets:
    @pytest.mark.parametrize("size", [16, 22, 24, 32, 48])
    def test_mosque_png_loads(self, size):
        path = os.path.join(ASSETS, f"mosque-{size}.png")
        assert os.path.isfile(path), path
        icon = QIcon(path)
        assert not icon.isNull()
        sizes = icon.availableSizes()
        assert sizes and sizes[0].width() == size

    def test_app_icon_untouched(self):
        base = os.path.join(os.path.dirname(ASSETS))
        assert os.path.isfile(os.path.join(base, "kaaba.svg"))
        assert os.path.isfile(os.path.join(base, "kaaba.png"))


class TestTrayStrings:
    KEYS = ["tray_show", "tray_quit", "notif_prayer_title", "notif_dnd_title"]

    def test_no_emoji_in_tray_strings(self):
        bad = []
        for f in sorted(glob.glob(os.path.join(TRANS, "*.json"))):
            ui = json.load(open(f, encoding="utf-8")).get("ui", {})
            for k in self.KEYS:
                v = ui.get(k, "")
                if "🕋" in v or "❌" in v:
                    bad.append((os.path.basename(f), k))
        assert bad == [], bad

    def test_tray_text_kept(self):
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from backend.translations import load, u

        load("ar")
        assert u("tray_show") == "إظهار النافذة"
        assert u("tray_quit") == "خروج"


class TestShowTraySetting:
    def test_default_true(self):
        from backend.settings import DEFAULT_SETTINGS

        assert DEFAULT_SETTINGS.get("show_tray") is True

    def test_toggle_persists(self):
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from backend.backend_controller import PrayerEngine

        e = PrayerEngine()
        try:
            e.updateSetting("show_tray", False)
            assert e.getSetting("show_tray") is False
            e.updateSetting("show_tray", True)
            assert e.getSetting("show_tray") is True
        finally:
            e.cleanup()


class TestHideToTrayPolicy:
    def test_matrix(self):
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from backend.main import should_hide_to_tray

        assert should_hide_to_tray(True, True) is True
        assert should_hide_to_tray(True, False) is False
        assert should_hide_to_tray(False, True) is False
        assert should_hide_to_tray(False, False) is False


class TestNotifyFallback:
    def test_tray_bubble_used_when_notify_send_missing(self, monkeypatch):
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import subprocess
        from backend.backend_controller import PrayerEngine

        e = PrayerEngine()
        try:
            calls = []
            e._tray_notify = lambda title, body: calls.append((title, body))

            def boom(*a, **k):
                raise FileNotFoundError("no notify-send")

            monkeypatch.setattr(subprocess, "Popen", boom)
            e._notify_os("TestPrayer")
            assert len(calls) == 1
            assert calls[0][1]
        finally:
            e.cleanup()

    def test_notify_silent_without_any_backend(self, monkeypatch):
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        import subprocess
        from backend.backend_controller import PrayerEngine

        e = PrayerEngine()
        try:
            e._tray_notify = None

            def boom(*a, **k):
                raise FileNotFoundError("no notify-send")

            monkeypatch.setattr(subprocess, "Popen", boom)
            e._notify_os("TestPrayer")  # must not raise
        finally:
            e.cleanup()
