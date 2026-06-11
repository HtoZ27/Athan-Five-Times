"""
Athkar Provider - Manages prayer and general athkar display.
Separated from PrayerEngine for single responsibility.
"""

import logging
from PySide6.QtCore import QObject, Signal, Slot

from .translations import get_athkar
from .i18n import t, t_prayer

logger = logging.getLogger(__name__)


class AthkarProvider(QObject):
    """Provides athkar texts for prayer-specific and general categories."""

    athkarChanged = Signal()
    generalAthkarChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._athkar_text: str = ""
        self._general_text: str = ""
        self._title_text: str = ""

    @Slot(str, str)
    def setPrayerAthkar(self, prayer_key: str, title: str = "") -> None:
        """Set athkar for a specific prayer."""
        texts = get_athkar(prayer_key)
        self._athkar_text = "\n\n".join(texts) if texts else ""
        self._title_text = title or t("athkar_after_prayer")
        self.athkarChanged.emit()

    @Slot(str, str)
    def setGeneralAthkar(self, key: str, title: str = "") -> None:
        """Set general athkar (morning/evening)."""
        texts = get_athkar(key)
        self._general_text = "\n\n".join(texts) if texts else ""
        self._title_text = title or t("athkar_title")
        self.generalAthkarChanged.emit()

    @Slot(result=str)
    def getAthkarText(self) -> str:
        """Get current athkar text (prayer or general)."""
        return self._athkar_text or self._general_text

    @Slot(result=str)
    def getGeneralAthkarText(self) -> str:
        """Get general athkar text."""
        return self._general_text

    @Slot(result=str)
    def getPrayerAthkarText(self) -> str:
        """Get prayer-specific athkar text."""
        return self._athkar_text

    @Slot(result=str)
    def getTitle(self) -> str:
        """Get current athkar title."""
        return self._title_text
