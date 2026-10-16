"""Tests for the structured adhkar library (backend/adhkar_repo.py)."""

import glob
import json
import os

import pytest

from backend.adhkar_repo import (
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
        assert len(cat["items"]) == 27
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


class TestLegacyCompat:
    def test_prayer_keys_map_to_after_prayer(self):
        for key in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
            texts = get_structured_texts(key)
            assert len(texts) == 12
            assert all(isinstance(t, str) and t for t in texts)

    def test_morning_evening(self):
        assert len(get_structured_texts("morning")) == 27
        assert len(get_structured_texts("evening")) == 26

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
        assert total == 373, total


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
        icons_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "assets", "adhkar_icons")
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
