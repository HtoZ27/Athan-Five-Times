"""
Display-server (Wayland / X11) detection and QPA normalization.

The app must start cleanly on both Wayland and X11 sessions:

* ``prepare_display_env()`` runs before ``QApplication`` exists. It inspects
  ``QT_QPA_PLATFORM`` and drops candidates whose runtime socket is missing —
  e.g. the common distro preset ``wayland;xcb`` on an X11 session used to
  attempt Wayland first and print ``Failed to create wl_display`` warnings on
  every start. Single explicit choices are respected untouched.
* ``session_type()`` reports the desktop session (Wayland/X11/…).
* ``platform_is_wayland()`` classifies the QPA platform actually in use once
  Qt is up (``QGuiApplication.platformName()``): this is the authoritative
  source for runtime behaviour — an app under XWayland reports ``xcb`` and
  should keep X11 window semantics.

No Qt imports here: the module is safe to import before Qt initializes.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _runtime_dir() -> str:
    return os.environ.get("XDG_RUNTIME_DIR") or "/run/user/%d" % os.getuid()


def wayland_available() -> bool:
    """True when WAYLAND_DISPLAY points at a reachable compositor socket."""
    name = os.environ.get("WAYLAND_DISPLAY", "").strip()
    if not name:
        return False
    sock = Path(name) if name.startswith("/") else Path(_runtime_dir()) / name
    try:
        return sock.is_socket()
    except OSError:
        return False


def x11_available() -> bool:
    """True when a DISPLAY is declared.

    Socket probing is unreliable here (X servers commonly listen on abstract
    sockets, not files), so the presence of DISPLAY is the signal.
    """
    return bool(os.environ.get("DISPLAY", "").strip())


def session_type() -> str:
    """Return the desktop session: "wayland", "x11", "tty" or "unknown"."""
    declared = (os.environ.get("XDG_SESSION_TYPE") or "").strip().lower()
    if declared in ("wayland", "x11", "tty"):
        return declared
    if wayland_available():
        return "wayland"
    if x11_available():
        return "x11"
    return "unknown"


def platform_is_wayland(platform_name: str) -> bool:
    """Classify a Qt platform name ("wayland", "wayland-egl", "xcb", …)."""
    return (platform_name or "").strip().lower().startswith("wayland")


def prepare_qpa_platform() -> str:
    """Normalize a multi-entry QT_QPA_PLATFORM list in place.

    Only lists (``a;b;c``) are touched; an explicit single platform is left
    untouched so user overrides keep working. Entries whose runtime is
    unreachable are dropped (wayland with no socket / xcb with no DISPLAY).
    Returns the effective value ("" means "leave the choice to Qt").
    """
    current = os.environ.get("QT_QPA_PLATFORM", "").strip()
    if not current:
        return ""
    parts = [p.strip().lower() for p in current.split(";") if p.strip()]
    if len(parts) <= 1:
        return current

    kept = []
    for p in parts:
        if p.startswith("wayland") and not wayland_available():
            continue
        if p in ("xcb", "x11") and not x11_available():
            continue
        kept.append(p)
    if kept and kept != parts:
        os.environ["QT_QPA_PLATFORM"] = ";".join(kept)
    # If nothing is reachable keep the original list: Qt will surface its own
    # diagnostic instead of us guessing a platform that is equally absent.
    return os.environ.get("QT_QPA_PLATFORM", "")


def prepare_display_env() -> dict:
    """Startup hook: normalize QPA and log the detected environment."""
    effective = prepare_qpa_platform()
    info = {
        "session": session_type(),
        "qpa_setting": effective,
        "wayland_socket": wayland_available(),
        "x11_display": x11_available(),
    }
    logger.info(
        "Display environment: session=%s qpa=%s wayland_socket=%s x11_display=%s",
        info["session"],
        effective or "<auto>",
        info["wayland_socket"],
        info["x11_display"],
    )
    return info
