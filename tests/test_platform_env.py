"""Tests for display-server (Wayland / X11) detection and QPA normalization.

Covers ``backend.platform_env``: session detection, the multi-entry
``QT_QPA_PLATFORM`` normalization that removes unreachable candidates, and
the runtime classification used by the widget to adapt its behaviour.
"""

import os
import shutil
import socket
import tempfile
from pathlib import Path

import pytest

from backend import platform_env as pe

_ENV_KEYS = (
    "QT_QPA_PLATFORM",
    "XDG_SESSION_TYPE",
    "WAYLAND_DISPLAY",
    "DISPLAY",
    "XDG_RUNTIME_DIR",
)


@pytest.fixture
def clean_env(monkeypatch):
    """Isolated environment + short runtime dir (unix sockets are path-bound)."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    tmp = Path(tempfile.mkdtemp(prefix="pe-rt-"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def _make_wayland_socket(tmp_path: Path, name: str = "wayland-0") -> socket.socket:
    """Create a real unix socket so ``is_socket()`` checks pass."""
    path = tmp_path / name
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(path))
    return sock


class TestAvailability:
    def test_wayland_available_with_socket(self, clean_env, monkeypatch):
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        sock = _make_wayland_socket(clean_env)
        try:
            assert pe.wayland_available() is True
        finally:
            sock.close()

    def test_wayland_unavailable_without_socket(self, clean_env, monkeypatch):
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-9")
        assert pe.wayland_available() is False

    def test_wayland_absolute_path(self, clean_env, monkeypatch):
        sock = _make_wayland_socket(clean_env, "custom-sock")
        monkeypatch.setenv("WAYLAND_DISPLAY", str(clean_env / "custom-sock"))
        try:
            assert pe.wayland_available() is True
        finally:
            sock.close()

    def test_wayland_absent_env(self, clean_env):
        assert pe.wayland_available() is False

    def test_x11_available_from_display(self, clean_env, monkeypatch):
        assert pe.x11_available() is False
        monkeypatch.setenv("DISPLAY", ":0")
        assert pe.x11_available() is True

    def test_x11_ignores_blank_display(self, clean_env, monkeypatch):
        monkeypatch.setenv("DISPLAY", "   ")
        assert pe.x11_available() is False


class TestSessionType:
    def test_declared_wayland(self, clean_env, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
        assert pe.session_type() == "wayland"

    def test_declared_x11_case_insensitive(self, clean_env, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_TYPE", "X11")
        assert pe.session_type() == "x11"

    def test_tty_session(self, clean_env, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_TYPE", "tty")
        assert pe.session_type() == "tty"

    def test_inferred_wayland_from_socket(self, clean_env, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_TYPE", "unspecified")
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        sock = _make_wayland_socket(clean_env)
        try:
            assert pe.session_type() == "wayland"
        finally:
            sock.close()

    def test_inferred_x11_from_display(self, clean_env, monkeypatch):
        monkeypatch.setenv("DISPLAY", ":0")
        assert pe.session_type() == "x11"

    def test_unknown_without_hints(self, clean_env):
        assert pe.session_type() == "unknown"


class TestPlatformClassify:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("wayland", True),
            ("wayland-egl", True),
            ("Wayland", True),
            ("xcb", False),
            ("offscreen", False),
            ("minimal", False),
            ("", False),
        ],
    )
    def test_platform_is_wayland(self, name, expected):
        assert pe.platform_is_wayland(name) is expected


class TestQpaNormalization:
    def test_unset_is_left_to_qt(self, clean_env):
        assert pe.prepare_qpa_platform() == ""
        assert "QT_QPA_PLATFORM" not in os.environ

    def test_single_explicit_is_respected(self, clean_env, monkeypatch):
        monkeypatch.setenv("QT_QPA_PLATFORM", "wayland")
        assert pe.prepare_qpa_platform() == "wayland"

    def test_wayland_dropped_on_x11_session(self, clean_env, monkeypatch):
        """The distro preset "wayland;xcb" on X11 keeps only xcb."""
        monkeypatch.setenv("QT_QPA_PLATFORM", "wayland;xcb")
        monkeypatch.setenv("DISPLAY", ":0")
        assert pe.prepare_qpa_platform() == "xcb"
        assert os.environ["QT_QPA_PLATFORM"] == "xcb"

    def test_wayland_kept_on_wayland_session(self, clean_env, monkeypatch):
        monkeypatch.setenv("QT_QPA_PLATFORM", "wayland;xcb")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        sock = _make_wayland_socket(clean_env)
        try:
            assert pe.prepare_qpa_platform() == "wayland;xcb"
        finally:
            sock.close()

    def test_xcb_dropped_without_display(self, clean_env, monkeypatch):
        monkeypatch.setenv("QT_QPA_PLATFORM", "wayland;xcb")
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        sock = _make_wayland_socket(clean_env)
        try:
            assert pe.prepare_qpa_platform() == "wayland"
        finally:
            sock.close()

    def test_all_unreachable_keeps_original(self, clean_env, monkeypatch):
        monkeypatch.setenv("QT_QPA_PLATFORM", "wayland;xcb")
        assert pe.prepare_qpa_platform() == "wayland;xcb"

    def test_other_platforms_pass_through(self, clean_env, monkeypatch):
        monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen;xcb")
        monkeypatch.setenv("DISPLAY", ":0")
        assert pe.prepare_qpa_platform() == "offscreen;xcb"

    def test_whitespace_and_case_tolerated(self, clean_env, monkeypatch):
        monkeypatch.setenv("QT_QPA_PLATFORM", "Wayland ; xcb")
        monkeypatch.setenv("DISPLAY", ":0")
        assert pe.prepare_qpa_platform() == "xcb"


class TestPrepareDisplayEnv:
    def test_returns_report(self, clean_env, monkeypatch):
        monkeypatch.setenv("QT_QPA_PLATFORM", "wayland;xcb")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
        info = pe.prepare_display_env()
        assert info["session"] == "x11"
        assert info["qpa_setting"] == "xcb"
        assert info["wayland_socket"] is False
        assert info["x11_display"] is True


class TestEnginePlatformSlots:
    """The QML-facing slots stay consistent with the detected QPA."""

    def test_slots_are_consistent(self):
        from backend.backend_controller import PrayerEngine

        e = PrayerEngine()
        try:
            plat = e.getRenderedPlatform()
            info = e.getPlatformInfo()
            assert set(("session", "platform", "wayland")) <= set(info)
            assert info["wayland"] is pe.platform_is_wayland(info["platform"])
            assert e.isWaylandRuntime() is pe.platform_is_wayland(plat)
            # With no QApplication (plain pytest) the slot reports "" instead
            # of Qt's compiled-in default.
            if plat == "":
                assert info["platform"] == "unknown"
                assert e.isWaylandRuntime() is False
        finally:
            e.cleanup()
