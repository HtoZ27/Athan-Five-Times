"""Cross-desktop Linux tray backends.

Qt 6 talks to a Linux system tray through one of two protocols:

* **StatusNotifierItem/XEmbed** via ``QSystemTrayIcon`` — used by KDE,
  GNOME (AppIndicator extension), Cinnamon/MATE (through ``xapp-sn-watcher``),
  and classic XEmbed trays (plain XFCE, Openbox, i3, …).
* **XApp StatusIcon** (``org.x.StatusIcon``) — used by Linux Mint's
  ``xapp-status-plugin`` when the SNI bridge is disabled. This is the only
  protocol the Mint XFCE panel hosts, and Qt does not implement it.

``detect_tray_kind()`` picks the first protocol with a live host; the
matching backend exposes a uniform API to `backend.main`. Backends never
raise from ``is_hosted()`` — callers use that to decide whether the window
may be hidden instead of quitting.
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon

logger = logging.getLogger(__name__)

KIND_QT = "qt"
KIND_XAPP = "xapp"

XAPP_BUS_PREFIX = "org.x.StatusIcon."
XAPP_MONITOR_PREFIX = "org.x.StatusIconMonitor"
XAPP_ICON_PATH = "/org/x/StatusIcon/Icon"
XAPP_MANAGER_PATH = "/org/x/StatusIcon"

SNI_WATCHER_NAME = "org.kde.StatusNotifierWatcher"


def _session_bus_names() -> list[str]:
    """Registered well-known names on the session bus ([] when unavailable)."""
    try:
        from PySide6.QtDBus import QDBusConnection

        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            return []
        iface = bus.interface()
        if iface is None:
            return []
        reply = iface.registeredServiceNames()
        if not reply.isValid():
            return []
        return [str(n) for n in reply.value()]
    except (ImportError, AttributeError, RuntimeError):
        return []


def _platform_name() -> str:
    """QPA platform name ('' when Qt is not importable yet)."""
    try:
        from PySide6.QtGui import QGuiApplication

        return QGuiApplication.platformName().lower()
    except (ImportError, AttributeError, RuntimeError):
        return ""


def _qt_reports_tray() -> bool:
    """Raw ``QSystemTrayIcon.isSystemTrayAvailable()`` (seam for tests)."""
    try:
        from PySide6.QtWidgets import QSystemTrayIcon

        return bool(QSystemTrayIcon.isSystemTrayAvailable())
    except (ImportError, AttributeError, RuntimeError):
        return False


def sni_watcher_available() -> bool:
    """True when a StatusNotifierWatcher (SNI host) owns its bus name."""
    return SNI_WATCHER_NAME in _session_bus_names()


def qt_tray_available() -> bool:
    """True when QSystemTrayIcon can actually display an icon.

    On X11 Qt checks both the SNI watcher and the legacy XEmbed tray
    window. On Wayland it reports the DBus tray as available even when no
    host exists yet (it registers on the fly later), so require a live SNI
    watcher there — otherwise close-to-tray would hide the window with no
    icon to restore it.
    """
    if not _qt_reports_tray():
        return False
    if _platform_name() == "xcb":
        return True
    return sni_watcher_available()


def xapp_monitor_available() -> bool:
    """True when an XApp status applet is listening on the session bus."""
    return any(n.startswith(XAPP_MONITOR_PREFIX) for n in _session_bus_names())


def xapp_runtime_available() -> bool:
    """True when the Python stack needed for the XApp backend is importable."""
    try:
        import dbus  # noqa: F401
        import dbus.service  # noqa: F401
        from gi.repository import GLib  # noqa: F401
    except (ImportError, ValueError):
        return False
    return True


def detect_tray_kind() -> str | None:
    """Return the best available tray backend for this session.

    Qt (SNI/XEmbed) wins when a host exists because it supports native
    menus; the XApp backend covers Mint panels that only host
    ``org.x.StatusIcon``.
    """
    if qt_tray_available():
        return KIND_QT
    if xapp_monitor_available() and xapp_runtime_available():
        return KIND_XAPP
    return None


def make_transparent_png(size: int = 22) -> str:
    """Create (once) a fully transparent tray PNG and return its path.

    Used for the azan flash; a null ``QIcon`` is interpreted by several
    SNI hosts as "remove the item", which used to make the icon vanish
    permanently after the first flash toggle.
    """
    path = os.path.join(tempfile.gettempdir(), f"athan-tray-blank-{size}.png")
    if os.path.isfile(path):
        return path
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        if not pixmap.save(path, "PNG"):
            return ""
    except (ImportError, RuntimeError, OSError):
        return ""
    return path if os.path.isfile(path) else ""


class TrayBackend(QObject):
    """Common interface implemented by every tray protocol wrapper."""

    activateRequested = Signal()
    menuRequested = Signal()

    kind = ""

    def __init__(self, icon_path: str, tooltip: str = "", parent=None):
        super().__init__(parent)
        self._icon_path = icon_path
        self._tooltip = tooltip

    def is_hosted(self) -> bool:
        """True only when an icon is actually visible to the user."""
        raise NotImplementedError

    def set_visible(self, visible: bool) -> None:
        raise NotImplementedError

    def set_tooltip(self, text: str) -> None:
        raise NotImplementedError

    def set_icon(self, path: str) -> None:
        raise NotImplementedError

    def show_message(self, title: str, body: str) -> bool:
        return False

    def destroy(self) -> None:
        raise NotImplementedError


class QtTrayBackend(TrayBackend):
    """QSystemTrayIcon backend (SNI on Wayland/modern X11, XEmbed on legacy)."""

    kind = KIND_QT

    def __init__(self, icon_path: str, tooltip: str = "", menu=None, parent=None):
        super().__init__(icon_path, tooltip, parent)
        from PySide6.QtWidgets import QSystemTrayIcon

        self._traymod = QSystemTrayIcon
        icon = QIcon(icon_path) if icon_path and os.path.isfile(icon_path) else QIcon()
        self._tray = QSystemTrayIcon(icon, parent)
        self._tray.setToolTip(tooltip)
        # Keep the QMenu alive: setContextMenu() does NOT take ownership and a
        # garbage-collected menu kills the right-click menu (or crashes).
        self._menu = menu
        if menu is not None:
            self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.messageClicked.connect(self.activateRequested)
        self._tray.show()

    def _on_activated(self, reason):
        reasons = self._traymod.ActivationReason
        if reason in (reasons.Trigger, reasons.DoubleClick, reasons.MiddleClick):
            self.activateRequested.emit()

    def is_hosted(self) -> bool:
        try:
            return bool(qt_tray_available() and self._tray.isVisible())
        except (AttributeError, RuntimeError):
            return False

    def set_visible(self, visible: bool) -> None:
        try:
            self._tray.setVisible(bool(visible))
        except (AttributeError, RuntimeError):
            pass

    def set_tooltip(self, text: str) -> None:
        self._tooltip = text
        try:
            self._tray.setToolTip(text)
        except (AttributeError, RuntimeError):
            pass

    def set_icon(self, path: str) -> None:
        icon = QIcon(path) if path and os.path.isfile(path) else QIcon()
        try:
            self._tray.setIcon(icon)
        except (AttributeError, RuntimeError):
            pass

    def show_message(self, title: str, body: str) -> bool:
        if not self.is_hosted():
            return False
        try:
            self._tray.showMessage(title, body, self._traymod.Information, 10000)
            return True
        except (AttributeError, RuntimeError, TypeError):
            return False

    def destroy(self) -> None:
        try:
            self._tray.hide()
            self._tray.setContextMenu(None)
        except (AttributeError, RuntimeError):
            pass
        self._tray.deleteLater()


class XAppTrayBackend(TrayBackend):
    """Native ``org.x.StatusIcon`` backend for Linux Mint status applets.

    Runs a private GLib main loop in a daemon thread because dbus-python is
    bound to GLib. Property changes are marshalled with ``GLib.idle_add``;
    clicks travel back as Qt signals (queued to the GUI thread).
    """

    kind = KIND_XAPP

    def __init__(self, icon_path: str, tooltip: str = "", menu=None, parent=None):
        super().__init__(icon_path, tooltip, parent)
        self._menu = menu  # kept for API symmetry; the panel calls ButtonPress
        self._service = f"{XAPP_BUS_PREFIX}athan{os.getpid()}"
        self._ready = threading.Event()
        self._error: Exception | None = None
        self._glib = None
        self._dbus = None
        self._loop = None
        self._owner = None
        self._icon_obj = None
        self._manager_obj = None
        self._state = {"icon": icon_path, "tooltip": tooltip, "visible": True}
        self._thread = threading.Thread(target=self._run, name="xapp-tray", daemon=True)
        self._thread.start()
        if not self._ready.wait(4.0):
            raise RuntimeError("XApp tray backend did not start in time")
        if self._error is not None:
            raise RuntimeError(f"XApp tray backend failed: {self._error}")

    # -- GLib thread ------------------------------------------------------
    def _run(self):
        try:
            import dbus
            import dbus.mainloop.glib
            import dbus.service
            from gi.repository import GLib

            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self._dbus = dbus
            self._glib = GLib
            bus = dbus.SessionBus()
            self._owner = dbus.service.BusName(self._service, bus, do_not_queue=True)
            backend = self

            class _Icon(dbus.service.Object):
                def __init__(self, conn, path):
                    super().__init__(conn, path)
                    self.props = {}

                def snapshot(self):
                    return dbus.Dictionary(self.props, signature="sv")

                @dbus.service.method("org.x.StatusIcon", in_signature="iiuui", out_signature="")
                def ButtonPress(self, x, y, button, time, panel_position):
                    backend._dispatch_button(int(button))

                @dbus.service.method("org.x.StatusIcon", in_signature="iiuui", out_signature="")
                def ButtonRelease(self, x, y, button, time, panel_position):
                    pass

                @dbus.service.method("org.x.StatusIcon", in_signature="iiu", out_signature="")
                def Scroll(self, delta, orientation, time):
                    pass

                @dbus.service.method(
                    "org.freedesktop.DBus.Properties", in_signature="ss", out_signature="v"
                )
                def Get(self, interface, prop):
                    return self.props.get(str(prop), dbus.String(""))

                @dbus.service.method(
                    "org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}"
                )
                def GetAll(self, interface):
                    return self.snapshot()

                @dbus.service.method(
                    "org.freedesktop.DBus.Properties", in_signature="ssv", out_signature=""
                )
                def Set(self, interface, prop, value):
                    self.props[str(prop)] = value

                @dbus.service.signal("org.freedesktop.DBus.Properties", signature="sa{sv}as")
                def PropertiesChanged(self, interface, changed, invalidated):
                    pass

            class _Manager(dbus.service.Object):
                def __init__(self, conn, path, icon):
                    super().__init__(conn, path)
                    self.icon = icon

                @dbus.service.method(
                    "org.freedesktop.DBus.ObjectManager", out_signature="a{oa{sa{sv}}}"
                )
                def GetManagedObjects(self):
                    return dbus.Dictionary(
                        {
                            dbus.ObjectPath(XAPP_ICON_PATH): dbus.Dictionary(
                                {"org.x.StatusIcon": self.icon.snapshot()}, signature="sa{sv}"
                            )
                        },
                        signature="oa{sa{sv}}",
                    )

                @dbus.service.signal("org.freedesktop.DBus.ObjectManager", signature="oa{sa{sv}}")
                def InterfacesAdded(self, path, interfaces):
                    pass

                @dbus.service.signal("org.freedesktop.DBus.ObjectManager", signature="oas")
                def InterfacesRemoved(self, path, interfaces):
                    pass

            self._icon_obj = _Icon(bus, XAPP_ICON_PATH)
            self._icon_obj.props = self._initial_props()
            self._manager_obj = _Manager(bus, XAPP_MANAGER_PATH, self._icon_obj)
            self._loop = GLib.MainLoop()
            self._ready.set()
            logger.info("XApp tray backend registered as %s", self._service)
            self._loop.run()
        except Exception as exc:  # noqa: BLE001 - surfaced to the GUI thread
            self._error = exc
            self._ready.set()
            logger.warning("XApp tray backend unavailable: %s", exc)

    def _initial_props(self):
        dbus = self._dbus
        icon = self._state["icon"]
        return {
            "Name": dbus.String("athan"),
            "IconName": dbus.String(icon if icon and os.path.isfile(icon) else ""),
            "TooltipText": dbus.String(self._state["tooltip"]),
            "Label": dbus.String(""),
            "Visible": dbus.Boolean(bool(self._state["visible"])),
            "IconSize": dbus.Int32(22),
            "PrimaryMenuIsOpen": dbus.Boolean(False),
            "SecondaryMenuIsOpen": dbus.Boolean(False),
            "Metadata": dbus.String(""),
        }

    def _dispatch_button(self, button: int):
        # Runs in the GLib thread; signals are queued to the GUI thread.
        if button in (1, 2):
            self.activateRequested.emit()
        elif button == 3:
            self.menuRequested.emit()

    # -- GUI thread -------------------------------------------------------
    def _update(self, **changes):
        glib = self._glib
        icon_obj = self._icon_obj
        if glib is None or icon_obj is None:
            self._state.update(changes)
            return

        def apply():
            try:
                dbus = self._dbus
                changed = {}
                for key, value in changes.items():
                    if key == "icon":
                        wrapped = dbus.String(value if value and os.path.isfile(value) else "")
                        target = "IconName"
                    elif key == "tooltip":
                        wrapped = dbus.String(value)
                        target = "TooltipText"
                    elif key == "visible":
                        wrapped = dbus.Boolean(bool(value))
                        target = "Visible"
                    else:
                        continue
                    icon_obj.props[target] = wrapped
                    changed[target] = wrapped
                    self._state[key] = value
                if changed:
                    icon_obj.PropertiesChanged(
                        "org.x.StatusIcon", dbus.Dictionary(changed, signature="sv"), []
                    )
            except Exception as exc:  # noqa: BLE001 - keep the thread alive
                logger.debug("XApp tray update failed: %s", exc)

        glib.idle_add(apply)

    def is_hosted(self) -> bool:
        return (
            self._ready.is_set()
            and self._error is None
            and self._icon_obj is not None
            and bool(self._state["visible"])
            and xapp_monitor_available()
        )

    def set_visible(self, visible: bool) -> None:
        self._state["visible"] = bool(visible)
        self._update(visible=bool(visible))

    def set_tooltip(self, text: str) -> None:
        self._state["tooltip"] = text
        self._update(tooltip=text)

    def set_icon(self, path: str) -> None:
        self._state["icon"] = path
        self._update(icon=path)

    def show_message(self, title: str, body: str) -> bool:
        glib = self._glib
        dbus = self._dbus
        if glib is None or dbus is None:
            return False

        def notify():
            try:
                obj = self._owner.get_bus().get_object(
                    "org.freedesktop.Notifications", "/org/freedesktop/Notifications"
                )
                iface = dbus.Interface(obj, "org.freedesktop.Notifications")
                iface.Notify("Athan Five Times", 0, "", str(title), str(body), [], {}, -1)
            except Exception:  # noqa: BLE001 - notifications are best-effort
                pass

        glib.idle_add(notify)
        return True

    def destroy(self) -> None:
        if self._loop is not None and self._glib is not None:
            self._glib.idle_add(self._loop.quit)
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._loop = None
        self._icon_obj = None
        self._manager_obj = None


def create_tray_backend(
    kind: str, icon_path: str, tooltip: str = "", menu=None, parent=None
) -> TrayBackend:
    if kind == KIND_QT:
        return QtTrayBackend(icon_path, tooltip, menu=menu, parent=parent)
    if kind == KIND_XAPP:
        return XAppTrayBackend(icon_path, tooltip, menu=menu, parent=parent)
    raise ValueError(f"Unknown tray backend: {kind!r}")


def _self_check() -> int:  # pragma: no cover - manual probe
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    print("qt_tray_available:", qt_tray_available())
    print("xapp_monitor_available:", xapp_monitor_available())
    print("xapp_runtime_available:", xapp_runtime_available())
    print("detect_tray_kind:", detect_tray_kind())
    del app
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_self_check())
