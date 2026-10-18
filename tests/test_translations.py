from datetime import date
import os
import re


from backend.i18n import t, t_prayer, format_date, set_lang, LANGS, get_lang
from backend.hijri import format_hijri
from backend.translations import (
    city_name,
    country_name,
    day_name,
    greg_month_name,
    hijri_month_name,
    hijri_suffix,
    ramadan_countdown,
    translate_islamic_event,
)


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

    QML_DIR = os.path.join(os.path.dirname(__file__), "..", "qml")
    TRANSLATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "translations")

    @staticmethod
    def _qml_tr_keys():
        import glob
        import re

        pattern = re.compile(r'tr\(\s*"((?:[^"\\]|\\.)*)"')
        keys = set()
        for path in glob.glob(os.path.join(TestUiKeyParity.QML_DIR, "*.qml")):
            with open(path, encoding="utf-8") as f:
                src = f.read()
            for match in pattern.finditer(src):
                key = match.group(1).replace('\\"', '"')
                key = key.replace("\\n", "\n").replace("\\\\", "\\")
                keys.add(key)
        return keys

    def test_new_keys_present_in_covered_languages(self):
        import json

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

    def test_all_qml_tr_keys_present_in_ar_and_en(self):
        import json

        keys = self._qml_tr_keys()
        assert len(keys) > 100, f"QML key extraction looks broken: {len(keys)} keys"
        for code in ("ar", "en"):
            with open(os.path.join(self.TRANSLATIONS_DIR, f"{code}.json"), encoding="utf-8") as f:
                ui = json.load(f)["ui"]
            missing = sorted(k for k in keys if k not in ui)
            assert not missing, f"{code}.json missing QML keys: {missing[:5]}"

    def test_untranslated_placeholder_falls_back_to_english(self):
        set_lang("de")
        assert t("الإزاحة") == "Offsets"
        set_lang("hi")
        assert t("الإزاحة") == "Offsets"
        set_lang("ar")

    def test_arabic_script_languages_keep_their_values(self):
        set_lang("ur")
        assert t("الإزاحة") == "الإزاحة"
        set_lang("ar")

    def test_missing_key_uses_english_before_arabic(self):
        set_lang("tk")
        assert t("شريط النظام") == "System tray"
        set_lang("ar")

    def test_translated_value_is_not_replaced_by_fallback(self):
        import re

        set_lang("de")
        value = t("المؤذن الافتراضي")
        assert value
        assert not re.search(r"[\u0600-\u06FF]", value)
        set_lang("ar")


class TestWidgetFeatureKeys:
    """Widget/reminders keys must never surface Arabic text in non-Arabic-script
    languages (localized value or English fallback only)."""

    ARABIC_SCRIPT = {"ar", "ur", "ps"}
    ARABIC = re.compile(r"[\u0600-\u06FF]")

    FEATURE_KEYS = [
        "الإثنين",
        "الثلاثاء",
        "الأربعاء",
        "الخميس",
        "الجمعة",
        "السبت",
        "الأحد",
        "كل يوم",
        "أيام التكرار:",
        "الوقت (HH:MM):",
        "نص التذكير",
        "إضافة تذكير",
        "(اتركها فارغة لكل يوم)",
        "إضافة",
        "إلغاء",
        "حفظ",
        "تذكيرات",
        "الصلاة القادمة",
        "إغلاق الودجة",
        "غداً",
        "أذان الأوقات الخمس",
    ]

    def test_no_arabic_for_non_arabic_script_languages(self):
        for code in LANGS:
            set_lang(code)
            for key in self.FEATURE_KEYS:
                value = t(key)
                assert value, f"empty value for {code}: {key}"
                if code not in self.ARABIC_SCRIPT:
                    assert not self.ARABIC.search(value), f"Arabic leak in {code}: {key} -> {value}"
        set_lang("ar")

    def test_recently_added_keys_are_translated(self):
        set_lang("tk")
        assert t("حفظ") == "Sakla"
        set_lang("de")
        assert t("إغلاق الودجة") != "إغلاق الودجة"
        assert not self.ARABIC.search(t("إغلاق الودجة"))
        set_lang("hi")
        assert not self.ARABIC.search(t("غداً"))
        set_lang("ar")


class TestHijriLocalization:
    """Hijri events, month names, era suffix and countdown must follow the
    interface language instead of leaking Arabic text."""

    ARABIC_SCRIPT = {"ar", "ur", "ps"}
    ARABIC = re.compile(r"[\u0600-\u06FF]")

    @staticmethod
    def _event_keys():
        path = os.path.join(os.path.dirname(__file__), "..", "backend", "islamic_events.py")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        keys = re.findall(r'events\.append\("([^"]+)"\)', src)
        assert len(keys) >= 19, f"event extraction looks broken: {len(keys)}"
        return keys

    def test_every_event_translated_in_every_language(self):
        for code in LANGS:
            set_lang(code)
            for key in self._event_keys():
                value = translate_islamic_event(key)
                assert value, f"empty event for {code}: {key}"
                if code != "ar":
                    assert value != key, f"untranslated event in {code}: {key}"
                if code not in self.ARABIC_SCRIPT:
                    assert not self.ARABIC.search(value), f"Arabic leak in {code}: {value}"
        set_lang("ar")

    def test_event_translation_spot_checks(self):
        set_lang("de")
        assert translate_islamic_event("عاشوراء") == "Aschura"
        set_lang("tr")
        assert translate_islamic_event("عاشوراء") == "Aşure"
        set_lang("ar")
        assert translate_islamic_event("عاشوراء") == "عاشوراء"

    def test_unknown_event_passthrough(self):
        set_lang("de")
        assert translate_islamic_event("__not_an_event__") == "__not_an_event__"
        assert translate_islamic_event("") == ""
        set_lang("ar")

    def test_ramadan_countdown_localized(self):
        set_lang("de")
        assert ramadan_countdown(5) == "Noch 5 Tage bis Ramadan"
        set_lang("tk")
        assert ramadan_countdown(5) == "Remezana 5 gün galdy"
        set_lang("ar")
        assert ramadan_countdown(1) == "باقي 1 يوم على رمضان"
        assert ramadan_countdown(5) == "باقي 5 أيام على رمضان"

    def test_countdown_never_arabic_for_non_script_languages(self):
        for code in LANGS:
            set_lang(code)
            value = ramadan_countdown(5)
            assert "5" in value, f"missing number for {code}: {value}"
            if code not in self.ARABIC_SCRIPT:
                assert not self.ARABIC.search(value), f"Arabic leak in {code}: {value}"
        set_lang("ar")

    def test_hijri_suffix_per_language(self):
        set_lang("ar")
        assert hijri_suffix() == "هـ"
        set_lang("ur")
        assert hijri_suffix() == "ھـ"
        set_lang("ps")
        assert hijri_suffix() == "هـ"
        set_lang("de")
        assert hijri_suffix() == "AH"
        set_lang("tk")
        assert hijri_suffix() == "AH"
        set_lang("ar")

    def test_hijri_months_no_arabic_leak(self):
        for code in LANGS:
            set_lang(code)
            for month in range(1, 13):
                name = hijri_month_name(month)
                assert name, f"empty month {month} for {code}"
                if code not in self.ARABIC_SCRIPT:
                    assert not self.ARABIC.search(name), f"Arabic month in {code}: {name}"
        set_lang("ar")

    def test_hijri_month_spot_checks(self):
        set_lang("tk")
        assert hijri_month_name(9) == "Remezan"
        set_lang("so")
        assert hijri_month_name(9) == "Ramadaan"
        set_lang("ms")
        assert hijri_month_name(12) == "Zulhijjah"
        set_lang("hi")
        assert hijri_month_name(9) == "रमज़ान"
        set_lang("ar")
        assert hijri_month_name(9) == "رمضان"

    def test_format_hijri_localized(self):
        set_lang("tk")
        line = format_hijri(date(2026, 10, 18))
        assert "AH" in line and not self.ARABIC.search(line)
        set_lang("hi")
        assert not self.ARABIC.search(format_hijri(date(2026, 10, 18)))
        set_lang("ar")
        assert "هـ" in format_hijri(date(2026, 10, 18))

    def test_gregorian_connector_follows_script(self):
        set_lang("ar")
        greg, _ = format_date(date(2025, 6, 15))
        assert "،" in greg
        set_lang("de")
        greg, _ = format_date(date(2025, 6, 15))
        assert "," in greg and "،" not in greg
        set_lang("ar")


class TestCalendarNames:
    """Gregorian day/month names must be localized as well — no English or
    Arabic leftovers in the languages that now carry native lists."""

    ARABIC_SCRIPT = {"ar", "ur", "ps"}
    ARABIC = re.compile(r"[\u0600-\u06FF]")

    def test_day_and_month_names_localized(self):
        for code in LANGS:
            set_lang(code)
            for weekday in range(7):
                assert day_name(weekday), f"empty day {weekday} for {code}"
            for month in range(1, 13):
                assert greg_month_name(month), f"empty month {month} for {code}"
        set_lang("ar")

    def test_no_arabic_leak_in_date_lines(self):
        for code in LANGS:
            set_lang(code)
            greg, hijri = format_date(date(2026, 10, 19))
            assert greg and hijri
            if code not in self.ARABIC_SCRIPT:
                assert not self.ARABIC.search(greg), f"Arabic leak in {code}: {greg}"
                assert not self.ARABIC.search(hijri), f"Arabic leak in {code}: {hijri}"
        set_lang("ar")

    def test_gregorian_spot_checks(self):
        set_lang("tk")
        assert day_name(0) == "Duşenbe"
        assert greg_month_name(10) == "Oktýabr"
        set_lang("so")
        assert greg_month_name(7) == "Luulyo"
        assert greg_month_name(12) == "Diseembar"
        set_lang("ms")
        assert day_name(6) == "Ahad"
        assert greg_month_name(8) == "Ogos"
        set_lang("hi")
        assert day_name(6) == "रविवार"
        assert greg_month_name(1) == "जनवरी"
        set_lang("ps")
        assert greg_month_name(5) == "مۍ"
        set_lang("ur")
        assert day_name(0) == "پیر"
        set_lang("id")
        assert greg_month_name(8) == "Agustus"
        set_lang("pa")
        assert greg_month_name(1) == "ਜਨਵਰੀ"
        set_lang("ar")

    def test_tk_prayer_names_match_official_sources(self):
        set_lang("tk")
        assert t_prayer("fajr") == "Ertir"
        assert t_prayer("sunrise") == "Gün dogşy"
        assert t_prayer("isha") == "Ýassy"
        set_lang("ar")
