import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest

@pytest.fixture(autouse=True)
def setup_lang():
    from backend.i18n import set_lang, LANGS
    set_lang("ar")
    yield
    set_lang("ar")
