"""Tray backend selection and wrapper behaviour (offscreen).

The protocol-level end-to-end checks live in ``scripts/e2e-tray-envs.sh``
(isolated dbus-run-session / Xephyr scenarios). These tests cover the parts
that can run without any host: detection precedence, the transparent flash
icon, menu lifetime and signal mapping.
"""

import gc
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon  # noqa: E402

from backend import tray_backend as tb  # noqa: E402

_app = QApplication.instance() or QApplication([])


class TestDetection:
    def test_qt_wins_when_both_hosts_exist(self, monkeypatch):
        monkeypatch.setattr(tb, "qt_tray_available", lambda: True)
        monkeypatch.setattr(tb, "xapp_monitor_available", lambda: True)
        monkeypatch.setattr(tb, "xapp_runtime_available", lambda: True)
        assert tb.detect_tray_kind() == tb.KIND_QT

    def test_xapp_used_when_qt_has_no_host(self, monkeypatch):
        monkeypatch.setattr(tb, "qt_tray_available", lambda: False)
        monkeypatch.setattr(tb, "xapp_monitor_available", lambda: True)
        monkeypatch.setattr(tb, "xapp_runtime_available", lambda: True)
        assert tb.detect_tray_kind() == tb.KIND_XAPP

    def test_xapp_needs_runtime_stack(self, monkeypatch):
        monkeypatch.setattr(tb, "qt_tray_available", lambda: False)
        monkeypatch.setattr(tb, "xapp_monitor_available", lambda: True)
        monkeypatch.setattr(tb, "xapp_runtime_available", lambda: False)
        assert tb.detect_tray_kind() is None

    def test_no_host_returns_none(self, monkeypatch):
        monkeypatch.setattr(tb, "qt_tray_available", lambda: False)
        monkeypatch.setattr(tb, "xapp_monitor_available", lambda: False)
        assert tb.detect_tray_kind() is None


class TestQtAvailability:
    """qt_tray_available() must not trust Qt blindly on non-X11 platforms."""

    def test_xcb_trusts_qt_without_watcher(self, monkeypatch):
        monkeypatch.setattr(tb, "_qt_reports_tray", lambda: True)
        monkeypatch.setattr(tb, "_platform_name", lambda: "xcb")
        monkeypatch.setattr(tb, "sni_watcher_available", lambda: False)
        assert tb.qt_tray_available() is True

    def test_wayland_requires_watcher(self, monkeypatch):
        monkeypatch.setattr(tb, "_qt_reports_tray", lambda: True)
        monkeypatch.setattr(tb, "_platform_name", lambda: "wayland")
        monkeypatch.setattr(tb, "sni_watcher_available", lambda: False)
        assert tb.qt_tray_available() is False

    def test_wayland_with_watcher_is_available(self, monkeypatch):
        monkeypatch.setattr(tb, "_qt_reports_tray", lambda: True)
        monkeypatch.setattr(tb, "_platform_name", lambda: "wayland")
        monkeypatch.setattr(tb, "sni_watcher_available", lambda: True)
        assert tb.qt_tray_available() is True

    def test_qt_reporting_no_tray_wins(self, monkeypatch):
        monkeypatch.setattr(tb, "_qt_reports_tray", lambda: False)
        monkeypatch.setattr(tb, "_platform_name", lambda: "xcb")
        monkeypatch.setattr(tb, "sni_watcher_available", lambda: True)
        assert tb.qt_tray_available() is False


class TestTransparentIcon:
    def test_png_is_fully_transparent(self):
        path = tb.make_transparent_png(22)
        assert path and os.path.isfile(path)
        icon = QIcon(path)
        assert not icon.isNull()
        image = icon.pixmap(22, 22).toImage()
        for point in ((0, 0), (11, 11), (21, 21)):
            assert image.pixelColor(*point).alpha() == 0

    def test_same_path_reused(self):
        assert tb.make_transparent_png(22) == tb.make_transparent_png(22)


class TestQtBackend:
    def test_menu_survives_garbage_collection(self):
        menu = QMenu()
        menu.addAction("entry")
        backend = tb.QtTrayBackend("", "tip", menu=menu)
        try:
            del menu
            gc.collect()
            assert backend._menu is not None
            assert len(backend._menu.actions()) == 1
        finally:
            backend.destroy()

    def test_wayland_without_watcher_is_not_hosted(self, monkeypatch):
        monkeypatch.setattr(tb, "_qt_reports_tray", lambda: True)
        monkeypatch.setattr(tb, "_platform_name", lambda: "wayland")
        monkeypatch.setattr(tb, "sni_watcher_available", lambda: False)
        backend = tb.QtTrayBackend("", "tip")
        try:
            assert backend.is_hosted() is False
        finally:
            backend.destroy()

    def test_not_hosted_offscreen(self, monkeypatch):
        monkeypatch.setattr(tb, "sni_watcher_available", lambda: False)
        backend = tb.QtTrayBackend("", "tip")
        try:
            assert backend.is_hosted() is False
            assert backend.show_message("t", "b") is False
        finally:
            backend.destroy()

    def test_setters_are_safe_without_host(self):
        backend = tb.QtTrayBackend("", "tip")
        try:
            backend.set_visible(False)
            backend.set_tooltip("next")
            backend.set_icon("")
            assert backend._tooltip == "next"
        finally:
            backend.destroy()

    @pytest.mark.parametrize(
        "reason,expected",
        [
            (QSystemTrayIcon.ActivationReason.Trigger, True),
            (QSystemTrayIcon.ActivationReason.DoubleClick, True),
            (QSystemTrayIcon.ActivationReason.MiddleClick, True),
            (QSystemTrayIcon.ActivationReason.Context, False),
            (QSystemTrayIcon.ActivationReason.Unknown, False),
        ],
    )
    def test_activation_mapping(self, reason, expected):
        backend = tb.QtTrayBackend("", "tip")
        calls = []
        backend.activateRequested.connect(lambda: calls.append(1))
        try:
            backend._on_activated(reason)
            assert bool(calls) is expected
        finally:
            backend.destroy()


class TestCreateFactory:
    def test_unknown_kind_rejected(self):
        with pytest.raises(ValueError):
            tb.create_tray_backend("bogus", "")

    def test_qt_kind_returns_qt_backend(self):
        backend = tb.create_tray_backend(tb.KIND_QT, "", "tip")
        try:
            assert isinstance(backend, tb.QtTrayBackend)
        finally:
            backend.destroy()
