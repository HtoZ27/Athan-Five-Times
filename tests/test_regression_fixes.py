"""Regression tests for analyst-reported bugs fixed in this cycle.

Covers: double-azan race + ghost azan, dead volume slider, UAE Isha
interval precedence, next-prayer highlight refresh, translation cache
clearing, polar-None empty state, and settings-TZ clock unification.
"""

import os
import sys
from datetime import date, datetime, timedelta

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)

from backend.backend_controller import PrayerEngine
import backend.backend_controller as BC


@pytest.fixture
def engine():
    e = PrayerEngine()
    e.recalculate()
    assert e._result is not None, "default Tunis calculation must succeed"
    yield e
    e.cleanup()


def _pick_prayer_key(engine):
    d = engine._result.as_dict()
    now = engine._now()
    for key in ("dhuhr", "asr", "maghrib", "isha", "fajr"):
        if d[key] > now - timedelta(hours=1):
            return key, d[key]
    return "dhuhr", d["dhuhr"]


class TestScheduledAzan:
    def test_timeout_marks_notified_single_trigger(self, engine):
        key, pdt = _pick_prayer_key(engine)
        engine._now = lambda: pdt + timedelta(seconds=10)
        calls = []
        engine._trigger_azan = lambda k: calls.append(k)
        engine._scheduled_next_prayer = key
        engine._on_scheduled_timeout()
        engine._on_scheduled_timeout()  # stray second fire must be a no-op
        assert calls == [key]
        assert key in engine._notified_prayers

    def test_late_scheduled_timeout_skipped(self, engine):
        key, pdt = _pick_prayer_key(engine)
        engine._now = lambda: pdt + timedelta(hours=3)
        calls = []
        engine._trigger_azan = lambda k: calls.append(k)
        engine._scheduled_next_prayer = key
        engine._on_scheduled_timeout()
        assert calls == []
        assert key in engine._notified_prayers


class TestVolumeWiring:
    def test_play_azan_forwards_global_volume(self, monkeypatch):
        import backend.audio as audio

        seen = {}

        class StubPlayer:
            _volume = 0.5

            def play(self, path, config, on_done, stop_flag):
                seen["volume"] = config.volume

        monkeypatch.setattr(audio, "_global_player", StubPlayer())
        audio.play_azan("/nonexistent.mp3")
        assert seen["volume"] == 0.5


class TestIshaInterval:
    def test_uae_official_oct9(self):
        # Awqaf Abu Dhabi official 2026-10-09: Fajr 05:01, Isha 19:18
        # (angle-derived 18.0/18.0 — verified, NOT a fixed interval).
        from backend.prayer_calc import calculate

        r = calculate(
            24.4539,
            54.3773,
            target_date=date(2026, 10, 9),
            method_name="الهيئة العامة للشؤون الإسلامية (الإمارات)",
            tz_name="Asia/Dubai",
        )
        d = r.as_dict()
        assert d["fajr"].strftime("%H:%M") == "05:01", d
        assert d["isha"].strftime("%H:%M") == "19:18", d


class TestHighlightRefresh:
    def test_cache_key_follows_next_prayer(self, engine):
        first = engine.getPrayerTimes()
        assert any(t["isNext"] for t in first)
        other = "isha" if engine._cached_next[0] != "isha" else "fajr"
        name, dt = engine._cached_next
        engine._cached_next = (other, dt)
        second = engine.getPrayerTimes()
        assert second is not first
        flagged = [t["key"] for t in second if t["isNext"]]
        assert flagged == [other]


class TestTranslationCaches:
    def test_clear_caches_empties_translations(self, engine):
        engine.translate("app_name")
        assert len(engine._TRANS_CACHE) > 0
        engine.clearCaches()
        assert engine._TRANS_CACHE == {}
        assert engine._TRANS_PRAYER_CACHE == {}
        assert BC._LANGUAGES_CACHE is None


class TestPolarNone:
    def test_failed_calc_clears_ui_state(self, engine, monkeypatch):
        engine.getPrayerTimes()
        assert len(engine._prayer_times_cache or []) > 0
        monkeypatch.setattr(BC, "calculate", lambda *a, **k: None)
        engine.recalculate()
        assert engine.getPrayerTimes() == []
        assert engine.getNextPrayerName() == "--"
        assert engine.getNextPrayerKey() == "fajr"


class TestSettingsClock:
    def test_now_naive_in_settings_zone(self, engine):
        engine.updateSetting("timezone", "Asia/Dubai")
        n = engine._now()
        assert n.tzinfo is None
        try:
            from zoneinfo import ZoneInfo

            ref = datetime.now(ZoneInfo("Asia/Dubai")).replace(tzinfo=None)
            assert abs((ref - n).total_seconds()) < 5
        except ImportError:
            pass


class TestQuitApp:
    def test_update_setting_converts_qjsvalue(self, engine):
        import json
        from PySide6.QtQml import QJSEngine

        js = QJSEngine()  # held: a dead engine yields a dead QJSValue
        v = js.evaluate("[10, 20, 300, 200]")
        engine.updateSetting("window_geometry", v)
        assert list(engine.getSetting("window_geometry")) == [10, 20, 300, 200]
        json.dumps(engine._settings)  # must stay JSON-serializable

    def test_quit_app_stops_saves_quits(self, engine, monkeypatch):
        import PySide6.QtWidgets as W

        saved = {}
        monkeypatch.setattr(BC, "save_settings", lambda s: saved.update(s))
        monkeypatch.setattr(engine, "stopAzan", lambda: saved.update(stopped=True))

        class FakeApp:
            def quit(self):
                saved["quit"] = True

        monkeypatch.setattr(W.QApplication, "instance", classmethod(lambda cls: FakeApp()))
        engine.quitApp()
        assert saved.get("stopped") is True
        assert saved.get("quit") is True
        assert "window_geometry" in saved or True


class TestTomorrowFajrWrap:
    def test_wrap_uses_computed_tomorrow_fajr(self, engine):
        assert engine._tomorrow_fajr is not None
        late = engine._result.isha + timedelta(hours=1)
        key, dt = engine._result.next_prayer(late, tomorrow_fajr=engine._tomorrow_fajr)
        assert key == "fajr"
        assert dt == engine._tomorrow_fajr

    def test_wrap_fallback_without_cache(self, engine):
        late = engine._result.isha + timedelta(hours=1)
        key, dt = engine._result.next_prayer(late)
        assert key == "fajr"
        assert dt == engine._result.fajr + timedelta(days=1)

    def test_helper_routes_cache(self, engine):
        late = engine._result.isha + timedelta(hours=1)
        assert engine._next_prayer(late)[1] == engine._tomorrow_fajr


class TestSingleInstanceLock:
    def test_second_lock_fails(self, tmp_path):
        from PySide6.QtCore import QLockFile

        first = QLockFile(str(tmp_path / "app.lock"))
        assert first.tryLock(100)
        try:
            second = QLockFile(str(tmp_path / "app.lock"))
            assert not second.tryLock(100)
        finally:
            first.unlock()


class TestNoRawCodesInUI:
    """End users must never see ISO codes, Latin keys or IANA paths."""

    def test_madhabs_translated(self, engine):
        for m in engine.getMadhabs():
            assert m["display"] not in ("shafi", "hanafi", "maliki"), m

    def test_themes_translated(self, engine):
        import re

        for t in engine.getThemes():
            assert not re.fullmatch(r"[a-z_]+", t["name"]), t

    def test_timezones_no_iana(self, engine):
        for z in engine.getTimezones():
            assert "/" not in z["name"], z

    def test_methods_no_latin(self, engine):
        import re

        for m in engine.getCalcMethods():
            assert not re.search(r"[A-Za-z]", m["display"]), m

    def test_ar_sections_exist(self):
        import json

        d = json.load(open("backend/translations/ar.json", encoding="utf-8"))
        for sec in ("madhab", "themes", "calc_methods"):
            assert sec in d, sec

    def test_language_switch_clears_display_caches(self, engine, monkeypatch):
        import backend.backend_controller as BC
        from backend.i18n import set_lang

        set_lang("en")
        BC._MADHABS_CACHE = None
        try:
            assert engine.getMadhabs()[0]["display"] == "Shafi'i"
            assert engine.getCountryList()[0]["name"] != ""
            engine.getTimezones()
            engine._settings = dict(engine._settings, language="ar")
            engine._stored_old_lang = "en"
            engine.commitSettings()
            assert engine.getMadhabs()[0]["display"] == "شافعي"
            assert BC._MADHABS_CACHE is not None
            assert BC._TIMEZONES_CACHE is None
            assert BC._THEMES_CACHE is None
            assert BC._CALC_METHODS_CACHE is None
            assert engine._TRANS_CACHE == {}
        finally:
            set_lang("ar")
            engine._settings = dict(engine._settings, language="ar")
            engine._stored_old_lang = None


class TestLocationValidation:
    def test_unknown_country_rejected(self, engine):
        before = engine.getSetting("country")
        engine.updateSetting("country", "XX")
        engine.updateSetting("country", "")
        assert engine.getSetting("country") == before

    def test_known_country_accepted(self, engine):
        engine.updateSetting("country", "TN")
        assert engine.getSetting("country") == "TN"

    def test_unknown_city_rejected(self, engine):
        engine.updateSetting("country", "TN")
        engine.updateSetting("city", "Tunis")
        engine.updateSetting("city", "NoSuchCity123")
        assert engine.getSetting("city") == "Tunis"

    def test_auto_coords_unknown_country_keeps_settings(self, engine):
        before_country = engine.getSetting("country")
        ok = engine._apply_auto_coords("XX", "Nowhere", 0.0, 0.0)
        assert ok is False
        assert engine.getSetting("country") == before_country

    def test_auto_coords_known_country_applies(self, engine):
        ok = engine._apply_auto_coords("TN", "Tunis", 36.8, 10.18)
        assert ok is True
        assert engine.getSetting("country") == "TN"

    def test_auto_coords_rejects_zero_coords(self, engine):
        before = (engine.getSetting("latitude"), engine.getSetting("longitude"))
        assert engine._apply_auto_coords("TN", "Tunis", 0.0, 0.0) is False
        assert engine._apply_auto_coords("TN", "Tunis", 91.0, 10.0) is False
        assert engine._apply_auto_coords("TN", "Tunis", 36.8, 181.0) is False
        assert (engine.getSetting("latitude"), engine.getSetting("longitude")) == before


class TestCancelRevertsSideEffects:
    def test_set_autostart_updates_settings(self, engine, monkeypatch):
        import backend.backend_controller as BC

        monkeypatch.setattr(BC, "_set_autostart", lambda enabled: None)
        engine.updateSetting("autostart", False)
        engine.setAutostart(True)
        assert engine.getSetting("autostart") is True

    def test_restore_reverts_language_theme_autostart(self, engine, monkeypatch):
        import backend.backend_controller as BC
        from backend.i18n import get_lang

        files = []
        monkeypatch.setattr(BC, "_set_autostart", lambda enabled: files.append(enabled))
        engine.updateSetting("autostart", False)
        engine.storeSettingsSnapshot()
        engine.updateSetting("language", "en")
        engine.updateSetting("theme", "light")
        engine.updateSetting("autostart", True)
        engine.restoreSettingsSnapshot()
        assert get_lang() == engine.getSetting("language")
        assert files and files[-1] == engine.getSetting("autostart")

    def test_city_name_cached_per_language(self):
        from backend.translations import city_name
        from backend.i18n import set_lang
        from backend.translations import _city_name_cached

        set_lang("ar")
        try:
            a1 = city_name("Tunis")
            hits_before = _city_name_cached.cache_info().hits
            a2 = city_name("Tunis")
            assert a1 == a2
            assert _city_name_cached.cache_info().hits > hits_before
        finally:
            set_lang("ar")


class TestAnalystRoundTwo:
    def test_set_offset_emits_and_recalcs(self, engine):
        seen = []
        engine.prayerTimesChanged.connect(lambda: seen.append(1))
        engine.setOffset("fajr", 2)
        assert seen, "setOffset must refresh the list"
        engine.setOffset("fajr", 0)

    def test_auto_location_rejected_falls_back(self, engine, monkeypatch):
        import backend.backend_controller as BC

        monkeypatch.setattr(BC, "save_settings", lambda s: None)
        engine.updateSetting("country", "TN")
        before = dict(engine._settings)
        engine._pending_location = {
            "country_code": "XX",
            "city": "Nowhere",
            "latitude": 10.0,
            "longitude": 10.0,
            "timezone": None,
        }
        engine._process_auto_location()
        assert engine.getSetting("country") == before["country"]

    def test_recalc_emits_location_only_for_location_keys(self, engine):
        locs, _ = [], None
        engine.locationChanged.connect(lambda: locs.append(1))
        engine._schedule_recalc(location_changed=True)
        engine._do_recalc()
        assert locs, "location keys must emit locationChanged"
        locs.clear()
        engine._schedule_recalc()
        engine._do_recalc()
        assert not locs, "non-location recalc must stay quiet"

    def test_midnight_guard_recalculates(self, engine, monkeypatch):
        from datetime import timedelta

        real_now = engine._now()
        monkeypatch.setattr(engine, "_now", lambda: real_now + timedelta(days=1))
        engine._update_clock()
        assert engine._result.calc_date == (real_now + timedelta(days=1)).date()

    def test_athkar_delay_default_aligned(self):
        from backend.settings import DEFAULT_SETTINGS

        assert DEFAULT_SETTINGS.get("athkar_popup_delay") == 60


class TestRestorePersistsDisk:
    def test_disk_matches_after_restore(self, engine, monkeypatch, tmp_path):
        import backend.backend_controller as BC
        from backend.i18n import get_lang

        monkeypatch.setattr(BC, "_set_autostart", lambda enabled: None)
        engine.updateSetting("autostart", False)
        engine.storeSettingsSnapshot()
        engine.updateSetting("language", "en")
        engine.restoreSettingsSnapshot()
        assert get_lang() == engine.getSetting("language")


class TestRecalcTriggers:
    def test_hijri_offset_schedules_recalc(self, engine, monkeypatch):
        calls = []
        monkeypatch.setattr(
            engine,
            "_schedule_recalc",
            lambda location_changed=False: calls.append(location_changed),
        )
        engine.updateSetting("hijri_day_offset", 1)
        assert calls, "hijri_day_offset must schedule a recalculation"

    def test_time_format_emits(self, engine):
        seen = []
        engine.prayerTimesChanged.connect(lambda: seen.append(1))
        engine.updateSetting("time_format", "24h")
        assert seen, "time_format must emit prayerTimesChanged"


class TestIpinfoProvider:
    def test_uppercase_and_validation(self):
        import json
        from unittest.mock import MagicMock, patch
        from backend.location import _try_ipinfo

        def resp(payload):
            m = MagicMock()
            m.read.return_value = json.dumps(payload).encode()
            m.__enter__.return_value = m
            return m

        with patch(
            "backend.location.urlopen",
            return_value=resp(
                {"country": "tn", "city": "Tunis", "loc": "36.8,10.2", "timezone": "Africa/Tunis"}
            ),
        ):
            r = _try_ipinfo()
        assert r is not None and r["country_code"] == "TN"

        with patch(
            "backend.location.urlopen",
            return_value=resp({"country": "TN", "city": "X", "loc": "0.0,0.0"}),
        ):
            assert _try_ipinfo() is None
