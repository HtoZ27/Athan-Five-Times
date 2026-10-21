#!/usr/bin/env python3
"""Drive a tray backend against a real (mock) host in an isolated session.

Runs inside scripts/e2e-tray-envs.sh; not meant for daily use.
Writes a JSON readiness file (--ready-file) once the backend attempted to
register, then exercises tooltip/icon updates and prints EVENT/STATE lines:

    EVENT kind=<qt|xapp|null>      detected backend
    EVENT ACTIVATE / EVENT MENU    click signals received from the host
    STATE hosted=<True|False>      tray_backend.is_hosted() at that moment
"""
import argparse
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.normpath(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def emit(line: str):
    print(line, flush=True)


def write_ready(path: str, payload: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("auto", "qt", "xapp"), default="auto")
    parser.add_argument("--duration", type=float, default=7.0)
    parser.add_argument("--ready-file", required=True)
    parser.add_argument("--icon", default="")
    args = parser.parse_args()

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from backend import tray_backend as tb

    app = QApplication([])
    icon = args.icon or os.path.join(
        os.path.normpath(ROOT), "assets", "tray", "mosque-22.png"
    )

    kind = args.kind
    if kind == "auto":
        kind = tb.detect_tray_kind()
        emit(f"EVENT kind={kind}")
        if kind is None:
            write_ready(args.ready_file, {"pid": os.getpid(), "kind": None, "hosted": False})
            return 0

    try:
        backend = tb.create_tray_backend(kind, icon, "e2e tooltip")
    except (RuntimeError, ValueError) as exc:
        emit(f"ERROR backend={kind} {exc}")
        write_ready(args.ready_file, {"pid": os.getpid(), "kind": kind, "hosted": False})
        return 4

    backend.activateRequested.connect(lambda: emit("EVENT ACTIVATE"))
    backend.menuRequested.connect(lambda: emit("EVENT MENU"))
    if kind == "qt":
        from PySide6.QtWidgets import QSystemTrayIcon

        emit(
            "EVENT qt avail={} visible={}".format(
                QSystemTrayIcon.isSystemTrayAvailable(), backend._tray.isVisible()
            )
        )
    write_ready(
        args.ready_file,
        {"pid": os.getpid(), "kind": kind, "hosted": backend.is_hosted()},
    )
    emit(f"EVENT kind={kind}")

    blank = tb.make_transparent_png(22)
    QTimer.singleShot(1000, lambda: backend.set_tooltip("e2e tooltip updated"))
    QTimer.singleShot(2000, lambda: backend.set_icon(blank or ""))
    QTimer.singleShot(3000, lambda: backend.set_icon(icon))
    QTimer.singleShot(4000, lambda: emit(f"STATE hosted={backend.is_hosted()}"))
    QTimer.singleShot(int(args.duration * 1000), app.quit)

    app.exec()
    emit(f"STATE hosted={backend.is_hosted()}")
    emit("EVENT done")
    backend.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
