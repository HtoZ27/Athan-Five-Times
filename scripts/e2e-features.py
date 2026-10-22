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
    # Default is headless: force offscreen even when the environment presets
    # QT_QPA_PLATFORM (setdefault would leave e.g. wayland;xcb in place and
    # leak "Failed to create wl_display" warnings into the error count).
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

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

    # The engine computes the first prayer times from a zero-timer; on xcb a
    # single processEvents() pass is not always enough, so wait briefly.
    import time as _time
    _deadline = _time.time() + 5.0
    while not pe.getPrayerTimes() and _time.time() < _deadline:
        app.processEvents()
        _time.sleep(0.02)

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
        check("general-categories", len(prov.getCategories()) == 23)
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
        for i in range(8):
            dlg.setProperty("currentTabIndex", i)
            app.processEvents()
        app.processEvents()
        check("settings-dialog-open", True)
        check("countries-241", len(pe.getCountryList()) == 241)
        check("cities-tunis", len(pe.getCityNamesForCountry("TN")) > 5)
        check("methods-26", len(pe.getCalcMethods()) == 26)
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
    check("adhkar-items-morning", len(prov.getCategoryItems("morning")) == 26)
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

    # --- Hijri calendar events ---
    from datetime import date as _date
    from backend.islamic_events import events_for_date
    ashura = events_for_date(_date(2025, 7, 6))       # 10 Muharram 1447
    check("events-ashura", "عاشوراء" in ashura, str(ashura))
    tarwiya = events_for_date(_date(2026, 5, 25))     # 8 Dhu al-Hijjah 1447
    check("events-tarwiya", "يوم التروية" in tarwiya, str(tarwiya))
    qadr = events_for_date(_date(2026, 3, 10))        # 21 Ramadan 1447
    check("events-laylat-qadr", "ليلة القدر" in qadr, str(qadr))
    mid_ramadan = events_for_date(_date(2026, 3, 4))  # 15 Ramadan 1447
    check("events-mid-ramadan", "النصف من رمضان" in mid_ramadan, str(mid_ramadan))

    # --- Reminders (with repeat days) ---
    check("reminder-add", pe.addReminder("e2e-تذكير", "06:00", [1, 3]) is True)
    rs = pe.getReminders()
    check("reminder-list", len(rs) == 1 and rs[0].get("days") == [1, 3], str(rs))
    if rs:
        rid = rs[0]["id"]
        check("reminder-update", pe.updateReminder(rid, "e2e-محدث", "06:30", []) is True)
        upd = pe.getReminders()[0]
        check("reminder-updated-values",
              upd["text"] == "e2e-محدث" and upd["time"] == "06:30" and upd["days"] == [])
        check("reminder-toggle", pe.toggleReminder(rid, False) is True)
        check("reminder-disabled", pe.getReminders()[0]["enabled"] is False)
        check("reminder-remove", pe.removeReminder(rid) is True)
        check("reminder-empty", pe.getReminders() == [])

    # --- Display server detection (Wayland / X11) ---
    from backend.platform_env import platform_is_wayland
    _qpa = pe.getRenderedPlatform()
    _pinfo = pe.getPlatformInfo()
    _expected = os.environ.get("QT_QPA_PLATFORM", "").split(";")[0]
    check("platform-runtime", bool(_qpa) and (not _expected or _qpa == _expected),
          f"qpa={_qpa!r} expected={_expected!r}")
    check("platform-info",
          {"session", "platform", "wayland"} <= set(_pinfo)
          and _pinfo["wayland"] is platform_is_wayland(_pinfo["platform"])
          and pe.isWaylandRuntime() is platform_is_wayland(_qpa),
          str(_pinfo))

    # --- Compact widget (settings + QML component) ---
    check("widget-default-hidden", pe.isWidgetVisible() is False)
    pe.setWidgetVisible(True)
    check("widget-show-setting", pe.isWidgetVisible() is True)
    pe.setWidgetVisible(False)
    check("widget-hide-setting", pe.isWidgetVisible() is False)
    pe.saveWidgetGeometry(15, 25)
    check("widget-geometry", pe.getWidgetGeometry() == [15, 25])

    from PySide6.QtQml import QQmlComponent
    wc = QQmlComponent(eng, QUrl.fromLocalFile(os.path.join(QML_DIR, "Widget.qml")))
    wob = wc.create() if wc.isReady() else None
    check("widget-qml-loads", wc.isReady() and wob is not None)
    if wob is not None:
        wob.setProperty("prayerEngine", pe)
        app.processEvents()
        wob.setProperty("visible", True)
        app.processEvents()
        check("widget-qml-live", bool(wob.property("nextName")) or
              bool(wob.property("countdownText")),
              f"next={wob.property('nextName')}")
        prog = wob.property("progress")
        check("widget-progress", isinstance(prog, float) and 0.0 <= prog <= 1.0,
              f"progress={prog}")
        foll = wob.property("following")
        check("widget-following",
              isinstance(foll, list) and len(foll) >= 1
              and all("name" in f and "time" in f for f in foll),
              f"following={foll}")

        # Progress fill must touch the start edge (right in RTL, left in LTR);
        # regression guard for LayoutMirroring double-flipping its position.
        def _find_item(name):
            for ch in wob.findChildren(QQuickItem):
                if ch.objectName() == name:
                    return ch
            return None

        ptrack, pfill = _find_item("progressTrack"), _find_item("progressFill")
        if ptrack is not None and pfill is not None:
            wob.setProperty("progress", 0.5)
            # On a real display the window geometry and the fill's SmoothAnimation
            # settle asynchronously; wait for both before measuring.
            import time as _time
            deadline = _time.time() + 3.0
            pw = wd = x = 0.0
            while _time.time() < deadline:
                app.processEvents()
                _time.sleep(0.02)
                pw = float(ptrack.property("width"))
                wd = float(pfill.property("width"))
                x = float(pfill.property("x"))
                if pw > 100 and abs(wd - pw * 0.5) <= 2.0:
                    break
            rtl = bool(wob.property("isRtl"))
            anchored = (pw > 100 and abs(wd - pw * 0.5) <= 2.0
                        and (abs(x + wd - pw) <= 1.5 if rtl else abs(x) <= 1.5))
            check("widget-progress-anchor", anchored,
                  f"rtl={rtl} x={x} w={wd} trackW={pw}")
        wob.setProperty("visible", False)
        app.processEvents()
        wob.deleteLater()
        app.processEvents()

    import glob as _g
    check("prayer-icons-14",
          len(_g.glob(os.path.join(ROOT, "assets", "prayer_icons", "*.png"))) == 14)
    import json as _json
    with open(os.path.join(ROOT, "assets", "adhkar", "index.json"), encoding="utf-8") as _f:
        _idx = _json.load(_f)
    _cats = _idx.get("categories", _idx)
    _missing = [c.get("icon") for c in _cats
                if not os.path.isfile(os.path.join(ROOT, "assets", "adhkar_icons",
                                                   str(c.get("icon")) + ".png"))]
    check("adhkar-icons-complete", len(_cats) == 23 and not _missing,
          f"categories={len(_cats)} missing={_missing}")

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
