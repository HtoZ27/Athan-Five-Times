#!/usr/bin/env python3
"""Minimal classic XEmbed system tray manager for e2e runs.

Owns ``_NET_SYSTEM_TRAY_S<screen>`` on the given X display, announces itself
with the ICCCM MANAGER client message and logs dock requests, without any
extra Python dependency: libX11 is called through ctypes. Used by
``scripts/e2e-tray-envs.sh --scenario-xembed`` to exercise the legacy
XI1/XEmbed path that QSystemTrayIcon uses on plain XFCE, Openbox or i3.
"""
import argparse
import ctypes
import ctypes.util
import signal
import sys
import time

CURRENT_TIME = 0
CLIENT_MESSAGE = 33
STRUCTURE_NOTIFY_MASK = 1 << 17
XA_VISUALID = 32
PROP_MODE_REPLACE = 0


class XClientMessageEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("message_type", ctypes.c_ulong),
        ("format", ctypes.c_int),
        ("data", ctypes.c_long * 5),
    ]


def load_x11():
    name = ctypes.util.find_library("X11")
    if not name:
        raise RuntimeError("libX11 not found")
    x11 = ctypes.cdll.LoadLibrary(name)
    display = ctypes.c_void_p
    x11.XOpenDisplay.restype = display
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XInternAtom.restype = ctypes.c_ulong
    x11.XInternAtom.argtypes = [display, ctypes.c_char_p, ctypes.c_int]
    x11.XDefaultScreen.restype = ctypes.c_int
    x11.XDefaultScreen.argtypes = [display]
    x11.XRootWindow.restype = ctypes.c_ulong
    x11.XRootWindow.argtypes = [display, ctypes.c_int]
    x11.XCreateSimpleWindow.restype = ctypes.c_ulong
    x11.XCreateSimpleWindow.argtypes = [
        display, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
        ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    x11.XSetSelectionOwner.argtypes = [display, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    x11.XGetSelectionOwner.restype = ctypes.c_ulong
    x11.XGetSelectionOwner.argtypes = [display, ctypes.c_ulong]
    x11.XSendEvent.argtypes = [display, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
    x11.XFlush.argtypes = [display]
    x11.XPending.restype = ctypes.c_int
    x11.XPending.argtypes = [display]
    x11.XNextEvent.argtypes = [display, ctypes.c_void_p]
    x11.XDefaultVisual.restype = ctypes.c_void_p
    x11.XDefaultVisual.argtypes = [display, ctypes.c_int]
    x11.XVisualIDFromVisual.restype = ctypes.c_ulong
    x11.XVisualIDFromVisual.argtypes = [ctypes.c_void_p]
    x11.XChangeProperty.argtypes = [
        display, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int,
    ]
    return x11


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--display", required=True)
    parser.add_argument("--screen", type=int, default=0)
    args = parser.parse_args()

    x11 = load_x11()
    dpy = x11.XOpenDisplay(args.display.encode())
    if not dpy:
        print(f"cannot open display {args.display}", file=sys.stderr, flush=True)
        return 2

    root = x11.XRootWindow(dpy, args.screen)
    selection = x11.XInternAtom(dpy, f"_NET_SYSTEM_TRAY_S{args.screen}".encode(), 0)
    manager = x11.XInternAtom(dpy, b"MANAGER", 0)
    opcode = x11.XInternAtom(dpy, b"_NET_SYSTEM_TRAY_OPCODE", 0)
    visual_atom = x11.XInternAtom(dpy, b"_NET_SYSTEM_TRAY_VISUAL", 0)

    tray = x11.XCreateSimpleWindow(dpy, root, -10, -10, 1, 1, 0, 0, 0)
    visual = ctypes.c_ulong(
        x11.XVisualIDFromVisual(x11.XDefaultVisual(dpy, args.screen))
    )
    x11.XChangeProperty(
        dpy, tray, visual_atom, XA_VISUALID, 32, PROP_MODE_REPLACE,
        ctypes.byref(visual), 1,
    )
    x11.XSetSelectionOwner(dpy, selection, tray, CURRENT_TIME)
    x11.XFlush(dpy)

    if x11.XGetSelectionOwner(dpy, selection) != tray:
        print("failed to own the system tray selection", file=sys.stderr, flush=True)
        return 3

    event = XClientMessageEvent()
    event.type = CLIENT_MESSAGE
    event.send_event = 1
    event.window = root
    event.message_type = manager
    event.format = 32
    event.data[0] = CURRENT_TIME
    event.data[1] = selection
    event.data[2] = tray
    x11.XSendEvent(dpy, root, 0, STRUCTURE_NOTIFY_MASK, ctypes.byref(event))
    x11.XFlush(dpy)

    print(
        f"XEMBED_READY selection=_NET_SYSTEM_TRAY_S{args.screen} window={tray}",
        flush=True,
    )

    running = True

    def stop(*_args):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    buffer = ctypes.create_string_buffer(192)
    while running:
        while x11.XPending(dpy):
            x11.XNextEvent(dpy, ctypes.cast(buffer, ctypes.c_void_p))
            message = ctypes.cast(buffer, ctypes.POINTER(XClientMessageEvent)).contents
            if message.type == CLIENT_MESSAGE and message.message_type == opcode:
                if message.data[1] == 0:
                    print(f"DOCK window={message.data[2]}", flush=True)
        time.sleep(0.05)
    return 0


if __name__ == "__main__":
    sys.exit(main())
