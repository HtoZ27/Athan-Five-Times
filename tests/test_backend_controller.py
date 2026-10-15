import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)

from backend.backend_controller import PrayerEngine, _ensure_country_data
from backend.i18n import set_lang


def _engine_with_muezzins(muezzins):
    e = PrayerEngine()
    e._settings = dict(e._settings)
    e._settings["muezzins"] = dict(muezzins)
    e._settings["removed_muezzins"] = []
    return e


class TestMuezzinManagement:
    def test_remove_default_by_translated_name(self):
        # NOTE: set_lang AFTER engine creation — the engine applies the
        # stored UI language on init, like the real application does.
        e = _engine_with_muezzins({"افتراضي": "/tmp/x.mp3"})
        set_lang("en")
        try:
            e.removeMuezzin("Default")
            assert "افتراضي" not in e._settings["muezzins"]
            assert "افتراضي" in e._settings["removed_muezzins"]
            e.cleanup()
        finally:
            set_lang("ar")

    def test_edit_muezzin_leaves_no_duplicate(self):
        e = _engine_with_muezzins({"Old": "/a.mp3"})
        e.addMuezzin("New", "/b.mp3")
        e.removeMuezzin("Old")
        assert list(e._settings["muezzins"]) == ["New"]
        e.cleanup()

    def test_readding_builtin_clears_removed_flag(self):
        e = _engine_with_muezzins({})
        e._settings["removed_muezzins"] = ["قطامي"]
        e.addMuezzin("قطامي", "/x.mp3")
        assert e._settings["removed_muezzins"] == []
        e.cleanup()

    def test_removed_builtin_stays_removed_after_reload(self):
        import backend.settings as S

        s = S.load()
        s["removed_muezzins"] = ["قطامي", "افتراضي"]
        assert S.save(s)
        S.invalidate_cache()
        s2 = S.load()
        assert "قطامي" not in s2["muezzins"]
        assert "افتراضي" not in s2["muezzins"]

    def test_migration_v3_to_v4_adds_removed_muezzins(self):
        import backend.settings as S

        migrated = S._run_migrations({"schema_version": 3, "language": "ar"})
        assert migrated["schema_version"] == S.SETTINGS_VERSION
        assert migrated["removed_muezzins"] == []


class TestAutoLocationStatus:
    def test_reset_emits_detecting(self):
        from unittest.mock import patch

        e = PrayerEngine()
        try:
            seen = []
            e.autoLocationStatus.connect(seen.append)
            with patch("backend.location.detect_async") as d:
                e.resetToAutoCoordinates()
            assert seen == ["detecting"]
            assert d.called
        finally:
            e.cleanup()

    def test_process_success_emits_success(self):
        e = PrayerEngine()
        try:
            seen = []
            e.autoLocationStatus.connect(seen.append)
            e._pending_location = {
                "country_code": "SA",
                "city": "Mecca",
                "latitude": 21.42,
                "longitude": 39.82,
                "timezone": "Asia/Riyadh",
            }
            e._process_auto_location()
            assert seen == ["success"]
            assert e.getSetting("city") == "Mecca"
        finally:
            e.cleanup()

    def test_process_none_emits_failed(self):
        e = PrayerEngine()
        try:
            seen = []
            e.autoLocationStatus.connect(seen.append)
            e._pending_location = None
            e._process_auto_location()
            assert seen == ["failed"]
        finally:
            e.cleanup()


class TestDndSerialization:
    def test_run_dnd_cmds_executes_all_backends(self):
        from unittest.mock import patch

        e = PrayerEngine()
        try:
            seen = []
            with patch("subprocess.run", side_effect=lambda cmd, **kw: seen.append(cmd)):
                e._run_dnd_cmds(True)
            assert seen[0][0] == "dunstctl"
            assert any(c[0] == "gsettings" for c in seen)
            assert any(c[0] == "swaync-client" for c in seen)
            assert len(seen) == 9
        finally:
            e.cleanup()


class TestEnsureCountryData:
    def test_loads_tuple(self):
        result = _ensure_country_data()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_contains_methods(self):
        methods, countries, cities = _ensure_country_data()
        assert isinstance(methods, dict)
        assert "TN" in methods

    def test_contains_countries(self):
        _, countries, _ = _ensure_country_data()
        assert isinstance(countries, dict)
        assert "TN" in countries
        assert "US" in countries

    def test_contains_cities(self):
        _, _, cities = _ensure_country_data()
        assert isinstance(cities, dict)
        assert "TN" in cities
        assert len(cities["TN"]) > 0
        assert isinstance(cities["TN"][0], tuple)
        assert len(cities["TN"][0]) == 3
