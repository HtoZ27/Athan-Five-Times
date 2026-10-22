"""Tests for the structured adhkar library (backend/adhkar_repo.py)."""

import glob
import json
import os

import pytest

from backend.adhkar_repo import (
    ALLOWED_REFERENCE_IDS,
    AdhkarRepository,
    AdhkarValidationError,
    get_structured_texts,
    validate_category,
    validate_index,
)

ASSETS = os.path.join(os.path.dirname(__file__), "..", "backend", "assets", "adhkar")
TRANSLATIONS = os.path.join(os.path.dirname(__file__), "..", "backend", "translations")


class TestIndex:
    def test_full_library_categories(self):
        repo = AdhkarRepository()
        index = repo.get_index()
        assert len(index) == 23
        ids = {c["id"] for c in index}
        assert {"morning", "evening", "after_prayer"} <= ids

    def test_index_sorted_by_order(self):
        repo = AdhkarRepository()
        orders = [c["order"] for c in repo.get_index()]
        assert orders == sorted(orders)

    def test_index_entries_have_names(self):
        for c in AdhkarRepository().get_index():
            assert c["name_ar"] and c["name_en"] and c["id"]

    def test_all_index_assets_exist(self):
        repo = AdhkarRepository(base_dir=os.path.abspath(ASSETS))
        for c in repo.get_index():
            assert os.path.isfile(
                os.path.join(os.path.abspath(ASSETS), os.path.basename(c["asset"]))
            ), c["id"]

    def test_all_index_icons_exist(self):
        icons_dir = os.path.join(os.path.dirname(os.path.abspath(ASSETS)), "adhkar_icons")
        known = {
            "morning",
            "evening",
            "after_prayer",
            "sleep",
            "waking",
            "home",
            "eating",
            "mosque",
            "travel",
            "dua",
            "prayer",
            "adhan",
            "tahara",
            "libas",
            "sick",
            "hajj",
            "distress",
            "ruqya",
            "protection",
            "manners",
            "nature",
            "tasbih",
            "istighfar",
            "misc",
        }
        for c in AdhkarRepository().get_index():
            icon = c.get("icon") or "dua"
            assert icon in known, c["id"]
            assert os.path.isfile(os.path.join(icons_dir, icon + ".png")), icon


class TestCategories:
    def test_morning_items_structured(self):
        cat = AdhkarRepository().load_category("morning")
        assert len(cat["items"]) == 26
        for it in cat["items"]:
            assert it["arabic"]
            assert it["count"] >= 1

    def test_after_prayer_items(self):
        cat = AdhkarRepository().load_category("after_prayer")
        assert len(cat["items"]) == 12

    def test_unknown_category_raises(self):
        with pytest.raises(KeyError):
            AdhkarRepository().load_category("nope")

    def test_lru_eviction(self):
        repo = AdhkarRepository(max_cache_size=2)
        repo.load_category("morning")
        repo.load_category("evening")
        repo.load_category("أذكار_النوم_والليل")
        assert set(repo._cache.keys()) == {"evening", "أذكار_النوم_والليل"}

    def test_clear_cache(self):
        repo = AdhkarRepository()
        repo.load_category("morning")
        repo.clear_cache()
        assert repo._cache == {} and repo._index is None


def _valid_item(**overrides):
    item = {
        "id": "i1",
        "arabic": "ذِكْرٌ",
        "count": 1,
        "reference_id": "bukhari",
        "reference_detail": "البخاري (1)",
    }
    item.update(overrides)
    return item


class TestValidation:
    def test_bad_index_rejected(self):
        with pytest.raises(AdhkarValidationError):
            validate_index({"categories": []})
        with pytest.raises(AdhkarValidationError):
            validate_index({"categories": [{"id": "x"}]})

    def test_bad_category_rejected(self):
        with pytest.raises(AdhkarValidationError):
            validate_category({"id": "x", "items": []})
        with pytest.raises(AdhkarValidationError):
            validate_category({"id": "x", "items": [{"id": "i1"}]})

    def test_sanad_is_mandatory(self):
        validate_category({"id": "x", "items": [_valid_item()]})
        for missing in ("reference_id", "reference_detail", "count"):
            item = _valid_item()
            del item[missing]
            with pytest.raises(AdhkarValidationError):
                validate_category({"id": "x", "items": [item]})
        with pytest.raises(AdhkarValidationError):
            validate_category(
                {"id": "x", "items": [_valid_item(reference_id="unknown-book")]}
            )
        with pytest.raises(AdhkarValidationError):
            validate_category({"id": "x", "items": [_valid_item(count=0)]})

    def test_invalid_translations_rejected(self):
        validate_category(
            {"id": "x", "items": [_valid_item(translations={"en": "Dhikr"})]}
        )
        with pytest.raises(AdhkarValidationError):
            validate_category(
                {"id": "x", "items": [_valid_item(translations=["Dhikr"])]}
            )
        with pytest.raises(AdhkarValidationError):
            validate_category(
                {"id": "x", "items": [_valid_item(translations={"en": "  "})]}
            )


class TestSanad:
    def test_every_item_has_sanad(self):
        repo = AdhkarRepository()
        for category in repo.get_index():
            for item in repo.load_category(category["id"])["items"]:
                where = (category["id"], item["id"])
                assert item["reference_id"] in ALLOWED_REFERENCE_IDS, where
                assert item["reference_detail"].strip(), where
                assert isinstance(item["count"], int), where
                assert item["count"] >= 1, where

    def test_corrected_counts(self):
        repo = AdhkarRepository()
        morning = {it["id"]: it for it in repo.load_category("morning")["items"]}
        evening = {it["id"]: it for it in repo.load_category("evening")["items"]}
        sleep = {
            it["id"]: it for it in repo.load_category("أذكار_النوم_والليل")["items"]
        }
        assert morning["m05"]["count"] == 1
        assert morning["m09"]["count"] == 10
        assert morning["mor20"]["count"] == 1
        assert morning["mor22"]["count"] == 1
        assert morning["mor26"]["count"] == 1
        assert evening["eve19"]["count"] == 1
        assert evening["eve21"]["count"] == 1
        assert evening["eve25"]["count"] == 1
        assert evening["eve28"]["count"] == 10
        assert sleep["s02"]["count"] == 1

    def test_corrected_sources(self):
        repo = AdhkarRepository()
        morning = {it["id"]: it for it in repo.load_category("morning")["items"]}
        sleep = {
            it["id"]: it for it in repo.load_category("أذكار_النوم_والليل")["items"]
        }
        assert "النحل: 98" in morning["m02"]["reference_detail"]
        assert morning["m06"]["reference_id"] == "tirmidhi"
        assert morning["mor22"]["reference_id"] == "abudawud"
        assert sleep["s02"]["count"] == 1
        assert "دون قوله" in sleep["s02"]["reference_detail"]
        assert sleep["sle14"]["reference_id"] == "tirmidhi"
        prayer = {
            it["id"]: it
            for it in repo.load_category("أدعية_الصلاة")["items"]
        }
        assert "بِرِضَاكَ" in prayer["دعاء_السجود_07"]["arabic"]

    def test_restored_morning_evening_items(self):
        repo = AdhkarRepository()
        morning = {it["id"]: it for it in repo.load_category("morning")["items"]}
        evening = {it["id"]: it for it in repo.load_category("evening")["items"]}
        for item_id in ("m04", "mor14", "mor15", "mor16", "mor21"):
            assert item_id in morning
        for item_id in ("e06", "e08", "eve14", "eve15", "eve20"):
            assert item_id in evening
        assert morning["m04"]["count"] == 1
        assert morning["mor14"]["count"] == 4
        assert morning["mor16"]["count"] == 7
        assert "الضعيفة (5020)" in morning["m04"]["reference_detail"]
        assert "الموقوف" in morning["mor16"]["reference_detail"]
        assert "حكم الرفع" in morning["mor16"]["reference_detail"]


class TestLegacyCompat:
    def test_prayer_keys_map_to_after_prayer(self):
        for key in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
            texts = get_structured_texts(key)
            assert len(texts) == 12
            assert all(isinstance(t, str) and t for t in texts)

    def test_morning_evening(self):
        assert len(get_structured_texts("morning")) == 26
        assert len(get_structured_texts("evening")) == 25

    def test_unknown_key_empty(self):
        assert get_structured_texts("nope") == []


class TestNoDuplication:
    def test_no_flat_athkar_in_translations(self):
        """Single source of truth: translations must not carry athkar texts."""
        dupes = []
        for f in sorted(glob.glob(os.path.join(TRANSLATIONS, "*.json"))):
            d = json.load(open(f, encoding="utf-8"))
            if "athkar" in d:
                dupes.append(os.path.basename(f))
        assert dupes == [], f"flat athkar duplicates library in: {dupes}"

    def test_total_item_count(self):
        total = 0
        for c in AdhkarRepository().get_index():
            total += len(AdhkarRepository().load_category(c["id"])["items"])
        assert total == 361, total


class TestCategoryTranslations:
    def test_every_category_name_has_ui_translation(self):
        from backend.i18n import LANGS

        names = [c["name_ar"] for c in AdhkarRepository().get_index()]
        for code in LANGS:
            path = os.path.join(TRANSLATIONS, f"{code}.json")
            with open(path, encoding="utf-8") as f:
                ui = json.load(f)["ui"]
            missing = [name for name in names if name not in ui]
            assert not missing, f"{code}.json missing category names: {missing[:3]}"

    def test_non_arabic_category_names_have_no_arabic(self):
        import re
        from backend.i18n import LANGS

        arabic = re.compile(r"[\u0600-\u06FF]")
        names = [c["name_ar"] for c in AdhkarRepository().get_index()]
        for code in LANGS:
            if code in {"ar", "ur", "ps"}:
                continue
            with open(os.path.join(TRANSLATIONS, f"{code}.json"), encoding="utf-8") as f:
                ui = json.load(f)["ui"]
            leaked = [name for name in names if arabic.search(ui[name])]
            assert not leaked, f"{code}.json Arabic category names: {leaked[:3]}"

    def test_index_english_names_are_english(self):
        import re

        arabic = re.compile(r"[\u0600-\u06FF]")
        leaked = [
            c["id"]
            for c in AdhkarRepository().get_index()
            if arabic.search(c["name_en"])
        ]
        assert not leaked, f"Arabic name_en values: {leaked}"

    def test_athkar_tab_translates_category_names(self):
        path = os.path.join(os.path.dirname(__file__), "..", "qml", "AthkarTab.qml")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        assert "tr(modelData.name_ar)" in src
        assert "tr(openCategoryName)" in src


def _bare_arabic(s: str) -> str:
    """Arabic text stripped of diacritics/tatweel for robust matching."""
    import unicodedata

    out = []
    for ch in unicodedata.normalize("NFD", s):
        if unicodedata.category(ch) == "Mn" or ch == "ـ":
            continue
        out.append({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"}.get(ch, ch))
    return "".join(out)


class TestTextIntegrity:
    """Guard rails for the adhkar text audit: operational instructions must
    never live inside recitable text, and key texts must stay complete."""

    BANNED_BARE = [
        "بعد كل صلاة",
        "عقب كل صلاة",
        "بعد السلام من صلاة",
        # NOTE: "انك لا تخلف الميعاد" deliberately excluded — it occurs
        # legitimately inside Quran 3:194 (waking/wak06).
    ]

    def _all_items(self):
        repo = AdhkarRepository()
        for c in repo.get_index():
            for it in repo.load_category(c["id"])["items"]:
                yield c["id"], it

    def test_no_operational_instructions_in_text(self):
        bad = []
        for cid, it in self._all_items():
            bare = _bare_arabic(it["arabic"])
            for phrase in self.BANNED_BARE:
                if phrase in bare:
                    bad.append((cid, it["id"], phrase))
        assert not bad, f"instructional text inside dhikr: {bad}"

    def test_kursi_items_complete(self):
        repo = AdhkarRepository()
        for cid, iid in [
            ("morning", "m02"),
            ("evening", "e02"),
            ("أذكار_النوم_والليل", "s04"),
            ("after_prayer", "aft11"),
        ]:
            cat = repo.load_category(cid)
            it = next(i for i in cat["items"] if i["id"] == iid)
            assert "وهو العلي العظيم" in _bare_arabic(it["arabic"]), (cid, iid)

    def test_istiadha_merged_with_kursi(self):
        repo = AdhkarRepository()
        for cid, iid in [("morning", "m02"), ("evening", "e02")]:
            cat = repo.load_category(cid)
            it = next(i for i in cat["items"] if i["id"] == iid)
            bare = _bare_arabic(it["arabic"])
            assert "اعوذ بالله من الشيطان الرجيم" in bare, (cid, iid)
            assert "النحل: 98" in it["reference_detail"], (cid, iid)

    def test_istighfar_items_complete(self):
        repo = AdhkarRepository()
        for cid, iid in [("morning", "m07"), ("evening", "e05")]:
            cat = repo.load_category(cid)
            it = next(i for i in cat["items"] if i["id"] == iid)
            assert "فانه لا يغفر الذنوب" in _bare_arabic(it["arabic"]), (cid, iid)

    def test_parentheses_balanced(self):
        bad = []
        for cid, it in self._all_items():
            t = it["arabic"]
            for a, b in [("(", ")"), ("[", "]"), ("﴾", "﴿")]:
                if t.count(a) != t.count(b):
                    bad.append((cid, it["id"], a, t.count(a), b, t.count(b)))
        assert not bad, f"unbalanced brackets: {bad}"

    def test_category_icons_exist(self):
        icons_dir = os.path.join(
            os.path.dirname(__file__), "..", "backend", "assets", "adhkar_icons"
        )
        repo = AdhkarRepository()
        missing = []
        mismatch = []
        for c in repo.get_index():
            cat = repo.load_category(c["id"])
            icon = cat.get("icon") or "dua"
            path = os.path.join(icons_dir, f"{icon}.png")
            if not os.path.isfile(path):
                missing.append((c["id"], icon))
            if c.get("icon") != cat.get("icon"):
                mismatch.append((c["id"], c.get("icon"), cat.get("icon")))
        assert not missing, f"missing icon files: {missing}"
        assert not mismatch, f"index/file icon mismatch: {mismatch}"


class TestAfterPrayerTranslations:
    """Pilot translation coverage for the after-prayer category.

    Sources: legacy translations (commit 9fbacb2), HadeethEnc 65102 for
    ap09, AlQuran Cloud editions for aft10/aft11, quranenc for Punjabi,
    and the official Turkmen Directorate translation for Turkmen.
    """

    def test_all_items_expose_translations(self):
        cat = AdhkarRepository().load_category("after_prayer")
        for it in cat["items"]:
            assert it["translations"], it["id"]
            assert it["translations"].get("ar") == it["arabic"], it["id"]
            for lang, text in it["translations"].items():
                assert text.strip(), f"{it['id']}/{lang} is empty"

    def test_translation_keys_are_supported_languages(self):
        from backend.i18n import LANGS

        cat = AdhkarRepository().load_category("after_prayer")
        for it in cat["items"]:
            unknown = set(it["translations"]) - set(LANGS)
            assert not unknown, f"{it['id']}: {unknown}"

    def test_old_translations_cover_dua_items(self):
        from backend.i18n import LANGS

        cat = AdhkarRepository().load_category("after_prayer")
        for it in cat["items"]:
            if it["id"] in {"aft10", "aft11"}:
                continue
            missing = set(LANGS) - set(it["translations"])
            assert not missing, f"{it['id']} missing: {sorted(missing)}"

    def test_quran_translations_cover_supported_languages(self):
        cat = AdhkarRepository().load_category("after_prayer")
        by_id = {it["id"]: it for it in cat["items"]}
        from backend.i18n import LANGS

        for iid in ("aft10", "aft11"):
            missing = set(LANGS) - set(by_id[iid]["translations"])
            assert not missing, f"{iid} missing: {sorted(missing)}"

    def test_aft10_uses_basmala_not_full_fatiha(self):
        cat = AdhkarRepository().load_category("after_prayer")
        by_id = {it["id"]: it for it in cat["items"]}
        aft10 = by_id["aft10"]["translations"]
        # Fatiha 1:2-1:7 must not be repeated three times before the short surahs.
        fatiha_only = {
            "en": "Guide us to the straight path",
            "tr": "Bizi doğru yola eriştir.",
            "id": "Tunjukilah kami jalan yang lurus",
            "fr": "Guide-nous dans le droit chemin",
            "de": "Leite uns den geraden Weg",
            "es": "Dirígenos por la vía recta",
            "it": "Guidaci sulla retta via",
            "ru": "Веди нас прямым путем",
            "hi": "हमें सीधा रास्ता दिखा",
            "ur": "ہم کو سیدھے رستے چلا",
            "ps": "ته مونږ ته سَمَه (نېغه) لاره وښَیَه",
            "so": "ee nagu hanuuni jidka toosan (Xaqa).",
            "ms": "Tunjukilah kami jalan yang lurus",
            "es_la": "Dirígenos por la vía recta",
        }
        for lang, phrase in fatiha_only.items():
            assert phrase not in aft10[lang], f"aft10/{lang} contains full Fatiha"

    def test_non_arabic_translations_have_no_arabic_script(self):
        import re

        arabic = re.compile(r"[\u0600-\u06FF]")
        cat = AdhkarRepository().load_category("after_prayer")
        for it in cat["items"]:
            for lang, text in it["translations"].items():
                if lang in {"ar", "ur", "ps"}:
                    continue
                assert not arabic.search(text), f"{it['id']}/{lang}: {text[:80]}"

    def test_aft10_does_not_repeat_short_surahs(self):
        cat = AdhkarRepository().load_category("after_prayer")
        by_id = {it["id"]: it for it in cat["items"]}
        tr = by_id["aft10"]["translations"]["tr"]
        assert tr.count("De ki:") == 3
        assert tr.count("Yaratıkların şerrinden") == 1
        assert tr.count("İnsanlardan ve cinlerden") == 1

    def test_aft11_complete_for_all_languages(self):
        cat = AdhkarRepository().load_category("after_prayer")
        by_id = {it["id"]: it for it in cat["items"]}
        endings = {
            "ar": "العلي العظيم",
            "en": "Most High, the Most Great",
            "fr": "le Très Haut, le Très Grand",
            "de": "der Erhabene und Allgewaltige",
            "es": "el Altísimo, el Grandioso",
            "es_la": "el Altísimo, el Grandioso",
            "it": "l'Altissimo, l'Immenso",
            "ru": "Возвышенный, Великий",
            "tr": "yücedir, büyüktür",
            "hi": "आलीशान बुजुर्ग़ मरतबा",
            "ur": "عالی رتبہ اور جلیل القدر",
            "ps": "ډېر اوچت دى، ډېر لوى دى",
            "so": "sareeye wayn",
            "id": "Maha Tinggi lagi Maha Besar",
            "ms": "Maha Tinggi (darjat kemuliaanNya), lagi Maha Besar",
            "pa": "ਮਹਾਨ ਅਤੇ ਸਰਬ-ਉੱਚ ਵਡਿਆਈ ਵਾਲੀ ਹਸਤੀ",
            "tk": "Beýikdir, Belentdir",
        }
        for lang, ending in endings.items():
            text = by_id["aft11"]["translations"][lang]
            if lang == "ar":
                assert ending in _bare_arabic(text), f"aft11/{lang}"
            else:
                assert ending in text, f"aft11/{lang}"
        assert "El. el Viviente" not in by_id["aft11"]["translations"]["es"]
        assert "El. el Viviente" not in by_id["aft11"]["translations"]["es_la"]

    def test_ap04_completion_phrase_present(self):
        cat = AdhkarRepository().load_category("after_prayer")
        by_id = {it["id"]: it for it in cat["items"]}
        phrases = {
            "en": "Completion of the hundred:",
            "fr": "Complément de la centaine",
            "de": "Vollendung der Hundert",
            "es": "Cumplimiento del centenar",
            "es_la": "Cumplimiento del centenar",
            "it": "Completamento del centinaio",
            "ru": "Дополнение до сотни",
            "tr": "Yüzü tamamlayan",
            "hi": "सौ की पूर्ति",
            "ur": "سو کی تکمیل",
            "ps": "د سلو بشپړول",
            "so": "Dhamaystirka boqolka",
            "id": "Penyempurna seratus",
            "ms": "Penyempurna seratus",
            "pa": "ਸੌ ਦੀ ਪੂਰਤੀ",
            "tk": "Ýüzü doldurýan",
        }
        for lang, phrase in phrases.items():
            assert phrase in by_id["ap04"]["translations"][lang], f"ap04/{lang}"

    def test_ap02_tk_replaces_unfitting_gloss(self):
        cat = AdhkarRepository().load_category("after_prayer")
        by_id = {it["id"]: it for it in cat["items"]}
        text = by_id["ap02"]["translations"]["tk"]
        assert "paýhas" not in text.lower()
        assert "Allahym! Sen Salamsyň" in text

    def test_ap09_ps_id_do_not_add_punishment_gloss(self):
        cat = AdhkarRepository().load_category("after_prayer")
        by_id = {it["id"]: it for it in cat["items"]}
        assert "عذاب" not in by_id["ap09"]["translations"]["ps"]
        assert "siksa" not in by_id["ap09"]["translations"]["id"].lower()

    def test_pa_has_no_footnote_markers(self):
        import re

        cat = AdhkarRepository().load_category("after_prayer")
        by_id = {it["id"]: it for it in cat["items"]}
        for iid in ("aft10", "aft11"):
            text = by_id[iid]["translations"]["pa"]
            assert not re.search(r"\[\d+\]", text), f"{iid}/pa footnote marker"

    def test_delegate_tr_depends_on_language(self):
        path = os.path.join(os.path.dirname(__file__), "..", "qml", "AdhkarItemDelegate.qml")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        start = src.index("function tr(key)")
        end = src.index("function refName", start)
        assert "l10n.currentLanguage" in src[start:end]

    def test_delegate_renders_translation(self):
        path = os.path.join(os.path.dirname(__file__), "..", "qml", "AdhkarItemDelegate.qml")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        assert "itemData.translations" in src
        assert "l10n.currentLanguage" in src
        assert "translationText" in src

class TestMorningEveningLegacyCoverage:
    COVERED = {
        "morning": {"m06", "m07", "m09", "m10", "mor14", "mor15", "mor16", "mor23"},
        "evening": {"e04", "e05", "e06", "e10", "eve14", "eve15", "eve22", "eve28"},
    }

    def test_seeded_items_cover_all_languages(self):
        from backend.i18n import LANGS

        repo = AdhkarRepository()
        for cat_id, ids in self.COVERED.items():
            cat = repo.load_category(cat_id)
            by_id = {it["id"]: it for it in cat["items"]}
            for iid in ids:
                it = by_id[iid]
                missing = set(LANGS) - set(it["translations"])
                assert not missing, f"{iid} missing: {sorted(missing)}"
                assert it["translations"]["ar"] == it["arabic"], iid
                for lang, text in it["translations"].items():
                    assert text.strip(), f"{iid}/{lang} is empty"

    def test_seeded_non_arabic_has_no_arabic_script(self):
        import re

        arabic = re.compile(r"[\u0600-\u06FF]")
        repo = AdhkarRepository()
        for cat_id, ids in self.COVERED.items():
            cat = repo.load_category(cat_id)
            by_id = {it["id"]: it for it in cat["items"]}
            for iid in ids:
                for lang, text in by_id[iid]["translations"].items():
                    if lang in {"ar", "ur", "ps"}:
                        continue
                    assert not arabic.search(text), f"{iid}/{lang}: {text[:80]}"


class TestMorningEveningQuranBatch:
    BATCH = {
        "morning": {
            "m02": "aft11",
            "mor11": ("aft10", 0),
            "mor12": ("aft10", 1),
            "mor13": ("aft10", 2),
        },
        "evening": {
            "e02": "aft11",
            "eve11": ("aft10", 0),
            "eve12": ("aft10", 1),
            "eve13": ("aft10", 2),
        },
    }

    @staticmethod
    def _split_basmala(text):
        best = ""
        for length in range(10, min(220, len(text))):
            prefix = text[:length]
            if text.count(prefix) >= 3 and len(prefix) > len(best):
                best = prefix
        parts = text.split(best)
        assert len(parts) == 4, f"expected 4 segments, got {len(parts)}"
        return [best + parts[i] for i in (1, 2, 3)]

    def test_batch_matches_after_prayer_source(self):
        from backend.i18n import LANGS

        repo = AdhkarRepository()
        ap = repo.load_category("after_prayer")
        ap_by = {it["id"]: it for it in ap["items"]}
        for cat_id, mapping in self.BATCH.items():
            cat = repo.load_category(cat_id)
            by_id = {it["id"]: it for it in cat["items"]}
            for iid, source in mapping.items():
                translations = by_id[iid]["translations"]
                assert set(translations) == set(LANGS), iid
                assert translations["ar"] == by_id[iid]["arabic"], iid
                for lang in LANGS:
                    if lang == "ar":
                        continue
                    if isinstance(source, str):
                        expected = ap_by[source]["translations"][lang]
                    else:
                        source_id, index = source
                        expected = self._split_basmala(ap_by[source_id]["translations"][lang])[index]
                    assert translations[lang] == expected, f"{iid}/{lang}"

    def test_batch_segments_are_distinct(self):
        from backend.i18n import LANGS

        repo = AdhkarRepository()
        for cat_id, mapping in self.BATCH.items():
            cat = repo.load_category(cat_id)
            by_id = {it["id"]: it for it in cat["items"]}
            for lang in LANGS:
                segments = [by_id[iid]["translations"][lang] for iid in mapping if iid.startswith(("mor1", "eve1"))]
                assert len(segments) == len(set(segments)), f"{cat_id}/{lang}: duplicate surah segments"

    def test_batch_non_arabic_has_no_arabic_script(self):
        import re

        arabic = re.compile(r"[\u0600-\u06FF]")
        repo = AdhkarRepository()
        for cat_id, mapping in self.BATCH.items():
            cat = repo.load_category(cat_id)
            by_id = {it["id"]: it for it in cat["items"]}
            for iid in mapping:
                for lang, text in by_id[iid]["translations"].items():
                    if lang in {"ar", "ur", "ps"}:
                        continue
                    assert not arabic.search(text), f"{iid}/{lang}: {text[:80]}"

    def test_batch_meta_lists_items(self):
        for cat_id, mapping in self.BATCH.items():
            path = os.path.join(ASSETS, f"{cat_id}.json")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            meta = data["translation_meta"]
            assert meta["quran_batch"]["items"] == sorted(mapping)
            assert set(mapping) <= set(meta["covered_items"])


class TestMorningEveningHisnPartialBatch:
    """Hisn al-Muslim batch: full-coverage languages plus per-item partial ones."""

    LANGUAGES = ("en", "es", "es_la", "fr", "hi", "id", "it", "ms", "ru", "tk", "tr")

    # Languages whose source only covers part of the batch; the id sets mirror
    # translation_meta.hisn_batch.partial_languages in the JSON files.
    PARTIAL = {
        "de": {
            "morning": {"m03", "m08", "mor19", "mor20"},
            "evening": {"e03", "e07", "e09", "eve18", "eve19"},
        },
        "ur": {
            "morning": {"m03", "m08", "mor19", "mor20"},
            "evening": {"e03", "e07", "e09", "eve18", "eve19"},
        },
        "so": {
            "morning": {"m03", "m04", "mor17", "mor19", "mor20", "mor21",
                        "mor22", "mor26", "mor29"},
            "evening": {"e07", "e08", "eve18", "eve19", "eve21", "eve25"},
        },
        "pa": {
            "morning": {"m03"},
            "evening": {"e07"},
        },
    }

    # ur/ps write in the Arabic script, so the no-Arabic-script check skips them.
    ARABIC_SCRIPT_LANGS = ("ur", "ps")

    ITEMS = {
        "morning": {
            "m03", "m04", "m05", "m08", "mor17", "mor18", "mor19",
            "mor20", "mor21", "mor22", "mor25", "mor26", "mor27", "mor29",
        },
        "evening": {
            "e03", "e07", "e08", "e09", "eve16", "eve17", "eve18",
            "eve19", "eve20", "eve21", "eve24", "eve25", "eve26",
        },
    }

    def _expected_langs(self, cat_id, iid):
        langs = set(self.LANGUAGES)
        for lang, per_cat in self.PARTIAL.items():
            if iid in per_cat.get(cat_id, set()):
                langs.add(lang)
        return langs

    def test_partial_batch_has_languages(self):
        repo = AdhkarRepository()
        for cat_id, ids in self.ITEMS.items():
            cat = repo.load_category(cat_id)
            by_id = {it["id"]: it for it in cat["items"]}
            for iid in ids:
                it = by_id[iid]
                assert it["translations"]["ar"] == it["arabic"], iid
                for lang in self._expected_langs(cat_id, iid):
                    assert it["translations"][lang].strip(), f"{iid}/{lang}"

    def test_partial_batch_has_no_arabic_script(self):
        import re

        arabic = re.compile(r"[\u0600-\u06FF]")
        repo = AdhkarRepository()
        for cat_id, ids in self.ITEMS.items():
            cat = repo.load_category(cat_id)
            by_id = {it["id"]: it for it in cat["items"]}
            for iid in ids:
                for lang in self._expected_langs(cat_id, iid):
                    if lang in self.ARABIC_SCRIPT_LANGS:
                        continue
                    assert not arabic.search(by_id[iid]["translations"][lang]), f"{iid}/{lang}"

    def test_partial_batch_meta(self):
        for cat_id, ids in self.ITEMS.items():
            path = os.path.join(ASSETS, f"{cat_id}.json")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            meta = data["translation_meta"]
            batch = meta["hisn_batch"]
            assert batch["items"] == sorted(ids)
            assert batch["languages"] == sorted(self.LANGUAGES)
            assert not (set(self.LANGUAGES) & set(batch["missing_languages"]))
            assert ids <= set(meta["partial_items"])
            assert not (ids & set(meta["covered_items"]))
            partial = batch.get("partial_languages", {})
            assert set(partial) == set(self.PARTIAL)
            for lang, per_cat in self.PARTIAL.items():
                assert set(partial[lang]) == set(per_cat.get(cat_id, set())), lang
                assert not (set(partial[lang]) & set(batch["languages"])), lang
                assert lang not in batch["missing_languages"], lang
