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
    def test_ten_categories(self):
        repo = AdhkarRepository()
        index = repo.get_index()
        assert len(index) == 10
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
        }
        for c in AdhkarRepository().get_index():
            icon = c.get("icon") or "dua"
            assert icon in known, c["id"]
            assert os.path.isfile(os.path.join(icons_dir, icon + ".png")), icon


class TestCategories:
    def test_morning_ten_items_structured(self):
        cat = AdhkarRepository().load_category("morning")
        assert len(cat["items"]) == 10
        for it in cat["items"]:
            assert it["arabic"]
            assert it["count"] >= 1
            assert it["reference_id"]

    def test_after_prayer_nine_items(self):
        cat = AdhkarRepository().load_category("after_prayer")
        assert len(cat["items"]) == 9

    def test_unknown_category_raises(self):
        with pytest.raises(KeyError):
            AdhkarRepository().load_category("nope")

    def test_lru_eviction(self):
        repo = AdhkarRepository(max_cache_size=2)
        repo.load_category("morning")
        repo.load_category("evening")
        repo.load_category("sleep")
        assert set(repo._cache.keys()) == {"evening", "sleep"}

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
            assert len(texts) == 9
            assert all(isinstance(t, str) and t for t in texts)

    def test_morning_evening(self):
        assert len(get_structured_texts("morning")) == 10
        assert len(get_structured_texts("evening")) == 10

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
