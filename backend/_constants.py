"""
Shared constants and helper functions used across modules.
Imports only from prayer_calc (PRAYER_ORDER). Safe to import without circular deps.
"""
import logging
from datetime import date

from .prayer_calc import PRAYER_ORDER

logger = logging.getLogger(__name__)

PRAYERS_WITH_AZAN = [k for k in PRAYER_ORDER if k != "sunrise"]
THEME_IDS = ["auto", "light", "dark", "ottoman_gold", "catppuccin_mocha", "catppuccin_latte"]
LANGS = ["ar", "en", "fr", "es", "it", "de", "ru", "tr", "es_la", "pa", "hi", "ur", "tk", "ps", "id", "ms", "so"]
DARK_THEMES = {"dark", "ottoman_gold", "catppuccin_mocha"}


def _display_key(key: str, today: date | None = None) -> str:
    if today is None:
        today = date.today()
    if key == "dhuhr" and today.weekday() == 4:
        return "jumuah"
    return key
