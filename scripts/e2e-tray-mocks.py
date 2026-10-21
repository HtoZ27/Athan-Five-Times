#!/usr/bin/env python3
"""Fake tray hosts for the isolated tray e2e runs (scripts/e2e-tray-envs.sh).

Modes:
  --monitor   Own a name under org.x.StatusIconMonitor.* (like Mint's
              xapp-status-plugin) so detect_tray_kind() sees an XApp host.
  --watcher   Implement org.kde.StatusNotifierWatcher (KDE/SNI protocol)
              claiming a registered host, and log every RegisterStatusNotifierItem.

Both run a GLib loop until SIGTERM.
"""
import argparse
import signal
import sys

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib


class SniWatcher(dbus.service.Object):
    def __init__(self, bus):
        super().__init__(bus, "/StatusNotifierWatcher")
        self.items = []

    def _props(self):
        return {
            "IsStatusNotifierHostRegistered": dbus.Boolean(True),
            "ProtocolVersion": dbus.Int32(0),
            "RegisteredStatusNotifierItems": dbus.Array(
                [dbus.String(i) for i in self.items], signature="s"
            ),
        }

    @dbus.service.method(
        "org.kde.StatusNotifierWatcher",
        in_signature="s",
        out_signature="",
        sender_keyword="sender",
    )
    def RegisterStatusNotifierItem(self, service, sender=None):
        service = str(service)
        if service.startswith("/"):
            name, path = str(sender), service
        else:
            name, path = service, "/StatusNotifierItem"
        item = name + path
        self.items.append(item)
        print(f"REGISTER_ITEM {name} {path}", flush=True)
        self.StatusNotifierItemRegistered(item)

    @dbus.service.method("org.kde.StatusNotifierWatcher", in_signature="s", out_signature="")
    def RegisterStatusNotifierHost(self, service):
        print(f"REGISTER_HOST {service}", flush=True)

    @dbus.service.method(
        "org.freedesktop.DBus.Properties", in_signature="ss", out_signature="v"
    )
    def Get(self, interface, prop):
        return self._props().get(str(prop), dbus.Boolean(False))

    @dbus.service.method(
        "org.freedesktop.DBus.Properties", in_signature="s", out_signature="a{sv}"
    )
    def GetAll(self, interface):
        return dbus.Dictionary(self._props(), signature="sv")

    @dbus.service.signal("org.kde.StatusNotifierWatcher", signature="s")
    def StatusNotifierItemRegistered(self, service):
        pass

    @dbus.service.signal("org.kde.StatusNotifierWatcher")
    def StatusNotifierHostRegistered(self):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--monitor", action="store_true")
    group.add_argument("--watcher", action="store_true")
    args = parser.parse_args()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()

    if args.monitor:
        name = dbus.service.BusName("org.x.StatusIconMonitor.e2e", bus)
        print(f"MONITOR_READY {name.get_name()}", flush=True)
    else:
        # Keep a strong reference: dbus-python releases the name as soon as
        # the BusName object is garbage-collected.
        watcher_name = dbus.service.BusName(
            "org.kde.StatusNotifierWatcher", bus, do_not_queue=True
        )
        watcher = SniWatcher(bus)  # noqa: F841 - kept alive for the loop
        print(f"WATCHER_READY {watcher_name.get_name()}", flush=True)

    loop = GLib.MainLoop()
    signal.signal(signal.SIGTERM, lambda *_: loop.quit())
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
