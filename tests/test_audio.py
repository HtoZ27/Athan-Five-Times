"""Tests for audio.py - AudioPlayer class."""

import threading
from unittest.mock import patch, MagicMock

from backend.audio import AudioPlayer, AudioConfig


class TestAudioConfig:
    def test_defaults(self):
        cfg = AudioConfig()
        assert cfg.fade_in is True
        assert cfg.fade_duration == 3
        assert cfg.takbeer_only is False
        assert cfg.volume == 1.0

    def test_custom(self):
        cfg = AudioConfig(fade_in=False, fade_duration=1, takbeer_only=True, volume=0.5)
        assert cfg.fade_in is False
        assert cfg.fade_duration == 1
        assert cfg.takbeer_only is True
        assert cfg.volume == 0.5


class TestAudioPlayer:
    def test_init(self):
        p = AudioPlayer()
        assert p._device is None
        assert p._current_gen is None
        assert p._volume == 1.0
        assert p._playback_thread is None

    def test_is_playing_when_not_playing(self):
        p = AudioPlayer()
        assert p.is_playing() is False

    def test_set_volume(self):
        p = AudioPlayer()
        p.set_volume(0.5)
        assert p._volume == 0.5
        p.set_volume(1.5)
        assert p._volume == 1.0
        p.set_volume(-0.5)
        assert p._volume == 0.0

    @patch("backend.audio._MINIAUDIO_AVAILABLE", False)
    def test_play_skips_when_no_miniaudio(self):
        p = AudioPlayer()
        callback = MagicMock()
        p.play("/nonexistent.mp3", on_done=callback)
        callback.assert_called_once()

    @patch("backend.audio._MINIAUDIO_AVAILABLE", False)
    def test_stop_noop_when_no_miniaudio(self):
        p = AudioPlayer()
        p.stop()
        assert p.is_playing() is False

    @patch("backend.audio._MINIAUDIO_AVAILABLE", False)
    def test_preload_noop(self):
        p = AudioPlayer()
        p.preload("/nonexistent.mp3")

    def test_lock_is_rlock(self):
        p = AudioPlayer()
        assert isinstance(p._lock, type(threading.RLock()))
