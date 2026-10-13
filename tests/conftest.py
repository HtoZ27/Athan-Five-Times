import os

import tempfile
import pytest
import backend.settings as S


@pytest.fixture(autouse=True, scope="session")
def _qt_offscreen():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def isolate_settings():
    tmp = tempfile.mkdtemp(prefix="athan_test_")
    old_dir = S.SETTINGS_DIR
    old_file = S.SETTINGS_FILE
    old_backup = S.SETTINGS_BACKUP
    old_autostart_dir = S.AUTOSTART_DIR
    old_autostart_file = S.AUTOSTART_FILE

    S.SETTINGS_DIR = tmp
    S.SETTINGS_FILE = os.path.join(tmp, "settings.json")
    S.SETTINGS_BACKUP = S.SETTINGS_FILE + ".bak"
    S.AUTOSTART_DIR = os.path.join(tmp, "autostart")
    S.AUTOSTART_FILE = os.path.join(S.AUTOSTART_DIR, "athan-five-times.desktop")
    yield
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)
    S.SETTINGS_DIR = old_dir
    S.SETTINGS_FILE = old_file
    S.SETTINGS_BACKUP = old_backup
    S.AUTOSTART_DIR = old_autostart_dir
    S.AUTOSTART_FILE = old_autostart_file


@pytest.fixture(autouse=True)
def setup_lang():
    from backend.i18n import set_lang

    set_lang("ar")
    yield
    set_lang("ar")
