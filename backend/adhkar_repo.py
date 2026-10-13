"""
Structured adhkar library (ported from the Dart sibling's assets/data/adhkar/).

Single source of truth for all remembrance texts: 10 JSON categories with
per-item repetition counts and source references. Loaded lazily per
category with structural validation and a small LRU cache.
"""

import json
import logging
import os
from collections import OrderedDict
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BASE_DIR: str = os.path.join(os.path.dirname(__file__), "assets", "adhkar")
INDEX_FILE: str = os.path.join(BASE_DIR, "index.json")

_MAX_CACHE_SIZE = 20


class AdhkarValidationError(ValueError):
    """Raised when an adhkar JSON file fails structural validation."""


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_index(data: Any) -> None:
    errors: List[str] = []
    cats = data.get("categories") if isinstance(data, dict) else None
    if not cats:
        errors.append("missing or empty categories list")
    for c in cats or []:
        if not isinstance(c, dict):
            errors.append("category entry is not a map")
            continue
        if not c.get("id"):
            errors.append("index: category missing id")
        if not c.get("asset"):
            errors.append("index: %s missing asset" % c.get("id"))
    if errors:
        raise AdhkarValidationError("; ".join(errors))


def validate_category(data: Any) -> None:
    errors: List[str] = []
    if not isinstance(data, dict) or not data.get("id"):
        errors.append("missing id")
    items = data.get("items") if isinstance(data, dict) else None
    if not items:
        errors.append("missing or empty items")
    for item in items or []:
        if not isinstance(item, dict):
            errors.append("item is not a map")
            continue
        if not item.get("arabic"):
            errors.append("%s: missing arabic" % item.get("id", "?"))
        if not item.get("reference_id"):
            errors.append("%s: missing reference_id" % item.get("id", "?"))
    if errors:
        raise AdhkarValidationError("; ".join(errors))


def _asset_path(entry_asset: str) -> str:
    """Remap a Dart-style asset path to this package's assets dir."""
    return os.path.join(BASE_DIR, os.path.basename(entry_asset))


class AdhkarRepository:
    """Lazy, validated, LRU-cached access to the adhkar JSON library."""

    def __init__(self, base_dir: str = BASE_DIR, max_cache_size: int = _MAX_CACHE_SIZE):
        self._base_dir = base_dir
        self._index_file = os.path.join(base_dir, "index.json")
        self._max_cache_size = max_cache_size
        self._index: Optional[List[Dict[str, Any]]] = None
        self._cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

    def get_index(self) -> List[Dict[str, Any]]:
        if self._index is None:
            data = _read_json(self._index_file)
            validate_index(data)
            entries = sorted(data["categories"], key=lambda c: c.get("order", 0))
            self._index = [
                {
                    "id": c["id"],
                    "name_ar": c.get("name_ar", c["id"]),
                    "name_en": c.get("name_en", c["id"]),
                    "icon": c.get("icon", "dua"),
                    "order": c.get("order", 0),
                    "asset": c.get("asset", ""),
                }
                for c in entries
            ]
        return list(self._index)

    def load_category(self, category_id: str) -> Dict[str, Any]:
        if category_id in self._cache:
            self._cache.move_to_end(category_id)
            return self._cache[category_id]
        index = {c["id"]: c for c in self.get_index()}
        entry = index.get(category_id)
        if entry is None:
            raise KeyError("Unknown adhkar category: %s" % category_id)
        data = _read_json(_asset_path(entry["asset"]))
        validate_category(data)
        category = {
            "id": data["id"],
            "name_ar": data.get("name_ar", data["id"]),
            "name_en": data.get("name_en", data["id"]),
            "icon": data.get("icon", "dua"),
            "total": data.get("total", len(data["items"])),
            "items": [
                {
                    "id": it.get("id", ""),
                    "arabic": it["arabic"],
                    "count": it.get("count", 1),
                    "reference_id": it.get("reference_id", ""),
                    "reference_detail": it.get("reference_detail", ""),
                    "virtue": it.get("virtue"),
                    "translation": it.get("translation"),
                    "tags": it.get("tags", []),
                }
                for it in data["items"]
            ],
        }
        if len(self._cache) >= self._max_cache_size:
            self._cache.popitem(last=False)
        self._cache[category_id] = category
        return category

    def clear_cache(self) -> None:
        self._cache.clear()
        self._index = None


_default_repo = AdhkarRepository()


def get_repository() -> AdhkarRepository:
    return _default_repo


_LEGACY_KEY_MAP = {
    "fajr": "after_prayer",
    "dhuhr": "after_prayer",
    "asr": "after_prayer",
    "maghrib": "after_prayer",
    "isha": "after_prayer",
    "morning": "morning",
    "evening": "evening",
}


def get_structured_texts(legacy_key: str) -> List[str]:
    """Compat: arabic strings for a legacy flat key, sourced from the library."""
    category_id = _LEGACY_KEY_MAP.get(legacy_key)
    if category_id is None:
        return []
    try:
        category = _default_repo.load_category(category_id)
    except (OSError, ValueError, KeyError) as exc:
        logger.warning("Adhkar library miss for %s: %s", legacy_key, exc)
        return []
    return [it["arabic"] for it in category["items"]]
