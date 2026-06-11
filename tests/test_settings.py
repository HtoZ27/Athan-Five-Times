import os
import tempfile
from copy import deepcopy

import pytest

from backend.settings import (
    resolve_azan_path, load, save, set_autostart, SETTINGS_VERSION,
    validate_and_coerce, _run_migrations, MIGRATIONS, SettingsSchema,
    schema_to_dict,
)


class TestResolveAzanPath:
    def test_empty_path_returns_empty(self):
        assert resolve_azan_path("") == ""

    def test_existing_file_returns_as_is(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"dummy")
            tmp = f.name
        try:
            result = resolve_azan_path(tmp)
            assert result == tmp
        finally:
            os.unlink(tmp)

    def test_nonexistent_falls_back_to_first_muezzin(self):
        result = resolve_azan_path("/nonexistent/no_match.mp3")
        from backend.settings import MUEZZINS_DIR
        if os.path.isdir(MUEZZINS_DIR):
            assert os.path.isfile(result)
        else:
            assert result == "/nonexistent/no_match.mp3"

    def test_known_muezzin_name_resolves(self):
        result = resolve_azan_path("قطامي")
        assert os.path.isfile(result) or result == "قطامي"

    def test_alternate_muezzin_name(self):
        result = resolve_azan_path("نعيم")
        assert os.path.isfile(result) or result == "نعيم"


class TestLoadSave:
    def test_load_returns_dict(self):
        s = load()
        assert isinstance(s, dict)

    def test_load_contains_expected_keys(self):
        s = load()
        assert "latitude" in s
        assert "longitude" in s
        assert "language" in s
        assert "theme" in s

    def test_save_and_reload(self):
        s = load()
        original = s.get("theme", "auto")
        s["theme"] = "test_save_value"
        save(s)
        try:
            s2 = load()
            assert s2["theme"] == "test_save_value"
        finally:
            s["theme"] = original
            save(s)

    def test_default_values(self):
        s = load()
        assert isinstance(s.get("latitude"), (int, float))
        assert isinstance(s.get("longitude"), (int, float))
        assert isinstance(s.get("azan_enabled"), dict)
        assert isinstance(s.get("offsets"), dict)

    def test_save_preserves_other_keys(self):
        s = load()
        original_keys = set(s.keys())
        s["_test_temp_key"] = "temp_value"
        save(s)
        try:
            s2 = load()
            assert "_test_temp_key" in s2
        finally:
            del s["_test_temp_key"]
            save(s)


class TestSetAutostart:
    def test_set_autostart_true_creates_file(self):
        set_autostart(True)
        autostart_file = os.path.join(
            os.path.expanduser("~"), ".config", "autostart", "athan-five-times.desktop"
        )
        assert os.path.isfile(autostart_file)

    def test_set_autostart_false_removes_file(self):
        set_autostart(True)
        autostart_file = os.path.join(
            os.path.expanduser("~"), ".config", "autostart", "athan-five-times.desktop"
        )
        set_autostart(False)
        assert not os.path.isfile(autostart_file)

    def test_autostart_file_contains_desktop_entry(self):
        autostart_file = os.path.join(
            os.path.expanduser("~"), ".config", "autostart", "athan-five-times.desktop"
        )
        set_autostart(True)
        try:
            with open(autostart_file) as f:
                content = f.read()
            assert "[Desktop Entry]" in content
            assert "Exec=" in content
        finally:
            set_autostart(False)


class TestSchemaVersion:
    def test_settings_version_is_positive_int(self):
        assert isinstance(SETTINGS_VERSION, int)
        assert SETTINGS_VERSION >= 1

    def test_loaded_settings_has_schema_version(self):
        s = load()
        assert "schema_version" in s
        assert s["schema_version"] == SETTINGS_VERSION


class TestSchemaToDict:
    def test_returns_dict_with_all_schema_fields(self):
        d = schema_to_dict()
        assert isinstance(d, dict)
        assert "country" in d
        assert "latitude" in d
        assert "language" in d
        assert "schema_version" in d

    def test_has_language_default(self):
        d = schema_to_dict()
        assert d["language"] == "ar"


class TestValidateAndCoerce:
    def test_int_coercion_from_string(self):
        result = validate_and_coerce({"volume": "5"})
        assert result["volume"] == 5.0

    def test_bool_coercion_from_string(self):
        result = validate_and_coerce({"first_run": "false"})
        assert result["first_run"] is False

    def test_bool_coercion_from_int(self):
        result = validate_and_coerce({"first_run": 0})
        assert result["first_run"] is False

    def test_preserves_unknown_keys(self):
        result = validate_and_coerce({"_custom_key": "custom_val"})
        assert result["_custom_key"] == "custom_val"

    def test_missing_keys_filled_with_defaults(self):
        result = validate_and_coerce({})
        assert result["country"] == "TN"
        assert result["language"] == "ar"
        assert result["theme"] == "dark"

    def test_none_value_falls_back_to_default(self):
        result = validate_and_coerce({"language": None})
        assert result["language"] == "ar"

    def test_dict_field_coerced(self):
        result = validate_and_coerce({"offsets": None})
        assert isinstance(result["offsets"], dict)

    def test_list_field_coerced(self):
        result = validate_and_coerce({"window_geometry": None})
        assert isinstance(result["window_geometry"], list)

    def test_int_field_coerced_from_float(self):
        result = validate_and_coerce({"pre_azan_minutes": 5.7})
        assert result["pre_azan_minutes"] == 5


class TestMigrationSystem:
    def test_migration_v0_to_v1_adds_language(self):
        old = {"country": "SA", "method": "Umm Al-Qura"}
        migrated = _run_migrations(deepcopy(old))
        assert migrated["language"] == "ar"

    def test_migration_v0_to_v1_adds_schema_version(self):
        old = {"country": "SA"}
        migrated = _run_migrations(deepcopy(old))
        assert migrated["schema_version"] == SETTINGS_VERSION

    def test_migration_v0_to_v1_preserves_existing_language(self):
        old = {"country": "SA", "language": "en"}
        migrated = _run_migrations(deepcopy(old))
        assert migrated["language"] == "en"

    def test_migration_v0_to_v1_preserves_existing_keys(self):
        old = {"country": "SA", "city": "Mecca"}
        migrated = _run_migrations(deepcopy(old))
        assert migrated["country"] == "SA"
        assert migrated["city"] == "Mecca"

    def test_migration_v0_to_v1_merges_subdicts(self):
        old = {"offsets": {"fajr": 5}}
        migrated = _run_migrations(deepcopy(old))
        assert migrated["offsets"]["fajr"] == 5
        assert migrated["offsets"]["dhuhr"] == 0

    def test_migration_v1_to_v2(self):
        current = {"schema_version": 1, "language": "fr"}
        migrated = _run_migrations(deepcopy(current))
        assert migrated["language"] == "fr"
        assert migrated["schema_version"] == 3

    def test_all_migrations_registered_sequentially(self):
        versions = sorted(MIGRATIONS.keys())
        expected = list(range(0, SETTINGS_VERSION))
        assert versions == expected, f"Expected migrations for versions {expected}, got {versions}"


class TestSettingsSchema:
    def test_dataclass_has_all_default_fields(self):
        schema = SettingsSchema()
        assert schema.theme == "dark"
        assert schema.language == "ar"
        assert schema.schema_version == SETTINGS_VERSION

    def test_offsets_default_has_all_prayers(self):
        schema = SettingsSchema()
        for prayer in ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"):
            assert prayer in schema.offsets

    def test_audio_default_has_all_prayers(self):
        schema = SettingsSchema()
        for prayer in ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha", "default"):
            assert prayer in schema.audio
