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
from PySide6.QtCore import QUrl, QTimer, qInstallMessageHandler, QtMsgType, QPoint, Qt, QEvent

from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtQuick import QQuickItem

ROOT = os.path.join(os.path.dirname(__file__), "..")
QML_DIR = os.path.join(ROOT, "qml")

qml_errors: list = []


def _handler(mode, context, message):
    if mode in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        text = str(message)
        if (
            "TypeError" in text
            or "ReferenceError" in text
            or "Binding loop" in text
            or "Failed" in text
        ):
            qml_errors.append(f"{context.file}:{context.line}: {text}")


results: list = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), str(detail)))
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else ""), flush=True)


def main() -> int:
    qInstallMessageHandler(_handler)
    from backend.backend_controller import PrayerEngine
    from backend.theme_controller import ThemeController
    from backend.l10n import LanguageManager
    from backend.settings import APP_VERSION, SETTINGS_FILE

    app = QApplication(sys.argv)
    eng = QQmlApplicationEngine()
    eng.addImportPath(QML_DIR)
    qmlRegisterSingletonType(
        QUrl.fromLocalFile(os.path.join(QML_DIR, "Theme.qml")), "Theme", 1, 0, "Theme"
    )
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
    check(
        "prayer-keys",
        [t["key"] for t in times] == ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"],
    )
    check("prayer-one-next", sum(1 for t in times if t["isNext"]) == 1)
    check(
        "next-key-name",
        pe.getNextPrayerKey() in {"fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"},
        pe.getNextPrayerKey(),
    )
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

    # Every shipped language, through the same path the settings dialog uses.
    from backend._constants import LANGS

    _rtl_langs = {"ar", "ur", "ps", "pa"}
    for lang in LANGS:
        lo.setLanguage(lang)
        pe.updateSetting("language", lang)
        pe.commitSettings()
        app.processEvents()
        nm = pe.getNextPrayerName()
        rows = pe.getPrayerTimes()
        row_name = rows[0]["name"] if rows else ""
        check(f"lang-{lang}", bool(nm) and bool(row_name), f"{nm}/{row_name}")
        check(f"lang-rtl-{lang}", pe.isRtl() is (lang in _rtl_langs))
    lo.setLanguage("ar")
    pe.updateSetting("language", "ar")
    pe.commitSettings()
    app.processEvents()

    for th in ("light", "dark", "ottoman_gold", "catppuccin_mocha", "catppuccin_latte", "auto"):
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
        check("methods-36", len(pe.getCalcMethods()) == 36)
        check(
            "madhabs-2-ar",
            all("شافعي" in m["display"] or "حنفي" in m["display"] for m in pe.getMadhabs()),
        )
        check("themes-6-ar", len(pe.getThemes()) == 6 and pe.getThemes()[0]["name"] == "تلقائي")
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
    check(
        "settings-persisted",
        saved.get("country") == "TN"
        and saved.get("city") == "Tunis"
        and saved.get("madhab") == "hanafi"
        and saved.get("volume") == 0.05,
        f"{saved.get('country')}/{saved.get('city')}",
    )
    check("settings-isolated", SETTINGS_FILE.startswith(TMP), SETTINGS_FILE)

    pe.updateSetting("country", "XX")
    check("reject-country", pe.getSetting("country") == "TN")
    pe.updateSetting("city", "NoSuchCity123")
    check("reject-city", pe.getSetting("city") == "Tunis")

    # City altitude map through the real controller, still isolated.
    from backend.prayer_calc import calculate as _calc

    def _calc_with_altitude(country, city, method, tz, altitude):
        return _calc(
            pe.getSetting("latitude"),
            pe.getSetting("longitude"),
            target_date=pe._result.calc_date,
            method_name=method,
            tz_name=tz,
            city_name=city,
            country_code=country,
            altitude=altitude,
        )

    def _engine_matches_altitude(country, city, method, tz, altitude):
        expected = _calc_with_altitude(country, city, method, tz, altitude)
        return expected is not None and pe._result.sunrise == expected.sunrise

    pe.updateSetting("country", "MA")
    pe.updateSetting("city", "Marrakesh")
    pe.updateSetting("method", "Morocco")
    pe.updateSetting("timezone", "Africa/Casablanca")
    pe.updateSetting("custom_coords", False)
    pe.commitSettings()
    pe.recalculate()
    app.processEvents()
    check(
        "altitude-map-marrakesh",
        _engine_matches_altitude("MA", "Marrakesh", "Morocco", "Africa/Casablanca", 457.0),
    )
    sea_level = _calc_with_altitude("MA", "Marrakesh", "Morocco", "Africa/Casablanca", 0.0)
    check(
        "altitude-map-differs-sea-level",
        sea_level is not None and pe._result.sunrise != sea_level.sunrise,
        f"{pe._result.sunrise} vs {sea_level.sunrise if sea_level else None}",
    )

    pe.updateSetting("country", "IQ")
    pe.updateSetting("city", "Dahuk")
    pe.updateSetting("method", "Iraq")
    pe.updateSetting("timezone", "Asia/Baghdad")
    pe.updateSetting("custom_coords", False)
    pe.commitSettings()
    pe.recalculate()
    app.processEvents()
    check(
        "altitude-static-dahuk",
        _engine_matches_altitude("IQ", "Dahuk", "Iraq", "Asia/Baghdad", 0.0),
    )
    dahuk_map = _calc_with_altitude("IQ", "Dahuk", "Iraq", "Asia/Baghdad", 570.0)
    check(
        "altitude-static-not-map",
        dahuk_map is not None and pe._result.sunrise != dahuk_map.sunrise,
        f"{pe._result.sunrise} vs {dahuk_map.sunrise if dahuk_map else None}",
    )

    # Restore the shared default for the remaining feature checks.
    pe.updateSetting("country", "TN")
    pe.updateSetting("city", "Tunis")
    pe.updateSetting("method", pe.getCalcMethods()[0]["key"])
    pe.updateSetting("timezone", "Africa/Tunis")
    pe.updateSetting("custom_coords", False)
    pe.commitSettings()
    pe.recalculate()
    app.processEvents()

    # --- Calculation matrix: every method, madhab, offset and timezone ---
    from datetime import date as _matrix_date
    from datetime import timedelta as _timedelta

    _methods = pe.getCalcMethods()
    _matrix_bad = []
    for _m in _methods:
        _r = _calc(
            36.8065,
            10.1815,
            target_date=_matrix_date(2026, 6, 21),
            method_name=_m["key"],
            tz_name="Africa/Tunis",
            city_name="Tunis",
            country_code="TN",
        )
        if _r is None:
            _matrix_bad.append(_m["key"])
            continue
        _vals = list(_r.as_dict().values())
        if not all(a < b for a, b in zip(_vals, _vals[1:])):
            _matrix_bad.append(_m["key"])
    check("methods-36-matrix", len(_methods) == 36 and not _matrix_bad, f"bad={_matrix_bad[:4]}")

    # The same methods at a high-latitude summer date exercise the clamps.
    _high_bad = []
    for _m in _methods:
        _r = _calc(
            51.5074,
            -0.1278,
            target_date=_matrix_date(2026, 6, 21),
            method_name=_m["key"],
            tz_name="Europe/London",
        )
        if _r is None:
            _high_bad.append(_m["key"])
            continue
        _vals = list(_r.as_dict().values())
        if not all(a < b for a, b in zip(_vals, _vals[1:])):
            _high_bad.append(_m["key"])
    check("methods-36-high-lat", not _high_bad, f"bad={_high_bad[:4]}")

    _shafi = _calc(
        36.8065,
        10.1815,
        target_date=_matrix_date(2026, 6, 21),
        method_name=_methods[0]["key"],
        madhab="shafi",
        tz_name="Africa/Tunis",
    ).as_dict()
    _hanafi = _calc(
        36.8065,
        10.1815,
        target_date=_matrix_date(2026, 6, 21),
        method_name=_methods[0]["key"],
        madhab="hanafi",
        tz_name="Africa/Tunis",
    ).as_dict()
    check("madhab-asr", _shafi["asr"] < _hanafi["asr"], f"{_shafi['asr']} vs {_hanafi['asr']}")
    check(
        "madhab-other-prayers",
        all(_shafi[k] == _hanafi[k] for k in ("fajr", "sunrise", "dhuhr", "maghrib", "isha")),
    )

    _base = _calc(
        36.8065,
        10.1815,
        target_date=_matrix_date(2026, 6, 21),
        method_name=_methods[0]["key"],
        tz_name="Africa/Tunis",
    ).as_dict()
    _offset_map = {"fajr": 5, "sunrise": -3, "dhuhr": 2, "asr": -4, "maghrib": 6, "isha": -7}
    _shifted = _calc(
        36.8065,
        10.1815,
        target_date=_matrix_date(2026, 6, 21),
        method_name=_methods[0]["key"],
        tz_name="Africa/Tunis",
        offsets=_offset_map,
    ).as_dict()
    check(
        "offsets-matrix",
        all((_shifted[k] - _base[k]).total_seconds() == _offset_map[k] * 60 for k in _offset_map),
    )

    _utc = _calc(
        36.8065,
        10.1815,
        target_date=_matrix_date(2026, 6, 21),
        method_name=_methods[0]["key"],
        tz_name="UTC",
    ).as_dict()
    check("timezone-matrix", all((_utc[k] - _base[k]) == _timedelta(hours=-1) for k in _base))
    check(
        "target-date",
        _calc(
            36.8065,
            10.1815,
            target_date=_matrix_date(2026, 6, 21),
            method_name=_methods[0]["key"],
            tz_name="Africa/Tunis",
        ).calc_date
        == _matrix_date(2026, 6, 21),
    )

    prov = pe.getAthkarProvider()
    check("adhkar-items-morning", len(prov.getCategoryItems("morning")) == 26)
    it = prov.getCategoryItems("morning")[0]
    check(
        "adhkar-item-shape",
        bool(it.get("arabic")) and it.get("count", 0) >= 1 and bool(it.get("reference_id")),
    )
    check("arabic-numeral", prov.toArabicNumeral(33) == "٣٣")

    pe._athkar_provider.setPrayerAthkar("fajr", "t")
    check("popup-text", len(pe._athkar_provider.getPrayerAthkarText()) > 100)

    # --- Every user-facing option, through the controller ---
    def _settle(seconds=0.3):
        end = _time.time() + seconds
        while _time.time() < end:
            app.processEvents()
            _time.sleep(0.01)

    _baseline = pe._result.as_dict()
    _all_keys = ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")
    for _key in _all_keys:
        pe.setOffset(_key, 7)
        check(
            f"offset-controller-{_key}",
            pe.getOffset(_key) == 7
            and (pe._result.as_dict()[_key] - _baseline[_key]).total_seconds() == 420,
        )
        pe.setOffset(_key, 0)
    check("offset-controller-reset", all(pe.getOffset(k) == 0 for k in _all_keys))

    for _entry in pe.getAzanEnabledList():
        _key = _entry["key"]
        pe.setAzanEnabled(_key, False)
        _state = {e["key"]: e["enabled"] for e in pe.getAzanEnabledList()}
        check(f"azan-toggle-{_key}", _state[_key] is False)
        pe.setAzanEnabled(_key, True)
    check("azan-toggle-reset", all(e["enabled"] for e in pe.getAzanEnabledList()))

    _option_values = {
        "dnd_enabled": False,
        "dnd_from": 21,
        "dnd_to": 5,
        "dnd_duration": 15,
        "fade_in": False,
        "fade_in_duration": 7,
        "takbeer_only": True,
        "sleep_mode": False,
        "show_tray": False,
        "athkar_popup_enabled": False,
        "athkar_popup_duration": 120,
        "athkar_popup_delay": 30,
        "athkarCount": 99,
        "athkarMethod": "specific_time",
        "background_enabled": False,
        "render_backend": "software",
        "render_loop": "basic",
        "window_geometry": [10, 20, 300, 200],
    }
    for _key, _value in _option_values.items():
        pe.updateSetting(_key, _value)
        check(f"option-{_key}", pe.getSetting(_key) == _value)
    pe.commitSettings()
    _settle()
    with open(SETTINGS_FILE, encoding="utf-8") as _f:
        _saved = json.load(_f)
    check("option-persisted", all(_saved.get(k) == v for k, v in _option_values.items()))

    check(
        "timer-awake", pe._clock_timer.interval() == 1000 and pe._prayer_timer.interval() == 60000
    )
    pe.setBackgroundMode(True)
    check(
        "timer-background",
        pe._clock_timer.interval() == 30000 and pe._prayer_timer.interval() == 300000,
    )
    pe.setBackgroundMode(False)
    check(
        "timer-foreground",
        pe._clock_timer.interval() == 1000 and pe._prayer_timer.interval() == 60000,
    )

    _option_defaults = {
        "dnd_enabled": True,
        "dnd_from": 22,
        "dnd_to": 6,
        "dnd_duration": 20,
        "fade_in": True,
        "fade_in_duration": 3,
        "takbeer_only": False,
        "sleep_mode": True,
        "show_tray": True,
        "athkar_popup_enabled": True,
        "athkar_popup_duration": 300,
        "athkar_popup_delay": 60,
        "athkarCount": 33,
        "athkarMethod": "after_prayer",
        "background_enabled": True,
        "render_backend": "auto",
        "render_loop": "auto",
        "window_geometry": [100, 100, 800, 600],
    }
    for _key, _value in _option_defaults.items():
        pe.updateSetting(_key, _value)
    pe.commitSettings()
    _settle()
    check("timer-sleep", pe._prayer_timer.interval() == 300000)

    # Pre-azan alert uses the real notification path with a fabricated next time.
    pe.updateSetting("pre_azan_minutes", 10)
    pe.updateSetting("pre_azan_enabled", True)
    pe.updateSetting("silent_mode", False)
    _real_next = pe._cached_next
    pe._cached_next = ("fajr", pe._now() + _timedelta(minutes=5))
    pe._pre_notified.clear()
    pe._check_pre_azan(pe._now())
    _alert = pe.getPreAlert()
    check("pre-alert-text", bool(_alert) and "10" in _alert, _alert)
    pe.updateSetting("silent_mode", True)
    pe._check_pre_azan(pe._now())
    check("pre-alert-silent", pe.getPreAlert() == "")
    pe.updateSetting("silent_mode", False)
    pe.updateSetting("pre_azan_enabled", False)
    pe._check_pre_azan(pe._now())
    check("pre-alert-disabled", pe.getPreAlert() == "")
    pe.updateSetting("pre_azan_enabled", True)
    pe._cached_next = _real_next
    pe._pre_notified.clear()

    for _fmt, _marker in (("12h", "AM"), ("24h", "")):
        pe.updateSetting("time_format", _fmt)
        app.processEvents()
        _rows = pe.getPrayerTimes()
        if _marker:
            _ok = all(r["time"].endswith(("AM", "PM")) for r in _rows)
        else:
            _ok = all("AM" not in r["time"] and "PM" not in r["time"] for r in _rows)
        check(f"time-format-{_fmt}", bool(_rows) and _ok, _rows[0]["time"] if _rows else "")
    pe.updateSetting("time_format", "24h")
    _settle()

    pe.updateSetting("hijri_day_offset", 0)
    _settle()
    _h0 = pe.getHijriDate()
    pe.updateSetting("hijri_day_offset", 1)
    _settle()
    _h1 = pe.getHijriDate()
    pe.updateSetting("hijri_day_offset", -1)
    _settle()
    _hm = pe.getHijriDate()
    pe.updateSetting("hijri_day_offset", 0)
    _settle()
    check(
        "hijri-offset",
        _h0 != _h1 and _h0 != _hm and _h1 != _hm and pe.getHijriDate() == _h0,
        f"{_h0} / {_h1} / {_hm}",
    )

    _tunis_reference = pe._result.as_dict()
    pe.updateSetting("custom_coords", True)
    pe.updateSetting("latitude", 48.8566)
    pe.updateSetting("longitude", 2.3522)
    pe.updateSetting("timezone", "Europe/Paris")
    _settle()
    _paris = pe._result.as_dict()
    check(
        "custom-coords-applied",
        pe.getSetting("custom_coords") is True
        and abs(pe.getSetting("latitude") - 48.8566) < 1e-6
        and abs(pe.getSetting("longitude") - 2.3522) < 1e-6
        and abs((_paris["fajr"] - _tunis_reference["fajr"]).total_seconds()) > 1800,
    )
    # Unchecking custom coordinates in the UI runs auto-location; emulate its
    # apply step with the known Tunis coordinates.
    _auto_ok = pe._apply_auto_coords("TN", "Tunis", 36.8065, 10.1815, "Africa/Tunis")
    _settle()
    check(
        "custom-coords-restored",
        _auto_ok is True
        and pe.getSetting("custom_coords") is False
        and pe._result.as_dict() == _tunis_reference,
    )

    pe.updateSetting("timezone", "UTC")
    _settle()
    _utc_times = pe._result.as_dict()
    check(
        "timezone-controller",
        all((_utc_times[k] - _tunis_reference[k]).total_seconds() == -3600 for k in _all_keys),
    )
    pe.updateSetting("timezone", "Africa/Tunis")
    _settle()

    pe.updateSetting("volume", 0.42)
    pe.commitSettings()
    _settle()
    _export = pe.exportSettings()
    check(
        "export-settings",
        bool(_export) and _export.startswith(TMP) and os.path.isfile(_export),
        _export,
    )
    with open(_export, encoding="utf-8") as _f:
        _export_json = json.load(_f)
    check(
        "export-content", _export_json.get("volume") == 0.42 and _export_json.get("country") == "TN"
    )

    pe.updateSetting("volume", 0.11)
    pe.updateSetting("country", "IQ")
    pe.updateSetting("city", "Baghdad")
    pe.updateSetting("timezone", "Asia/Baghdad")
    _settle()
    pe.importSettings(_export)
    _settle()
    check(
        "import-settings",
        pe.getSetting("volume") == 0.42
        and pe.getSetting("country") == "TN"
        and pe.getSetting("city") == "Tunis"
        and pe.getSetting("timezone") == "Africa/Tunis",
    )

    _bad_file = os.path.join(TMP, "bad-settings.json")
    with open(_bad_file, "w", encoding="utf-8") as _f:
        json.dump({"volume": 0.5, "evil_key": 1}, _f)
    pe.importSettings(_bad_file)
    _settle()
    check(
        "import-reject-unknown",
        pe.getSetting("volume") == 0.42 and pe.getSetting("country") == "TN",
    )
    with open(_bad_file, "w", encoding="utf-8") as _f:
        json.dump([], _f)
    pe.importSettings(_bad_file)
    _settle()
    check("import-reject-nondict", pe.getSetting("volume") == 0.42)

    pe.updateSetting("volume", 0.05)
    pe.commitSettings()
    _settle()
    pe.storeSettingsSnapshot()
    pe.updateSetting("volume", 0.77)
    pe.updateSetting("method", pe.getCalcMethods()[2]["key"])
    pe.commitSettings()
    _settle()
    pe.restoreSettingsSnapshot()
    _settle()
    check(
        "snapshot-restore",
        pe.getSetting("volume") == 0.05
        and pe.getSetting("method") == pe.getCalcMethods()[0]["key"],
    )

    pe.saveTheme("ottoman_gold")
    _settle()
    with open(SETTINGS_FILE, encoding="utf-8") as _f:
        _saved = json.load(_f)
    check("theme-save", _saved.get("theme") == "ottoman_gold")
    pe.saveTheme("dark")
    _settle()

    _prev_country = pe.getSetting("country")
    _auto_ok = pe._apply_auto_coords("FR", "Paris", 48.8566, 2.3522, "Europe/Paris")
    _settle()
    check(
        "auto-coords-apply",
        _auto_ok is True
        and pe.getSetting("country") == "FR"
        and pe.getSetting("city") == "Paris"
        and pe.getSetting("custom_coords") is False,
    )
    _auto_bad = pe._apply_auto_coords("ZZ", "Nowhere", 0.0, 0.0, None)
    check("auto-coords-reject", _auto_bad is False and pe.getSetting("country") == "FR")
    pe.updateSetting("country", "TN")
    pe.updateSetting("city", "Tunis")
    pe.updateSetting("timezone", "Africa/Tunis")
    _settle()
    check("auto-coords-restored", pe.getSetting("country") == _prev_country)

    _page = pe.searchCitiesPaginated("TN", "tunis", 0, 2)
    check(
        "search-query",
        _page["total"] == 1 and _page["items"][0]["engName"] == "Tunis",
        str(_page["total"]),
    )
    _page_all = pe.searchCitiesPaginated("TN", "", 0, 5)
    _page_next = pe.searchCitiesPaginated("TN", "", 5, 5)
    check(
        "search-paging",
        len(_page_all["items"]) == 5
        and _page_all["total"] > 5
        and bool(_page_next["items"])
        and _page_next["items"][0] != _page_all["items"][0],
    )
    _coords = pe.getCityCoords("TN", "Tunis")
    check(
        "city-coords", abs(_coords["lat"] - 36.8065) < 0.01 and abs(_coords["lon"] - 10.1815) < 0.01
    )
    check("default-method", pe.getDefaultMethod("TN") in {m["key"] for m in pe.getCalcMethods()})
    check("offset-keys", pe.getOffsetKeys() == ["fajr", "dhuhr", "asr", "maghrib", "isha"])
    _tn_cities = pe.getCitiesForCountry("TN")
    check(
        "cities-shape",
        len(_tn_cities) > 5
        and all({"name", "engName", "lat", "lon", "countryCode"} <= set(c) for c in _tn_cities[:5]),
    )
    check("nested-setting", pe.getNestedSetting("offsets.fajr") == 0)
    _all_settings = pe.getSettings()
    check(
        "settings-shape",
        {"country", "city", "method", "offsets", "azan_enabled", "audio"} <= set(_all_settings),
    )

    _tray = pe.getTrayInfo()
    check(
        "tray-info", bool(_tray.get("next")) and isinstance(_tray.get("remaining"), str), str(_tray)
    )
    check("progress", 0.0 <= pe.getProgressToNext() <= 1.0)
    _following = pe.getFollowingPrayers()
    check(
        "following",
        1 <= len(_following) <= 3 and all("name" in f and "time" in f for f in _following),
        str(_following),
    )
    check("credits", bool(pe.getCreditsTitle()) and len(pe.getCreditsHtml()) > 500)
    check("location-text", bool(pe.getLocationText()), pe.getLocationText())
    check(
        "date-texts",
        bool(pe.getClockText()) and bool(pe.getGregorianDate()) and bool(pe.getHijriDate()),
    )
    check("translate", bool(pe.translate("app_name")) and bool(pe.translatePrayer("fajr")))

    from backend.countries_data import COUNTRY_CITIES

    _rows = 0
    _bad_data = []
    for _code, _cities in COUNTRY_CITIES.items():
        if not _cities:
            _bad_data.append(_code)
            continue
        for _name, _lat, _lon in _cities:
            _rows += 1
            if not (-90 <= _lat <= 90 and -180 <= _lon <= 180):
                _bad_data.append(f"{_code}/{_name}")
    check(
        "city-data-complete", _rows == 9681 and not _bad_data, f"rows={_rows} bad={_bad_data[:3]}"
    )

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

    pe.setPrayerAudio("fajr", tmp_mp3)
    check("audio-prayer-assign", pe.getPrayerAudio("fajr") == tmp_mp3)
    pe.setDefaultMuezzin(tmp_mp3)
    check("audio-default-assign", pe.getPrayerAudio("isha") == tmp_mp3)

    from backend.settings import set_autostart

    set_autostart(True)
    ad = os.path.join(os.environ["XDG_CONFIG_HOME"], "autostart", "athan-five-times.desktop")
    check("autostart-on", os.path.isfile(ad))
    set_autostart(False)
    check("autostart-off", not os.path.isfile(ad))

    # --- Hijri calendar events ---
    from datetime import date as _date
    from backend.islamic_events import events_for_date

    ashura = events_for_date(_date(2025, 7, 6))  # 10 Muharram 1447
    check("events-ashura", "عاشوراء" in ashura, str(ashura))
    tarwiya = events_for_date(_date(2026, 5, 25))  # 8 Dhu al-Hijjah 1447
    check("events-tarwiya", "يوم التروية" in tarwiya, str(tarwiya))
    qadr = events_for_date(_date(2026, 3, 10))  # 21 Ramadan 1447
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
        check(
            "reminder-updated-values",
            upd["text"] == "e2e-محدث" and upd["time"] == "06:30" and upd["days"] == [],
        )
        check("reminder-toggle", pe.toggleReminder(rid, False) is True)
        check("reminder-disabled", pe.getReminders()[0]["enabled"] is False)
        check("reminder-remove", pe.removeReminder(rid) is True)
        check("reminder-empty", pe.getReminders() == [])

    # --- Display server detection (Wayland / X11) ---
    from backend.platform_env import platform_is_wayland

    _qpa = pe.getRenderedPlatform()
    _pinfo = pe.getPlatformInfo()
    _expected = os.environ.get("QT_QPA_PLATFORM", "").split(";")[0]
    check(
        "platform-runtime",
        bool(_qpa) and (not _expected or _qpa == _expected),
        f"qpa={_qpa!r} expected={_expected!r}",
    )
    check(
        "platform-info",
        {"session", "platform", "wayland"} <= set(_pinfo)
        and _pinfo["wayland"] is platform_is_wayland(_pinfo["platform"])
        and pe.isWaylandRuntime() is platform_is_wayland(_qpa),
        str(_pinfo),
    )

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
        check(
            "widget-qml-live",
            bool(wob.property("nextName")) or bool(wob.property("countdownText")),
            f"next={wob.property('nextName')}",
        )
        prog = wob.property("progress")
        check("widget-progress", isinstance(prog, float) and 0.0 <= prog <= 1.0, f"progress={prog}")
        foll = wob.property("following")
        check(
            "widget-following",
            isinstance(foll, list)
            and len(foll) >= 1
            and all("name" in f and "time" in f for f in foll),
            f"following={foll}",
        )

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
            anchored = (
                pw > 100
                and abs(wd - pw * 0.5) <= 2.0
                and (abs(x + wd - pw) <= 1.5 if rtl else abs(x) <= 1.5)
            )
            check("widget-progress-anchor", anchored, f"rtl={rtl} x={x} w={wd} trackW={pw}")
        wob.setProperty("visible", False)
        app.processEvents()
        wob.deleteLater()
        app.processEvents()

    # --- Real UI: settings layout, city picker, every language at 460px ---
    def _pump(n=25):
        for _ in range(n):
            app.processEvents()
            _time.sleep(0.008)

    def _walk_all(obj):
        out = []
        seen = set()
        stack = [obj]
        while stack:
            node = stack.pop()
            if id(node) in seen:
                continue
            seen.add(id(node))
            out.append(node)
            stack.extend(node.children())
            if isinstance(node, QQuickItem):
                stack.extend(node.childItems())
        return out

    def _prop(obj, name):
        try:
            return obj.property(name)
        except Exception:
            return None

    def _popup_ids(obj):
        ids = set()
        for node in _walk_all(obj):
            if node.metaObject().className().startswith("Popup_QMLTYPE"):
                ids.update(id(sub) for sub in _walk_all(node))
        return ids

    def _type_text(text, target=None):
        target = target if target is not None else root
        for ch in text:
            for ev in (
                QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, ch),
                QKeyEvent(QEvent.KeyRelease, 0, Qt.NoModifier, ch),
            ):
                QApplication.sendEvent(target, ev)
            _pump(2)

    if dlg is not None:
        root.setProperty("width", 460)
        root.setProperty("height", 680)
        dlg.open()
        _pump(90)

        dw = float(dlg.property("width"))
        dh = float(dlg.property("height"))
        dx = float(dlg.property("x"))
        dy = float(dlg.property("y"))
        check(
            "ui-dialog-fits",
            dw <= 440 and dh <= 660 and dx >= 10 and dy >= 10,
            f"{dw:.0f}x{dh:.0f}@{dx:.0f},{dy:.0f} in 460x680",
        )

        tab_buttons = sorted(
            (
                o
                for o in _walk_all(dlg)
                if str(_prop(o, "objectName") or "").startswith("settingsTab")
                and str(_prop(o, "objectName"))[11:].isdigit()
            ),
            key=lambda o: int(str(_prop(o, "objectName"))[11:]),
        )
        check("ui-tabs-8", len(tab_buttons) == 8, f"got {len(tab_buttons)}")
        tab_texts = []
        for b in tab_buttons:
            lbl = next((c for c in _walk_all(b) if "Label" in c.metaObject().className()), None)
            tab_texts.append(str(_prop(lbl, "text")) if lbl else "")
        check("ui-tabs-labeled", len(tab_texts) == 8 and all(tab_texts), str(tab_texts))

        stack = next(
            (o for o in _walk_all(dlg) if "StackLayout" in o.metaObject().className()), None
        )
        tabs = [c for c in stack.children() if isinstance(c, QQuickItem)] if stack else []
        check("ui-tabs-stack-8", len(tabs) == 8, f"got {len(tabs)}")

        def _layout_issues():
            problems = []
            rw = float(root.property("width"))
            rh = float(root.property("height"))
            w = float(dlg.property("width"))
            h = float(dlg.property("height"))
            px = float(dlg.property("x"))
            py = float(dlg.property("y"))
            if w > rw - 20 or h > rh - 20 or px < 10 or py < 10:
                problems.append(f"dialog {w:.0f}x{h:.0f}@{px:.0f},{py:.0f} in {rw:.0f}x{rh:.0f}")
            for b in tab_buttons:
                lbl = next((c for c in _walk_all(b) if "Label" in c.metaObject().className()), None)
                if lbl and float(lbl.implicitWidth()) > lbl.width() + 1:
                    problems.append(f"tab label {_prop(lbl, 'text')!r} elided")
            live_popups = _popup_ids(dlg)
            for idx in range(len(tabs)):
                dlg.setProperty("currentTabIndex", idx)
                _pump(28)
                tab = next((c for c in tabs if c.isVisible()), None)
                if tab is None:
                    problems.append(f"tab{idx} not visible")
                    continue
                tw = float(tab.width())
                if tw <= 0:
                    problems.append(f"tab{idx} zero width")
                    continue
                for o in _walk_all(tab):
                    if id(o) in live_popups or not isinstance(o, QQuickItem) or not o.isVisible():
                        continue
                    ow = float(o.width())
                    oh = float(o.height())
                    if ow <= 0 and oh <= 0:
                        continue
                    cn = o.metaObject().className()
                    x = float(o.mapToItem(tab, 0, 0).x())
                    if (
                        (x < -2 or x + ow > tw + 2)
                        and "ScrollBar" not in cn
                        and "ScrollIndicator" not in cn
                    ):
                        problems.append(f"tab{idx} overflow {cn} w={ow:.0f} tabW={tw:.0f}")
                    if "Label" in cn or cn == "QQuickText":
                        text = _prop(o, "text")
                        cw = _prop(o, "contentWidth")
                        ch = _prop(o, "contentHeight")
                        if text and cw is not None and float(cw) > ow + 1.5:
                            problems.append(
                                f"tab{idx} text {str(text)[:28]!r} "
                                f"content={float(cw):.0f} w={ow:.0f}"
                            )
                        if text and ch is not None and float(ch) > oh + 1.5:
                            problems.append(
                                f"tab{idx} clipped {str(text)[:28]!r} "
                                f"contentH={float(ch):.0f} h={oh:.0f}"
                            )
            return problems

        _ar_probs = _layout_issues()
        check("ui-layout-ar-460", not _ar_probs, "; ".join(_ar_probs[:3]))

        # --- city picker: switch country through the real ComboBox ---
        dlg.setProperty("currentTabIndex", 0)
        _pump(20)
        picker = next((o for o in _walk_all(dlg) if _prop(o, "objectName") == "cityPicker"), None)
        check("ui-city-picker-found", picker is not None)

        def _find_ui(name):
            return next((o for o in _walk_all(dlg) if _prop(o, "objectName") == name), None)

        country_combo = _find_ui("countryCombo")
        method_combo = _find_ui("methodCombo")
        check(
            "ui-combos-found",
            all(x is not None for x in (country_combo, method_combo)),
            f"country={country_combo is not None} method={method_combo is not None}",
        )

        def _select_country(code):
            model = country_combo.property("model") or []
            for i, item in enumerate(model):
                if item.get("code") == code:
                    country_combo.setProperty("currentIndex", i)
                    _pump(90)
                    return True
            return False

        if picker is not None and country_combo is not None:
            save_btn = _find_ui("settingsSaveButton")

            check("ui-country-select-sa", _select_country("SA"))
            st = pe.getSettings()
            check(
                "ui-country-sa-consistent",
                st.get("city") == "Mecca" and st.get("timezone") == "Asia/Riyadh",
                f"{st.get('city')}/{st.get('timezone')}",
            )
            check("ui-country-select-tn", _select_country("TN"))
            st = pe.getSettings()
            check(
                "ui-country-tn-consistent",
                st.get("city") == "Tunis"
                and st.get("timezone") == "Africa/Tunis"
                and abs(st.get("latitude", 0) - 36.8065) < 0.01,
                f"{st.get('city')}/{st.get('timezone')}/{st.get('latitude')}",
            )
            check(
                "ui-picker-sync",
                _prop(picker, "countryCode") == "TN"
                and _prop(picker, "selectedEngName") == "Tunis",
            )

            popup = next(
                (o for o in _walk_all(picker) if _prop(o, "objectName") == "cityPopup"), None
            )
            city_list = next(
                (o for o in _walk_all(popup) if _prop(o, "objectName") == "cityListView"), None
            )
            from PySide6.QtCore import QMetaObject

            QMetaObject.invokeMethod(popup, "open")
            _pump(60)
            tn_cities = pe.getCityNamesForCountry("TN")
            check(
                "ui-city-popup-all",
                city_list.property("count") == len(tn_cities) and popup.property("height") >= 56,
                f"count={city_list.property('count')} h={popup.property('height'):.0f}",
            )

            field = next(
                o for o in _walk_all(picker) if _prop(o, "objectName") == "citySearchField"
            )
            field.forceActiveFocus()
            _pump(8)
            QMetaObject.invokeMethod(field, "selectAll")
            _type_text("Sfax", field)
            _pump(90)
            check(
                "ui-city-filter",
                city_list.property("count") == 1,
                f"count={city_list.property('count')}",
            )

            rows = [
                o
                for o in _walk_all(popup)
                if isinstance(o, QQuickItem)
                and 20 <= float(_prop(o, "height") or 0) <= 46
                and float(_prop(o, "width") or 0) > 100
                and o.isVisible()
            ]
            check("ui-city-row-visible", bool(rows), f"rows={len(rows)}")
            if rows:
                center = rows[0].mapToItem(None, rows[0].width() / 2, rows[0].height() / 2)
                QTest.mouseClick(
                    root, Qt.LeftButton, Qt.NoModifier, QPoint(int(center.x()), int(center.y()))
                )
                _pump(110)
                coords = pe.getCityCoords("TN", "Sfax")
                st = pe.getSettings()
                check(
                    "ui-city-click-sfax",
                    _prop(picker, "selectedEngName") == "Sfax"
                    and st.get("city") == "Sfax"
                    and abs(st.get("latitude", 0) - coords["lat"]) < 0.01
                    and abs(st.get("longitude", 0) - coords["lon"]) < 0.01,
                    f"{st.get('city')}/{st.get('latitude'):.3f},{st.get('longitude'):.3f}",
                )
                check("ui-city-popup-closed", not popup.property("opened"))

            field.forceActiveFocus()
            _pump(8)
            QMetaObject.invokeMethod(field, "selectAll")
            _type_text("zzzzzz", field)
            _pump(90)
            empty = next(
                (o for o in _walk_all(popup) if _prop(o, "objectName") == "cityEmptyLabel"), None
            )
            check(
                "ui-city-empty-state",
                city_list.property("count") == 0
                and popup.property("height") >= 56
                and empty is not None
                and empty.isVisible(),
                f"count={city_list.property('count')} h={popup.property('height'):.0f}",
            )
            QMetaObject.invokeMethod(popup, "close")
            _pump(25)

            # --- live language switch keeps values in sync ---
            def _combo_method_label():
                try:
                    idx = int(method_combo.property("currentIndex"))
                    methods = pe.getCalcMethods()
                    if 0 <= idx < len(methods):
                        return methods[idx]["display"]
                except Exception:
                    pass
                return ""

            check(
                "ui-lang-country-ar",
                str(_prop(country_combo, "editText")) == "تونس",
                str(_prop(country_combo, "editText")),
            )
            check(
                "ui-lang-method-ar",
                str(_prop(method_combo, "displayText")) == _combo_method_label(),
                str(_prop(method_combo, "displayText")),
            )
            lo.setLanguage("en")
            _pump(70)
            check(
                "ui-lang-switch-country",
                str(_prop(country_combo, "editText")) == "Tunisia",
                str(_prop(country_combo, "editText")),
            )
            check(
                "ui-lang-switch-method",
                str(_prop(method_combo, "displayText")) == _combo_method_label(),
                str(_prop(method_combo, "displayText")),
            )
            check(
                "ui-lang-switch-title",
                dlg.property("title") == "Settings",
                str(dlg.property("title")),
            )
            if save_btn is not None:
                check(
                    "ui-lang-switch-save",
                    str(_prop(save_btn, "text")) == "Save",
                    str(_prop(save_btn, "text")),
                )
            check(
                "ui-lang-switch-city",
                _prop(picker, "selectedEngName") == "Sfax",
                str(_prop(picker, "selectedEngName")),
            )
            lo.setLanguage("ar")
            _pump(60)

        # --- every shipped language, every tab, narrowest window ---
        from backend._constants import LANGS as _UI_LANGS

        for lang in _UI_LANGS:
            lo.setLanguage(lang)
            _pump(30)
            probs = _layout_issues()
            check(f"ui-lang-{lang}", not probs, "; ".join(probs[:3]))

        # --- other real window sizes with the longest labels ---
        for _w, _h in ((500, 840), (800, 900)):
            root.setProperty("width", _w)
            root.setProperty("height", _h)
            _pump(45)
            for lang in ("ar", "en", "ru", "ur", "pa", "ps"):
                lo.setLanguage(lang)
                _pump(25)
                probs = _layout_issues()
                check(f"ui-size-{_w}-{lang}", not probs, "; ".join(probs[:3]))

        lo.setLanguage("ar")
        pe.updateSetting("language", "ar")
        pe.commitSettings()
        _pump(45)
        dlg.setProperty("currentTabIndex", 0)
        _pump(15)
        dlg.close()
        _pump(20)

    # --- Full reset returns the app to first-run defaults ---
    pe.resetAllSettings()
    _settle()
    check(
        "reset-defaults",
        pe.getSetting("country") == "SA"
        and pe.getSetting("city") == "Mecca"
        and pe.getSetting("volume") == 1.0
        and pe.getSetting("theme") == "dark"
        and all(v == 0 for v in pe.getSetting("offsets").values()),
    )
    check("reset-recalculates", len(pe.getPrayerTimes()) == 6)

    import glob as _g

    check(
        "prayer-icons-14", len(_g.glob(os.path.join(ROOT, "assets", "prayer_icons", "*.png"))) == 14
    )
    import json as _json

    with open(os.path.join(ROOT, "assets", "adhkar", "index.json"), encoding="utf-8") as _f:
        _idx = _json.load(_f)
    _cats = _idx.get("categories", _idx)
    _missing = [
        c.get("icon")
        for c in _cats
        if not os.path.isfile(
            os.path.join(ROOT, "assets", "adhkar_icons", str(c.get("icon")) + ".png")
        )
    ]
    check(
        "adhkar-icons-complete",
        len(_cats) == 23 and not _missing,
        f"categories={len(_cats)} missing={_missing}",
    )

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
    print(f"\nE2E: {len(results) - len(fails)}/{len(results)} passed, {len(qml_errors)} qml errors")
    return 1 if (fails or qml_errors) else 0


if __name__ == "__main__":
    sys.exit(main())
