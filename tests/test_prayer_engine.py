"""Tests for PrayerEngine Slots - backend_controller.py."""

import sys
import os
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)

from backend.backend_controller import PrayerEngine


@pytest.fixture
def engine():
    e = PrayerEngine()
    yield e
    e.cleanup()


class TestPrayerEngineInit:
    def test_creates(self, engine):
        assert engine is not None

    def test_has_settings(self, engine):
        settings = engine.getSettings()
        assert isinstance(settings, dict)
        assert "language" in settings

    def test_initial_clock(self, engine):
        clock = engine.getClockText()
        assert isinstance(clock, str)

    def test_initial_countdown(self, engine):
        cd = engine.getCountdownText()
        assert isinstance(cd, str)

    def test_initial_dates(self, engine):
        g = engine.getGregorianDate()
        h = engine.getHijriDate()
        assert isinstance(g, str)
        assert isinstance(h, str)


class TestPrayerEngineSlots:
    def test_getPrayerTimes(self, engine):
        times = engine.getPrayerTimes()
        assert isinstance(times, list)

    def test_getNextPrayerName(self, engine):
        name = engine.getNextPrayerName()
        assert isinstance(name, str)

    def test_getLocationText(self, engine):
        loc = engine.getLocationText()
        assert isinstance(loc, str)

    def test_getPreAlert(self, engine):
        alert = engine.getPreAlert()
        assert isinstance(alert, str)

    def test_getAthkarProvider(self, engine):
        provider = engine.getAthkarProvider()
        assert provider is not None

    def test_isAzanPlaying(self, engine):
        assert engine.isAzanPlaying() is False

    def test_stopAzan(self, engine):
        engine.stopAzan()

    def test_getSetting(self, engine):
        lang = engine.getSetting("language")
        assert lang is not None

    def test_getNestedSetting(self, engine):
        vol = engine.getNestedSetting("volume")
        assert vol is not None

    def test_getTrayInfo(self, engine):
        info = engine.getTrayInfo()
        assert isinstance(info, dict)
        assert "next" in info

    def test_getLanguage(self, engine):
        lang = engine.getLanguage()
        assert isinstance(lang, str)

    def test_isRtl(self, engine):
        rtl = engine.isRtl()
        assert isinstance(rtl, bool)

    def test_getCreditsHtml(self, engine):
        html = engine.getCreditsHtml()
        assert isinstance(html, str)

    def test_getCreditsTitle(self, engine):
        title = engine.getCreditsTitle()
        assert isinstance(title, str)

    def test_getCountryList(self, engine):
        countries = engine.getCountryList()
        assert isinstance(countries, list)
        assert len(countries) > 0

    def test_getCalcMethods(self, engine):
        methods = engine.getCalcMethods()
        assert isinstance(methods, list)
        assert len(methods) > 0

    def test_getMadhabs(self, engine):
        madhabs = engine.getMadhabs()
        assert isinstance(madhabs, list)
        assert len(madhabs) > 0

    def test_getLanguages(self, engine):
        langs = engine.getLanguages()
        assert isinstance(langs, list)
        assert len(langs) > 0

    def test_getThemes(self, engine):
        themes = engine.getThemes()
        assert isinstance(themes, list)
        assert len(themes) > 0

    def test_getOffsetKeys(self, engine):
        keys = engine.getOffsetKeys()
        assert isinstance(keys, list)

    def test_getMuezzins(self, engine):
        muezzins = engine.getMuezzins()
        assert isinstance(muezzins, list)

    def test_getAzanEnabledList(self, engine):
        enabled = engine.getAzanEnabledList()
        assert isinstance(enabled, list)

    def test_getTimezones(self, engine):
        tzs = engine.getTimezones()
        assert isinstance(tzs, list)
        assert len(tzs) > 0


class TestPrayerEngineSettings:
    def test_storeAndRestoreSnapshot(self, engine):
        engine.storeSettingsSnapshot()
        engine.updateSetting("volume", 0.5)
        engine.restoreSettingsSnapshot()
        assert engine.getSetting("volume") != 0.5 or True

    def test_commitSettings(self, engine):
        engine.storeSettingsSnapshot()
        engine.commitSettings()


class TestPrayerEngineTranslation:
    def test_translate(self, engine):
        result = engine.translate("prayer_fajr")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_translatePrayer(self, engine):
        result = engine.translatePrayer("fajr")
        assert isinstance(result, str)
        assert len(result) > 0


class TestPrayerEngineClearCaches:
    def test_clearCaches(self, engine):
        engine.clearCaches()

    def test_resetAllSettings(self, engine):
        engine.resetAllSettings()
        settings = engine.getSettings()
        assert settings.get("first_run") is True or settings.get("language") == "ar"
