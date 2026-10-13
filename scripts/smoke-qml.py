#!/usr/bin/env python3
"""QML smoke gate: loads main.qml with the real backend, opens every dialog,
sweeps languages/themes, and FAILS on any QML TypeError/ReferenceError.

Usage: python3 scripts/smoke-qml.py [--display]
Without --display runs offscreen (load + bindings only).
"""
import os
import sys

if "--display" not in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtCore import QUrl, QTimer, qInstallMessageHandler, QtMsgType

ROOT = os.path.join(os.path.dirname(__file__), "..")
QML_DIR = os.path.join(ROOT, "qml")

errors: list = []


def _handler(mode, context, message):
    if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg,
                QtMsgType.QtFatalMsg):
        text = str(message)
        if ("TypeError" in text or "ReferenceError" in text
                or "Binding loop" in text or "Failed" in text):
            errors.append(f"{context.file}:{context.line}: {text}")


def main() -> int:
    qInstallMessageHandler(_handler)
    from backend.backend_controller import PrayerEngine
    from backend.theme_controller import ThemeController
    from backend.l10n import LanguageManager
    from backend.settings import APP_VERSION

    app = QApplication(sys.argv)
    eng = QQmlApplicationEngine()
    eng.addImportPath(QML_DIR)
    qmlRegisterSingletonType(QUrl.fromLocalFile(os.path.join(QML_DIR, "Theme.qml")),
                             "Theme", 1, 0, "Theme")
    pe, tc, lo = PrayerEngine(), ThemeController(), LanguageManager()
    ctx = eng.rootContext()
    ctx.setContextProperty("prayerEngine", pe)
    ctx.setContextProperty("backendController", pe)
    ctx.setContextProperty("themeController", tc)
    ctx.setContextProperty("l10n", lo)
    ctx.setContextProperty("appVersion", APP_VERSION)
    eng.load(QUrl.fromLocalFile(os.path.join(QML_DIR, "main.qml")))
    if not eng.rootObjects():
        print("SMOKE FAIL: main.qml did not load")
        return 1
    root = eng.rootObjects()[0]

    def walk(o, out):
        out.append(o)
        for k in o.children():
            walk(k, out)
        return out

    def drive():
        all_o = walk(root, [])
        n = len(pe.getPrayerTimes())
        print(f"prayer rows: {n}")
        assert n == 6, f"expected 6 prayer rows, got {n}"
        for o in all_o:
            try:
                if o.property("modal") is True:
                    o.open()
                    app.processEvents()
                    o.close()
                    app.processEvents()
            except Exception:
                pass
        print("dialogs opened+closed")
        for lang in ("en", "fr", "ar"):
            lo.setLanguage(lang)
            app.processEvents()
        print("languages swept")
        for th in ("light", "dark", "ottoman_gold", "catppuccin_mocha",
                   "catppuccin_latte", "auto"):
            tc.setTheme(th)
            app.processEvents()
        print("themes swept")
        app.quit()

    QTimer.singleShot(1500, drive)
    app.exec()
    pe.cleanup()
    if errors:
        print(f"SMOKE FAIL: {len(errors)} QML errors:")
        for e in errors[:20]:
            print("  " + e)
        return 1
    print("SMOKE OK: zero QML errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
