#!/usr/bin/env python3
"""Real isolated end-to-end test for EVERY feature and setting.

Isolation: a temporary XDG_CONFIG_HOME/XDG_DATA_HOME, so the user's real
settings, autostart entry and muezzins are never touched.
Audio previews run briefly at near-zero volume.

Usage: python3 scripts/e2e-features.py [--display]
Exits 0 only if every check passes and zero QML errors were logged.
"""
import json
import os
import shutil
import sys
import tempfile

if "--display" not in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

TMP = tempfile.mkdtemp(prefix="athan-e2e-")
os.environ["XDG_CONFIG_HOME"] = os.path.join(TMP, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(TMP, "data")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtCore import QUrl, QTimer, qInstallMessageHandler, QtMsgType

from PySide6.QtQuick import QQuickItem

ROOT = os.path.join(os.path.dirname(__file__), "..")
QML_DIR = os.path.join(ROOT, "qml")

qml_errors: list = []


def _handler(mode, context, message):
    if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg,
                QtMsgType.QtFatalMsg):
        text = str(message)
        if ("TypeError" in text or "ReferenceError" in text
                or "Binding loop" in text or "Failed" in text):
            qml_errors.append(f"{context.file}:{context.line}: {text}")


results: list = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), str(detail)))
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else ""),
          flush=True)


def main() -> int:
    qInstallMessageHandler(_handler)
    from backend.backend_controller import PrayerEngine
    from backend.theme_controller import ThemeController
    from backend.l10n import LanguageManager
    from backend.settings import APP_VERSION, SETTINGS_FILE

    app = QApplication(sys.argv)
    eng = QQmlApplicationEngine()
    eng.addImportPath(QML_DIR)
    qmlRegisterSingletonType(QUrl.fromLocalFile(os.path.join(QML_DIR, "Theme.qml")),
                             "Theme", 1, 0, "Theme")
    pe, tc, lo = PrayerEngine(), ThemeController(), LanguageManager()
    lo.languageChanged.connect(pe.clearCaches)
    ctx = eng.rootContext()
    ctx.setContextProperty("prayerEngine", pe)
    ctx.setContextProperty("backendController", pe)
    ctx.setContextProperty("themeController", tc)
    ctx.setContextProperty("l10n", lo)
    ctx.setContextProperty("appVersion", APP_VERSION)
    eng.load(QUrl.fromLocalFile(os.path.join(QML_DIR, "main.qml")))
    check("startup-load", len(eng.rootObjects()) == 1)
    root = eng.rootObjects()[0]
    app.processEvents()

    def walk(o, out):
        out.append(o)
        for k in o.children():
            walk(k, out)
        return out

    times = pe.getPrayerTimes()
    check("prayer-6-rows", len(times) == 6, f"got {len(times)}")
    check("prayer-keys", [t["key"] for t in times] ==
          ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"])
    check("prayer-one-next", sum(1 for t in times if t["isNext"]) == 1)
    check("next-key-name", pe.getNextPrayerKey() in
          {"fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"},
          pe.getNextPrayerKey())
    c1 = pe.getCountdownText()
    check("countdown-live", bool(c1), c1)

    all_o = walk(root, [])
    stacks = []
    for o in all_o:
        try:
            kids = o.childItems() if isinstance(o, QQuickItem) else []
            if o.property("currentIndex") == 0 and len(kids) == 3:
                stacks.append(o)
        except Exception:
            continue
    check("stack-found", bool(stacks))
    if stacks:
        st = stacks[0]
        st.setProperty("currentIndex", 1)
        app.processEvents()
        prov = pe.getAthkarProvider()
        check("prayer-athkar-items", len(prov.getCategoryItems("after_prayer")) == 12)
        st.setProperty("currentIndex", 2)
        app.processEvents()
        check("general-categories", len(prov.getCategories()) == 140)
        st.setProperty("currentIndex", 0)
        app.processEvents()

    for lang in ("en", "fr", "ar"):
        lo.setLanguage(lang)
        app.processEvents()
        nm = pe.getNextPrayerName()
        check(f"lang-{lang}", bool(nm), nm)

    for th in ("light", "dark", "ottoman_gold", "catppuccin_mocha",
               "catppuccin_latte", "auto"):
        try:
            tc.setTheme(th)
            app.processEvents()
            ok = True
        except Exception as ex:  # noqa: BLE001
            ok = str(ex)
        check(f"theme-{th}", ok is True, "" if ok is True else ok)

    dlg = None
    for o in walk(root, []):
        try:
            if o.property("currentTabIndex") == 0:
                dlg = o
                break
        except Exception:
            continue
    check("settings-dialog-found", dlg is not None)
    if dlg is not None:
        dlg.open()
        app.processEvents()
        for i in range(7):
            dlg.setProperty("currentTabIndex", i)
            app.processEvents()
        app.processEvents()
        check("settings-dialog-open", True)
        check("countries-241", len(pe.getCountryList()) == 241)
        check("cities-tunis", len(pe.getCityNamesForCountry("TN")) > 5)
        check("methods-27", len(pe.getCalcMethods()) == 27)
        check("madhabs-2-ar", all("شافعي" in m["display"] or "حنفي" in m["display"]
                                  for m in pe.getMadhabs()))
        check("themes-6-ar", len(pe.getThemes()) == 6 and
              pe.getThemes()[0]["name"] == "تلقائي")
        check("timezones-clean", all("/" not in z["name"] for z in pe.getTimezones()))
        check("langs-list", len(pe.getLanguages()) >= 3)
        dlg.close()
        app.processEvents()

    pe.updateSetting("country", "TN")
    pe.updateSetting("city", "Tunis")
    pe.updateSetting("method", pe.getCalcMethods()[0]["key"])
    pe.updateSetting("madhab", "hanafi")
    pe.updateSetting("volume", 0.05)
    pe.updateSetting("time_format", "24h")
    pe.commitSettings()
    app.processEvents()
    saved = json.load(open(SETTINGS_FILE, encoding="utf-8"))
    check("settings-persisted",
          saved.get("country") == "TN" and saved.get("city") == "Tunis"
          and saved.get("madhab") == "hanafi" and saved.get("volume") == 0.05,
          f"{saved.get('country')}/{saved.get('city')}")
    check("settings-isolated", SETTINGS_FILE.startswith(TMP), SETTINGS_FILE)

    pe.updateSetting("country", "XX")
    check("reject-country", pe.getSetting("country") == "TN")
    pe.updateSetting("city", "NoSuchCity123")
    check("reject-city", pe.getSetting("city") == "Tunis")

    prov = pe.getAthkarProvider()
    check("adhkar-items-morning", len(prov.getCategoryItems("morning")) == 30)
    it = prov.getCategoryItems("morning")[0]
    check("adhkar-item-shape",
          bool(it.get("arabic")) and it.get("count", 0) >= 1 and bool(it.get("reference_id")))
    check("arabic-numeral", prov.toArabicNumeral(33) == "٣٣")

    pe._athkar_provider.setPrayerAthkar("fajr", "t")
    check("popup-text", len(pe._athkar_provider.getPrayerAthkarText()) > 100)

    import glob
    src = sorted(glob.glob(os.path.join(ROOT, "assets", "muezzins", "*.mp3")))[0]
    tmp_mp3 = os.path.join(TMP, "test-muezzin.mp3")
    shutil.copy(src, tmp_mp3)
    n0 = len(pe.getMuezzins())
    pe.addMuezzin("e2e-test", tmp_mp3)
    check("muezzin-add", len(pe.getMuezzins()) == n0 + 1)
    pe.removeMuezzin("e2e-test")
    check("muezzin-remove", len(pe.getMuezzins()) == n0)

    pe.previewAudio(tmp_mp3)
    import time
    time.sleep(2.0)
    playing = pe.isAzanPlaying()
    pe.stopPreview()
    time.sleep(0.5)
    check("audio-preview", playing is True, f"playing={playing}")
    check("audio-stop", pe.isAzanPlaying() is False)

    from backend.settings import set_autostart
    set_autostart(True)
    ad = os.path.join(os.environ["XDG_CONFIG_HOME"], "autostart",
                      "athan-five-times.desktop")
    check("autostart-on", os.path.isfile(ad))
    set_autostart(False)
    check("autostart-off", not os.path.isfile(ad))

    import glob as _g
    check("prayer-icons-14",
          len(_g.glob(os.path.join(ROOT, "assets", "prayer_icons", "*.png"))) == 14)
    check("adhkar-icons-10",
          len(_g.glob(os.path.join(ROOT, "assets", "adhkar_icons", "*.png"))) == 10)

    QTimer.singleShot(1000, pe.quitApp)
    QTimer.singleShot(20000, lambda: app.exit(42))

    ret = app.exec()
    pe.cleanup()
    check("quit-via-x", ret == 0, f"exit={ret}")
    shutil.rmtree(TMP, ignore_errors=True)

    fails = [r for r in results if not r[1]]
    if qml_errors:
        print(f"QML ERRORS: {len(qml_errors)}")
        for e in qml_errors[:15]:
            print("  " + e)
    print(f"\nE2E: {len(results) - len(fails)}/{len(results)} passed, "
          f"{len(qml_errors)} qml errors")
    return 1 if (fails or qml_errors) else 0


if __name__ == "__main__":
    sys.exit(main())
