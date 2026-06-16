
"""
Audio playback for the Azan call to prayer.
Uses miniaudio streaming (stream_file) to avoid loading entire MP3 into RAM.
Singleton PlaybackDevice reused across calls for efficiency.
"""

import array
import logging
import os
import platform
import threading
from dataclasses import dataclass
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Try to import miniaudio, handle headless environments gracefully
try:
    import miniaudio
    _MINIAUDIO_AVAILABLE = True
except (ImportError, OSError, ModuleNotFoundError) as exc:
    logger.warning("miniaudio not available: %s. Audio playback disabled.", exc)
    miniaudio = None
    _MINIAUDIO_AVAILABLE = False


@dataclass
class AudioConfig:
    """Configuration for audio playback."""
    fade_in: bool = True
    fade_duration: int = 3
    takbeer_only: bool = False
    volume: float = 1.0


class AudioPlayer:
    """Thread-safe streaming audio player for Azan playback.

    Singleton PlaybackDevice — created once, reused across calls.
    Uses miniaudio.stream_file() to decode on the fly — no full decode into RAM.
    """

    def __init__(self):
        self._device = None
        self._device_config: tuple | None = None
        self._current_gen = None
        self._current_lock = threading.Lock()
        self._play_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._done_event = threading.Event()
        self._volume = 1.0
        self._playback_thread: threading.Thread | None = None

    def _ensure_device(self, sample_rate: int, nchannels: int):
        """Return singleton device, creating it on first call.
        If format changes, old device is stopped and replaced.
        """
        new_config = (sample_rate, nchannels, miniaudio.SampleFormat.SIGNED16)
        if self._device is not None and self._device_config == new_config:
            return self._device
        if self._device is not None:
            try:
                self._device.stop()
            except Exception:
                pass
            self._device = None
        self._device = miniaudio.PlaybackDevice(
            sample_rate=sample_rate,
            nchannels=nchannels,
            output_format=miniaudio.SampleFormat.SIGNED16,
            buffersize_msec=500,
        )
        self._device_config = new_config
        return self._device

    def _create_stream(self, path: str, config: AudioConfig,
                        stop_flag: Optional[threading.Event] = None):
        """Create a processed streaming generator from a file.
        Decodes in chunks — never loads the entire file into RAM.
        """
        info = miniaudio.get_file_info(path)
        sample_rate = info.sample_rate
        nchannels = info.nchannels

        file_stream = miniaudio.stream_file(
            path,
            sample_rate=sample_rate,
            nchannels=nchannels,
            output_format=miniaudio.SampleFormat.SIGNED16,
        )

        fade_frames = int(config.fade_duration * sample_rate) if config.fade_in else 0
        takbeer_frames = int(3.0 * sample_rate) if config.takbeer_only else None
        frame_counter = 0

        def _stream():
            nonlocal frame_counter
            try:
                for raw_chunk in file_stream:
                    if self._stop_event.is_set() or (stop_flag and stop_flag.is_set()):
                        return

                    chunk = array.array("h", raw_chunk)
                    frames = len(chunk) // nchannels

                    if frame_counter < fade_frames:
                        for i in range(min(frames, fade_frames - frame_counter)):
                            scale = (frame_counter + i) / fade_frames
                            for c in range(nchannels):
                                chunk[i * nchannels + c] = int(
                                    chunk[i * nchannels + c] * scale
                                )

                    if config.volume < 1.0:
                        for i in range(len(chunk)):
                            chunk[i] = int(chunk[i] * config.volume)

                    if takbeer_frames is not None:
                        if frame_counter + frames >= takbeer_frames:
                            remaining = takbeer_frames - frame_counter
                            if remaining > 0:
                                chunk = chunk[:remaining * nchannels]
                                yield chunk.tobytes()
                            return

                    frame_counter += frames
                    nframes = yield chunk.tobytes()
                    if nframes is not None:
                        pass
            finally:
                self._done_event.set()

        return _stream(), sample_rate, nchannels

    def preload(self, path: str) -> None:
        """Preload — no-op with streaming (file is read on demand)."""
        if not _MINIAUDIO_AVAILABLE:
            return
        if not os.path.isfile(path):
            logger.warning("Audio file not found for preload: %s", path)

    def play(
        self,
        azan_path: str,
        config: Optional[AudioConfig] = None,
        on_done: Optional[Callable] = None,
        stop_flag: Optional[threading.Event] = None,
    ) -> None:
        """Play azan with given configuration using streaming + singleton device."""
        if not _MINIAUDIO_AVAILABLE:
            logger.warning("Audio playback skipped: miniaudio unavailable")
            if on_done:
                on_done()
            return

        config = config or AudioConfig()
        self.stop()
        self._stop_event.clear()

        _old_thread = self._playback_thread

        def _play():
            if _old_thread is not None and _old_thread is not threading.current_thread():
                _old_thread.join(timeout=3.0)

            acquired = self._play_lock.acquire(timeout=5.0)
            if not acquired:
                logger.warning("Timed out waiting for audio lock - another playback in progress")
                if on_done:
                    try:
                        on_done()
                    except Exception:
                        logger.exception("on_done callback failed")
                return

            try:
                self._done_event.clear()
                if not os.path.isfile(azan_path):
                    logger.warning("Azan file not found: %s", azan_path)
                    self._done_event.set()
                    return

                gen, sample_rate, nchannels = self._create_stream(azan_path, config, stop_flag)
                next(gen)

                if self._stop_event.is_set() or (stop_flag and stop_flag.is_set()):
                    gen.close()
                    self._done_event.set()
                    return

                device = self._ensure_device(sample_rate, nchannels)

                with self._current_lock:
                    self._current_gen = gen

                try:
                    device.stop()
                except Exception:
                    pass

                # Race guard: stop() may have closed gen between _current_gen and device.stop()
                if self._stop_event.is_set() or (stop_flag and stop_flag.is_set()):
                    with self._current_lock:
                        self._current_gen = None
                    gen.close()
                    self._done_event.set()
                    return

                device.start(gen)

                if not self._done_event.wait(timeout=300.0):
                    logger.warning("Playback timed out after 300s, forcing stop")
                    with self._current_lock:
                        if self._current_gen is not None:
                            try:
                                self._current_gen.close()
                            except Exception:
                                pass
                        self._current_gen = None
                    try:
                        device.stop()
                    except Exception:
                        pass

            except (RuntimeError, ValueError, AttributeError, KeyError, TypeError):
                logger.exception("Playback error")
            finally:
                _cb = on_done
                with self._current_lock:
                    self._current_gen = None
                self._done_event.set()
                if _cb:
                    try:
                        _cb()
                    except Exception:
                        logger.exception("on_done callback failed")
                try:
                    self._play_lock.release()
                except RuntimeError as exc:
                    logger.debug("play_lock release failed (expected): %s", exc)

        self._playback_thread = threading.Thread(target=_play, daemon=True)
        self._playback_thread.start()

    def stop(self, wait: bool = True, timeout: float = 2.0) -> None:
        """Stop current playback. Singleton device is stopped but kept for reuse."""
        if not _MINIAUDIO_AVAILABLE:
            return
        self._stop_event.set()
        with self._current_lock:
            gen = self._current_gen
            self._current_gen = None
        if gen is not None:
            try:
                gen.close()
            except (AttributeError, RuntimeError, OSError) as exc:
                logger.debug("Error closing audio generator: %s", exc)
        if self._device is not None:
            try:
                self._device.stop()
            except (AttributeError, RuntimeError, OSError) as exc:
                logger.debug("Error stopping audio device: %s", exc)

        if wait and self._playback_thread is not None and self._playback_thread.is_alive():
            if self._playback_thread is threading.current_thread():
                logger.debug("stop() called from playback thread, skipping self-join")
            else:
                self._playback_thread.join(timeout=timeout)
                if self._playback_thread.is_alive():
                    logger.warning("Playback thread did not finish within timeout")

    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        if not _MINIAUDIO_AVAILABLE:
            return False
        return not self._done_event.is_set() and (
            self._play_lock.locked() or
            (self._playback_thread is not None and self._playback_thread.is_alive())
        )

    def set_volume(self, vol: float) -> None:
        """Set global volume."""
        self._volume = max(0.0, min(1.0, vol))
        logger.debug("Volume set to %.2f", self._volume)


# Global instance for backward compatibility
_global_player = AudioPlayer()


def clear_cache() -> None:
    """Clear cache — no-op with streaming (no decoded cache)."""
    logger.debug("Audio cache clear: no-op (streaming mode)")


def preload_audio(path: str) -> None:
    """Preload audio (backward compatibility)."""
    _global_player.preload(path)


def play_azan(
    azan_path: str,
    fade_in: bool = True,
    fade_duration: int = 3,
    takbeer_only: bool = False,
    on_done: Optional[Callable] = None,
    stop_flag: Optional[threading.Event] = None,
    backend=None,
) -> None:
    """Play azan (backward compatibility)."""
    config = AudioConfig(
        fade_in=fade_in,
        fade_duration=fade_duration,
        takbeer_only=takbeer_only,
    )
    _global_player.play(azan_path, config, on_done, stop_flag)


def stop_azan() -> None:
    """Stop azan (backward compatibility)."""
    _global_player.stop()


def is_playing() -> bool:
    """Check if playing (backward compatibility)."""
    return _global_player.is_playing()


def set_volume(vol: float) -> None:
    """Set volume (backward compatibility)."""
    _global_player.set_volume(vol)


def is_audio_available() -> bool:
    """Check if audio playback is available (miniaudio + audio backend)."""
    if not _MINIAUDIO_AVAILABLE:
        return False
    if platform.system() == "Linux":
        if os.environ.get("PULSE_SERVER") or os.path.exists("/run/user/%d/pulse/native" % os.getuid()):
            return True
        if os.environ.get("PIPEWIRE_RUNTIME_DIR") or os.path.exists("/run/user/%d/pipewire-0" % os.getuid()):
            return True
        if os.path.exists("/dev/snd/pcmC0D0p"):
            return True
    return _MINIAUDIO_AVAILABLE
