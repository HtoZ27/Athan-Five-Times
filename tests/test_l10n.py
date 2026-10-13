from backend.l10n import _build_languages


class TestBuildLanguages:
    def test_returns_list_of_dicts(self):
        langs = _build_languages()
        assert isinstance(langs, list)
        assert len(langs) >= 17

    def test_each_has_code_and_name(self):
        for entry in _build_languages():
            assert "code" in entry
            assert "name" in entry
            assert len(entry["code"]) > 0
            assert len(entry["name"]) > 0

    def test_arabic_first(self):
        langs = _build_languages()
        arabic = next(entry for entry in langs if entry["code"] == "ar")
        assert arabic["name"] == "العربية"

    def test_english_name(self):
        langs = _build_languages()
        english = next(entry for entry in langs if entry["code"] == "en")
        assert english["name"] == "English"
