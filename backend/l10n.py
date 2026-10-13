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
from ._constants import LANGS, LANG_NAMES
from .i18n import set_lang as _set_lang_backend

logger = logging.getLogger(__name__)

_RTL_LANGS = frozenset({"ar", "ur", "ps", "pa"})


def _build_languages() -> list[dict[str, str]]:
    return [{"code": c, "name": LANG_NAMES.get(c, c)} for c in LANGS]


class LanguageManager(QObject):
    """Language control for QML — no persistence; delegates to i18n."""

    languageChanged = Signal()

    def __init__(self, initial_lang: str = "ar", parent=None):
        super().__init__(parent)
        self._lang = initial_lang if initial_lang in LANGS else "ar"
        _set_lang_backend(self._lang)

    @Property(str, notify=languageChanged)
    def currentLanguage(self) -> str:
        return self._lang

    @Property(bool, notify=languageChanged)
    def isRtl(self) -> bool:
        return self._lang in _RTL_LANGS

    @Property("QVariantList", notify=languageChanged)
    def languages(self) -> list[dict[str, str]]:
        return _build_languages()

    @Slot(str)
    def setLanguage(self, code: str) -> None:
        if code == self._lang or code not in LANGS:
            return
        logger.info("Language changed: %s → %s", self._lang, code)
        self._lang = code
        _set_lang_backend(code)
        self.languageChanged.emit()
