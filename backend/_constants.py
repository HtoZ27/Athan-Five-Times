"""
Shared constants and helper functions used across modules.
Imports only from prayer_calc (PRAYER_ORDER). Safe to import without circular deps.
"""

from datetime import date

from .prayer_calc import PRAYER_ORDER

PRAYERS_WITH_AZAN = [k for k in PRAYER_ORDER if k != "sunrise"]
THEME_IDS = ["auto", "light", "dark", "ottoman_gold", "catppuccin_mocha", "catppuccin_latte"]
LANGS = [
    "ar",
    "en",
    "fr",
    "es",
    "it",
    "de",
    "ru",
    "tr",
    "es_la",
    "pa",
    "hi",
    "ur",
    "tk",
    "ps",
    "id",
    "ms",
    "so",
]
LANG_NAMES = {
    "ar": "العربية",
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "es_la": "Español (Latinoamérica)",
    "it": "Italiano",
    "de": "Deutsch",
    "ru": "Русский",
    "tr": "Türkçe",
    "pa": "ਪੰਜਾਬੀ",
    "hi": "हिन्दी",
    "ur": "اردو",
    "tk": "Türkmençe",
    "ps": "پښتو",
    "id": "Bahasa Indonesia",
    "ms": "Bahasa Melayu",
    "so": "Soomaali",
}
DARK_THEMES = {"dark", "ottoman_gold", "catppuccin_mocha"}


def _display_key(key: str, today: date | None = None) -> str:
    if today is None:
        today = date.today()
    if key == "dhuhr" and today.weekday() == 4:
        return "jumuah"
    return key
