from datetime import date
from backend._constants import (
    PRAYERS_WITH_AZAN,
    THEME_IDS,
    LANGS,
    LANG_NAMES,
    DARK_THEMES,
    _display_key,
)


class TestPrayersWithAzan:
    def test_excludes_sunrise(self):
        assert PRAYERS_WITH_AZAN == ["fajr", "dhuhr", "asr", "maghrib", "isha"]


class TestThemeIds:
    def test_contains_auto(self):
        assert "auto" in THEME_IDS

    def test_all_themes_present(self):
        expected = {"auto", "light", "dark", "ottoman_gold", "catppuccin_mocha", "catppuccin_latte"}
        assert set(THEME_IDS) == expected


class TestLangs:
    def test_all_languages_have_names(self):
        for code in LANGS:
            assert code in LANG_NAMES, f"Missing name for {code}"

    def test_lang_names_all_nonempty(self):
        for name in LANG_NAMES.values():
            assert len(name) > 0


class TestDarkThemes:
    def test_dark_contains_dark(self):
        assert "dark" in DARK_THEMES

    def test_light_not_dark(self):
        assert "light" not in DARK_THEMES


class TestDisplayKey:
    def test_normal_day_returns_key(self):
        monday = date(2025, 6, 16)
        assert _display_key("dhuhr", monday) == "dhuhr"

    def test_friday_returns_jumuah(self):
        friday = date(2025, 6, 13)
        assert _display_key("dhuhr", friday) == "jumuah"

    def test_defaults_to_today(self):
        result = _display_key("dhuhr")
        today = date.today()
        expected = "jumuah" if today.weekday() == 4 else "dhuhr"
        assert result == expected
