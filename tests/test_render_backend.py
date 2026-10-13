"""Render backend/loop setting: defaults, env precedence, invalid fallback."""

import os


class TestRenderDefaults:
    def test_schema_defaults_auto(self):
        from backend.settings import DEFAULT_SETTINGS

        assert DEFAULT_SETTINGS.get("render_backend") == "auto"
        assert DEFAULT_SETTINGS.get("render_loop") == "auto"

    def test_update_accepts_values(self):
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from backend.backend_controller import PrayerEngine

        e = PrayerEngine()
        try:
            e.updateSetting("render_backend", "software")
            assert e.getSetting("render_backend") == "software"
            e.updateSetting("render_loop", "threaded")
            assert e.getSetting("render_loop") == "threaded"
        finally:
            e.cleanup()


class TestRenderEnvApply:
    def test_software_sets_env(self, tmp_path, monkeypatch):
        import json

        cfg = tmp_path / "settings.json"
        cfg.write_text(
            json.dumps({"render_backend": "software", "render_loop": "basic"}), encoding="utf-8"
        )
        monkeypatch.delenv("QT_QUICK_BACKEND", raising=False)
        monkeypatch.delenv("QSG_RENDER_LOOP", raising=False)
        monkeypatch.setattr("backend.main.SETTINGS_FILE", str(cfg))
        import backend.main as M

        M.apply_render_env()
        assert os.environ.get("QT_QUICK_BACKEND") == "software"
        assert os.environ.get("QSG_RENDER_LOOP") == "basic"
        monkeypatch.delenv("QT_QUICK_BACKEND", raising=False)
        monkeypatch.delenv("QSG_RENDER_LOOP", raising=False)

    def test_user_export_wins(self, tmp_path, monkeypatch):
        import json

        cfg = tmp_path / "settings.json"
        cfg.write_text(json.dumps({"render_backend": "software"}), encoding="utf-8")
        monkeypatch.setenv("QT_QUICK_BACKEND", "opengl")
        monkeypatch.setattr("backend.main.SETTINGS_FILE", str(cfg))
        import backend.main as M

        M.apply_render_env()
        assert os.environ.get("QT_QUICK_BACKEND") == "opengl"

    def test_invalid_falls_back_silently(self, tmp_path, monkeypatch):
        import json

        cfg = tmp_path / "settings.json"
        cfg.write_text(
            json.dumps({"render_backend": "vulkan9", "render_loop": "turbo"}), encoding="utf-8"
        )
        monkeypatch.delenv("QT_QUICK_BACKEND", raising=False)
        monkeypatch.delenv("QSG_RENDER_LOOP", raising=False)
        monkeypatch.setattr("backend.main.SETTINGS_FILE", str(cfg))
        import backend.main as M

        M.apply_render_env()
        assert "QT_QUICK_BACKEND" not in os.environ
        assert "QSG_RENDER_LOOP" not in os.environ

    def test_missing_file_is_auto(self, tmp_path, monkeypatch):
        monkeypatch.delenv("QT_QUICK_BACKEND", raising=False)
        monkeypatch.setattr("backend.main.SETTINGS_FILE", str(tmp_path / "none.json"))
        import backend.main as M

        M.apply_render_env()
        assert "QT_QUICK_BACKEND" not in os.environ
