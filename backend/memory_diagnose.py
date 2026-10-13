#!/usr/bin/env python3
"""
Memory diagnostic for Athan Five Times.
Measures RSS/PSS at each initialization phase.
Usage:
  python -m backend.memory_diagnose              # offscreen
  QT_QPA_PLATFORM=xcb python -m backend.memory_diagnose  # X11
"""

import os
import sys
import gc
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


def measure_rss():
    gc.collect()
    with open(f"/proc/{os.getpid()}/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    return 0


def measure_pss():
    try:
        with open(f"/proc/{os.getpid()}/smaps_rollup") as f:
            for line in f:
                if line.startswith("Pss:"):
                    return int(line.split()[1])
    except FileNotFoundError:
        pass
    return 0


times = []


def phase(name):
    rss = measure_rss()
    pss = measure_pss()
    times.append((name, rss, pss))
    print(f"  [{name:58s}]  RSS={rss / 1024:7.2f} MB  PSS={pss / 1024:7.2f} MB")


def main():
    platform = os.environ.get("QT_QPA_PLATFORM", "offscreen")

    print("=" * 82)
    print(f"  Athan Five Times - Memory Diagnosis  (platform={platform})")
    print("=" * 82)

    phase("1. Python interpreter + stdlib")

    from PySide6.QtCore import QUrl, QCoreApplication

    phase("2. PySide6.QtCore")

    from PySide6.QtGui import QFont, QFontDatabase

    phase("3. PySide6.QtGui")

    from PySide6.QtWidgets import QApplication

    phase("4. PySide6.QtWidgets")

    from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
    from PySide6.QtQuickControls2 import QQuickStyle

    phase("5. PySide6.QtQml + QtQuickControls2")

    from backend.settings import load as load_settings, APP_VERSION

    phase("6. backend.settings")

    phase("7. backend.location")

    from backend.backend_controller import PrayerEngine
    from backend.theme_controller import ThemeController

    phase("8. backend.controllers + audio")

    QQuickStyle.setStyle("Fusion")
    app = QApplication(sys.argv[:1])
    phase("9. QApplication() created")

    assets_dir = os.path.join(BASE_DIR, "assets")
    fonts_dir = os.path.join(assets_dir, "fonts")
    if os.path.isdir(fonts_dir):
        for fname in sorted(os.listdir(fonts_dir)):
            if fname.lower().endswith(".ttf"):
                QFontDatabase.addApplicationFont(os.path.join(fonts_dir, fname))
    phase("10. Fonts loaded")

    font = QFont("Cairo", 14)
    if not font.exactMatch():
        font = QFont("Sans", 14)
    app.setFont(font)
    phase("11. Default font set")

    load_settings()
    phase("12. Settings loaded (+ PrayerTimes calc init)")

    qml_dir = os.path.join(BASE_DIR, "qml")
    engine = QQmlApplicationEngine()
    engine.addImportPath(qml_dir)
    phase("13. QQmlApplicationEngine created")

    qmlRegisterSingletonType(
        QUrl.fromLocalFile(os.path.join(qml_dir, "Theme.qml")), "Theme", 1, 0, "Theme"
    )
    phase("14. Theme singleton registered")

    theme_controller = ThemeController()
    prayer_engine = PrayerEngine()
    phase("15. Controllers instantiated")

    ctx = engine.rootContext()
    ctx.setContextProperty("prayerEngine", prayer_engine)
    ctx.setContextProperty("backendController", prayer_engine)
    ctx.setContextProperty("themeController", theme_controller)
    ctx.setContextProperty("appVersion", APP_VERSION)
    phase("16. Context properties set")

    qml_file = os.path.join(qml_dir, "main.qml")
    engine.load(QUrl.fromLocalFile(qml_file))
    gc.collect()
    QCoreApplication.processEvents()
    time.sleep(0.2)
    QCoreApplication.processEvents()
    gc.collect()
    phase("17. QML loaded (window ready, offscreen)")

    root = engine.rootObjects()[0]
    root.show()
    QCoreApplication.processEvents()
    gc.collect()
    QCoreApplication.processEvents()
    phase("18. Window shown")

    print()
    print("-" * 82)
    print(f"  {'Phase':58s}  {'RSS MB':>8s}  {'Δ MB':>7s}  {'PSS MB':>7s}")
    print("-" * 82)
    prev_rss = times[0][1]
    for name, rss, pss in times:
        delta = rss - prev_rss
        if name.startswith("1."):
            delta_str = "   --"
        else:
            delta_str = f"+{delta / 1024:6.2f}"
        print(f"  {name:58s}  {rss / 1024:8.2f}  {delta_str:>7s}  {pss / 1024:8.2f}")
        prev_rss = rss

    print("-" * 82)
    print(
        f"\n  Total RSS: {times[-1][1] / 1024:.1f} MB  |  Total PSS: {times[-1][2] / 1024:.1f} MB"
    )
    print("  X11 overhead: run again with QT_QPA_PLATFORM=xcb to measure\n")


if __name__ == "__main__":
    main()
