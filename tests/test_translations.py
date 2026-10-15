from datetime import date


from backend.i18n import t, t_prayer, format_date, set_lang, LANGS, get_lang
from backend.translations import city_name, country_name


class TestTranslationFunction:
    def test_t_returns_arabic_key_by_default(self):
        set_lang("ar")
        result = t("app_name")
        assert isinstance(result, str)
        assert "أذان" in result

    def test_t_returns_english_when_switched(self):
        set_lang("en")
        result = t("app_name")
        assert result == "Prayer Times"

    def test_t_french_returns_french(self):
        set_lang("fr")
        result = t("app_name")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_t_missing_key_returns_key_itself(self):
        result = t("__nonexistent_key_xyz__")
        assert result == "__nonexistent_key_xyz__"

    def test_t_prayer_returns_prayer_name(self):
        set_lang("ar")
        name = t_prayer("fajr")
        assert name == "الفجر"

    def test_t_prayer_english(self):
        set_lang("en")
        name = t_prayer("fajr")
        assert isinstance(name, str)
        assert len(name) > 0

    def test_t_with_arg(self):
        set_lang("ar")
        result = t("pre_alert", mins="10", prayer="الفجر")
        assert isinstance(result, str)

    def test_all_languages_have_app_name(self):
        for lang in LANGS:
            set_lang(lang)
            name = t("app_name")
            assert name, f"app_name empty for {lang}"

    def test_set_lang_affects_get_lang(self):
        set_lang("fr")
        assert get_lang() == "fr"
        set_lang("ar")
        assert get_lang() == "ar"

    def test_credits_html_returns_string(self):
        from backend.i18n import credits_html

        html = credits_html()
        assert isinstance(html, str)
        assert len(html) > 0

    def test_credits_title_returns_string(self):
        from backend.i18n import credits_title

        title = credits_title()
        assert isinstance(title, str)
        assert len(title) > 0

    def test_city_name_arabic_returns_arabic(self):
        set_lang("ar")
        assert city_name("Tunis") == "تونس"

    def test_city_name_english_returns_english(self):
        set_lang("en")
        assert city_name("Tunis") == "Tunis"

    def test_city_name_unknown_returns_itself(self):
        set_lang("ar")
        assert city_name("__nonexistent_city__") == "__nonexistent_city__"

    def test_city_name_french_returns_english(self):
        set_lang("fr")
        assert city_name("Tunis") == "Tunis"

    def test_country_name_arabic_returns_arabic(self):
        set_lang("ar")
        assert country_name("TN") == "تونس"
        assert country_name("US") == "الولايات المتحدة"

    def test_country_name_english_returns_english(self):
        set_lang("en")
        name = country_name("TN")
        assert name == "Tunisia"

    def test_country_name_invalid_code_returns_code(self):
        set_lang("ar")
        assert country_name("__XX__") == "__XX__"

    def test_country_name_french_returns_french(self):
        set_lang("fr")
        assert country_name("TN") == "Tunisie"

    def test_t_prayer_jumuah(self):
        friday = date(2025, 6, 13)  # Friday
        from backend._constants import _display_key

        key = _display_key("dhuhr", friday)
        name = t_prayer(key)
        assert isinstance(name, str)


class TestFormatDate:
    def test_format_date_returns_tuple(self):
        d = date.today()
        greg, hijri = format_date(d)
        assert isinstance(greg, str)
        assert isinstance(hijri, str)
        assert len(greg) > 0
        assert len(hijri) > 0

    def test_format_date_with_offset(self):
        d = date(2025, 1, 15)
        greg, hijri = format_date(d, offset_days=0)
        assert "يناير" in greg or "Jan" in greg or "January" in greg

    def test_format_date_contains_hijri_marker(self):
        d = date.today()
        _, hijri = format_date(d)
        assert "هـ" in hijri

    def test_format_date_different_languages(self):
        d = date(2025, 6, 15)
        set_lang("en")
        greg_en, _ = format_date(d)
        set_lang("ar")
        greg_ar, _ = format_date(d)
        assert greg_en != greg_ar

    def test_format_date_known_date(self):
        set_lang("ar")
        d = date(2025, 1, 1)
        greg, hijri = format_date(d)
        assert "الأربعاء" in greg
        assert "يناير" in greg
        assert "هـ" in hijri


class TestUiKeyParity:
    """Recently added settings labels must exist in the main languages,
    and any remaining gap must fall back to English (never Arabic text)."""

    NEW_KEYS = [
        "اختيار المنطقة الزمنية لحساب مواقيت الصلاة بدقة",
        "❓ حول التطبيق",
        "📋",
    ]
    COVERED = ["de", "es", "es_la", "fr", "id", "it", "ms", "ru", "tr"]

    def test_new_keys_present_in_covered_languages(self):
        import json
        import os

        base = os.path.join(os.path.dirname(__file__), "..", "backend", "translations")
        for code in self.COVERED:
            with open(os.path.join(base, f"{code}.json"), encoding="utf-8") as f:
                ui = json.load(f)["ui"]
            for key in self.NEW_KEYS:
                assert key in ui, f"{key!r} missing in {code}"

    def test_missing_key_falls_back_to_english_not_arabic(self):
        # 'hi' intentionally lacks the timezone hint: English, not Arabic.
        set_lang("hi")
        assert t("اختيار المنطقة الزمنية لحساب مواقيت الصلاة بدقة") == (
            "Select timezone for accurate prayer calculation"
        )
        set_lang("ar")
