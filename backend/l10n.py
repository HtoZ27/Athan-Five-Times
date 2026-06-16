"""
Language manager — QObject for QML-bound localization.

Thin wrapper around the existing i18n JSON system:
  - isRtl property (reactive QML binding)
  - tr() / trPrayer() slots for QML translate calls
  - languages property for ComboBox models
  - setLanguage() for immediate language switching

Persistence is handled by the caller via the existing JSON settings path.
"""

import logging
from PySide6.QtCore import QObject, Signal, Property, Slot
from ._constants import LANGS
from .i18n import t, t_prayer, set_lang as _set_lang_backend

logger = logging.getLogger(__name__)

_RTL_LANGS = frozenset({"ar", "ur", "ps", "pa"})


def _build_languages() -> list[dict[str, str]]:
    lang_names = {
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
    return [{"code": c, "name": lang_names.get(c, c)} for c in LANGS]


class LanguageManager(QObject):
    """Language control for QML — no persistence; delegates to i18n."""

    languageChanged = Signal()

    def __init__(self, initial_lang: str = "ar", parent=None):
        super().__init__(parent)
        self._lang = initial_lang if initial_lang in LANGS else "ar"
        _set_lang_backend(self._lang)

    # ── properties ────────────────────────────────────────────────────

    @Property(str, notify=languageChanged)
    def currentLanguage(self) -> str:
        return self._lang

    @Property(bool, notify=languageChanged)
    def isRtl(self) -> bool:
        return self._lang in _RTL_LANGS

    @Property("QVariantList", notify=languageChanged)
    def languages(self) -> list[dict[str, str]]:
        return _build_languages()

    # ── slots ──────────────────────────────────────────────────────────

    @Slot(str)
    def setLanguage(self, code: str) -> None:
        if code == self._lang or code not in LANGS:
            return
        logger.info("Language changed: %s → %s", self._lang, code)
        self._lang = code
        _set_lang_backend(code)
        self.languageChanged.emit()

    @Slot(str, result=str)
    def tr(self, key: str) -> str:
        return t(key)

    @Slot(str, result=str)
    def trPrayer(self, key: str) -> str:
        return t_prayer(key)
