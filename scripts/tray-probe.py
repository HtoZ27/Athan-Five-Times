#!/usr/bin/env python3
"""Report how the system tray behaves in the current desktop session.

Run this inside GNOME X11, GNOME Wayland, or MATE X11 as the logged-in
user. Static mode only inspects the session bus and Qt; ``--live N`` also
shows the real tray icon for N seconds and logs activations/menu actions.

    python3 scripts/tray-probe.py
    python3 scripts/tray-probe.py --live 20

Nothing is written outside the temporary blank-icon file used by the app.
"""
import argparse
import ctypes
import ctypes.util
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def stamp() -> str:
    return time.strftime("%H:%M:%S")


def log(message: str) -> None:
    print(f"[{stamp()}] {message}", flush=True)


def pick_icon() -> str:
    assets = ROOT / "assets"
    try:
        from PySide6.QtGui import QGuiApplication

        screens = QGuiApplication.screens()
        dpr = (screens[0].devicePixelRatio() if screens else 1.0) or 1.0
    except (ImportError, AttributeError, RuntimeError):
        dpr = 1.0
    size = int(22 * dpr)
    pick = min((16, 22, 24, 32, 48), key=lambda candidate: abs(candidate - size))
    for name in (f"mosque-{pick}.png", "mosque-22.png"):
        candidate = assets / "tray" / name
        if candidate.is_file():
            return str(candidate)
    fallback = assets / "kaaba.png"
    return str(fallback) if fallback.is_file() else ""


def x11_tray_owner():
    if not os.environ.get("DISPLAY"):
        return None
    try:
        x11 = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11") or "libX11.so.6")
        display = ctypes.c_void_p
        x11.XOpenDisplay.restype = display
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XInternAtom.restype = ctypes.c_ulong
        x11.XInternAtom.argtypes = [display, ctypes.c_char_p, ctypes.c_int]
        x11.XGetSelectionOwner.restype = ctypes.c_ulong
        x11.XGetSelectionOwner.argtypes = [display, ctypes.c_ulong]
        x11.XCloseDisplay.argtypes = [display]
        dpy = x11.XOpenDisplay(None)
        if not dpy:
            return None
        atom = x11.XInternAtom(dpy, b"_NET_SYSTEM_TRAY_S0", 0)
        owner = int(x11.XGetSelectionOwner(dpy, atom))
        x11.XCloseDisplay(dpy)
        return owner
    except (OSError, AttributeError, TypeError):
        return None


def watcher_owner(name: str) -> str:
    try:
        from PySide6.QtDBus import QDBusConnection

        interface = QDBusConnection.sessionBus().interface()
        if interface is None:
            return ""
        reply = interface.serviceOwner(name)
        return str(reply.value()) if reply.isValid() else ""
    except (ImportError, AttributeError, RuntimeError):
        return ""


def print_report(tb, platform: str) -> list[str]:
    names = tb._session_bus_names()
    interesting = sorted(
        name
        for name in names
        if any(
            token in name.lower()
            for token in ("statusnotifier", "statusicon", "indicator", "gnome.shell",
                          "mate", "cinnamon", "xapp", "panel")
        )
    )
    print("== Athan tray probe ==")
    for key in (
        "XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP", "XDG_SESSION_TYPE",
        "DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM",
    ):
        print(f"{key}={os.environ.get(key, '')}")
    print(f"qt-platform={platform or '(none)'}")
    print(f"bus-watcher-owner={watcher_owner(tb.SNI_WATCHER_NAME) or '(none)'}")
    print(f"bus-interesting={interesting}")
    print(
        "checks="
        f"qt_reports={tb._qt_reports_tray()} "
        f"sni_watcher={tb.sni_watcher_available()} "
        f"qt_available={tb.qt_tray_available()} "
        f"xapp_monitor={tb.xapp_monitor_available()} "
        f"xapp_runtime={tb.xapp_runtime_available()}"
    )
    owner = x11_tray_owner()
    print(f"xembed-owner={hex(owner) if owner else '(none)'}")
    kind = tb.detect_tray_kind()
    print(f"detect={kind or 'none'}")
    return names


def run_live(tb, kind: str, duration: int) -> None:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMenu

    app = QApplication.instance() or QApplication([])
    menu = QMenu()
    show_action = menu.addAction("Athan — إظهار النافذة")
    info_action = menu.addAction("معلومات الصلاة")
    info_action.setEnabled(False)
    menu.addSeparator()
    quit_action = menu.addAction("خروج")
    backend = tb.create_tray_backend(
        kind, pick_icon(), "Athan Five Times — tray probe", menu=menu
    )
    backend.activateRequested.connect(lambda: log("EVENT activate"))
    backend.menuRequested.connect(lambda: log("EVENT menu-requested"))
    show_action.triggered.connect(lambda: log("EVENT action show-window"))
    quit_action.triggered.connect(lambda: log("EVENT action quit"))
    print(
        f"live: backend={kind} — انقر يسارًا للتفعيل ويمينًا للقائمة "
        f"(يعمل {duration} ثانية)",
        flush=True,
    )

    def report() -> None:
        log(f"live-hosted={backend.is_hosted()}")

    QTimer.singleShot(1500, report)
    QTimer.singleShot(duration * 1000, app.quit)
    app.exec()
    log(f"live-done hosted={backend.is_hosted()}")
    backend.destroy()
    menu.deleteLater()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", type=int, default=0, metavar="SECONDS")
    args = parser.parse_args()

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 is not available", file=sys.stderr)
        return 2
    app = QApplication.instance() or QApplication([sys.argv[0]])

    try:
        from backend import tray_backend as tb
    except Exception as exc:
        print(f"cannot import backend.tray_backend: {exc}", file=sys.stderr)
        return 2

    from PySide6.QtGui import QGuiApplication

    print_report(tb, QGuiApplication.platformName())
    if args.live > 0:
        kind = tb.detect_tray_kind()
        if kind is None:
            print("live: skipped — لا يوجد host (هذا متوقع على GNOME بلا AppIndicator)")
        else:
            run_live(tb, kind, args.live)
    if QApplication.instance() is app:
        app.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
