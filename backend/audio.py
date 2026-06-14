
"""
Audio playback for the Azan call to prayer.
Uses miniaudio for audio playback with fallback for headless environments.
Refactored to use class-based approach instead of global state.
"""

import array
import logging
import os
import platform
import threading
from dataclasses import dataclass
from typing import Optional, Callable
from functools import lru_cache

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
    """Thread-safe audio player for Azan playback."""

    def __init__(self, max_cached: int = 2):
        self._current_device = None
        self._current_gen = None
        self._current_lock = threading.Lock()
        self._play_lock = threading.RLock()  # RLock for reentrancy safety
        self._stop_event = threading.Event()
        self._done_event = threading.Event()
        self._volume = 1.0
        self._playback_thread: threading.Thread | None = None
        # Device configuration for reuse
        self._device_config: tuple | None = None  # (sample_rate, nchannels, format)

    @lru_cache(maxsize=2)
    def _get_decoded(self, path: str) -> tuple:
        """Return cached decoded audio or decode and cache it. Uses LRU cache."""
        if not _MINIAUDIO_AVAILABLE:
            raise RuntimeError("miniaudio not available")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Audio not found: {path}")
        decoded = miniaudio.decode_file(
            path,
            output_format=miniaudio.SampleFormat.SIGNED16,
        )
        return (decoded.samples, decoded.sample_rate, decoded.nchannels)

    def preload(self, path: str) -> None:
        """Preload audio in background thread."""
        def _load():
            try:
                self._get_decoded(path)
                logger.debug("Preloaded audio: %s", path)
            except (FileNotFoundError, OSError, ValueError, RuntimeError) as exc:
                logger.warning("Could not preload audio %s: %s", path, exc)
        threading.Thread(target=_load, daemon=True).start()

    def play(
        self,
        azan_path: str,
        config: Optional[AudioConfig] = None,
        on_done: Optional[Callable] = None,
        stop_flag: Optional[threading.Event] = None,
    ) -> None:
        """Play azan with given configuration."""
        if not _MINIAUDIO_AVAILABLE:
            logger.warning("Audio playback skipped: miniaudio unavailable")
            if on_done:
                on_done()
            return

        config = config or AudioConfig()
        self.stop()
        self._stop_event.clear()

        # Capture old thread reference before starting new one
        _old_thread = self._playback_thread

        def _play():
            # Join old thread to prevent leak
            if _old_thread is not None and _old_thread is not threading.current_thread():
                _old_thread.join(timeout=3.0)
            # Use RLock with timeout - if we can't acquire, another playback is in progress
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
                    return

                samples, sample_rate, nchannels = self._get_decoded(azan_path)
                fade_frames = int(config.fade_duration * sample_rate) if config.fade_in else 0
                takbeer_frames = (
                    int(3.0 * sample_rate) if config.takbeer_only else None
                )
                frame_counter = 0
                sample_offset = 0
                volume = config.volume

                def _stream():
                    nonlocal frame_counter, sample_offset
                    try:
                        # First chunk: use default frame count (1024)
                        chunk = array.array("h", samples[:1024 * nchannels])
                        sample_offset += len(chunk)
                        frame_counter += 1024
                        nframes = yield chunk.tobytes()
                        if nframes is None:
                            nframes = 1024

                        # Subsequent chunks: use nframes from device
                        while sample_offset < len(samples):
                            if self._stop_event.is_set() or (
                                stop_flag and stop_flag.is_set()
                            ):
                                return

                            avail_frames = (len(samples) - sample_offset) // nchannels
                            read_frames = min(nframes, avail_frames)
                            if read_frames <= 0:
                                return
                            chunk_samples = read_frames * nchannels
                            chunk = array.array("h", samples[sample_offset:sample_offset + chunk_samples])
                            sample_offset += chunk_samples
                            frames = read_frames

                            if fade_frames > 0 and frame_counter < fade_frames:
                                for i in range(frames):
                                    global_idx = frame_counter + i
                                    if global_idx < fade_frames:
                                        scale = global_idx / fade_frames
                                        for c in range(nchannels):
                                            chunk[i * nchannels + c] = int(
                                                chunk[i * nchannels + c] * scale
                                            )

                            if volume < 1.0:
                                for i in range(len(chunk)):
                                    chunk[i] = int(chunk[i] * volume)

                            frame_counter += frames

                            if takbeer_frames is not None and frame_counter >= takbeer_frames:
                                remaining = takbeer_frames - (frame_counter - frames)
                                if remaining > 0:
                                    chunk = chunk[:remaining * nchannels]
                                    yield chunk.tobytes()
                                return

                            nframes = yield chunk.tobytes()
                            if nframes is None:
                                nframes = 1024
                    finally:
                        self._done_event.set()

                gen = _stream()
                next(gen)
                if self._stop_event.is_set() or (stop_flag and stop_flag.is_set()):
                    return

                # Determine device configuration for reuse
                new_config = (sample_rate, nchannels, miniaudio.SampleFormat.SIGNED16)

                with self._current_lock:
                    self._current_gen = gen
                    # Reuse device if configuration matches
                    if self._current_device is not None and self._device_config == new_config:
                        device = self._current_device
                    else:
                        device = miniaudio.PlaybackDevice(
                            sample_rate=sample_rate,
                            nchannels=nchannels,
                            output_format=miniaudio.SampleFormat.SIGNED16,
                            buffersize_msec=500,
                        )
                        self._current_device = device
                        self._device_config = new_config
                    device.start(gen)

                self._done_event.wait()

            except (RuntimeError, ValueError, AttributeError, KeyError, TypeError):
                logger.exception("Playback error")
                self._done_event.set()
            finally:
                with self._current_lock:
                    self._current_device = None
                    self._current_gen = None
                if on_done:
                    try:
                        on_done()
                    except Exception:
                        logger.exception("on_done callback failed")
                # Release the lock - using try/finally ensures it's always released
                try:
                    self._play_lock.release()
                except RuntimeError:
                    # Lock wasn't locked (shouldn't happen with RLock, but safety)
                    pass

        self._playback_thread = threading.Thread(target=_play, daemon=True)
        self._playback_thread.start()

    def stop(self, wait: bool = True, timeout: float = 2.0) -> None:
        """Stop current playback.

        Args:
            wait: If True, wait for playback thread to finish
            timeout: Maximum time to wait for playback thread to finish
        """
        if not _MINIAUDIO_AVAILABLE:
            return
        self._stop_event.set()
        with self._current_lock:
            gen = self._current_gen
            dev = self._current_device
            self._current_gen = None
            self._current_device = None
        if gen is not None:
            try:
                gen.close()
            except (AttributeError, RuntimeError, OSError) as exc:
                logger.debug("Error closing audio generator: %s", exc)
        if dev is not None:
            try:
                dev.stop()
            except (AttributeError, RuntimeError, OSError) as exc:
                logger.debug("Error stopping audio device: %s", exc)

        # Wait for playback thread to finish and release the lock
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
        if self._done_event.is_set():
            return False
        if self._play_lock.locked():
            return True
        if self._playback_thread is not None and self._playback_thread.is_alive():
            return True
        return False

    def clear_cache(self) -> None:
        """Clear the decoded audio cache to free memory."""
        self._get_decoded.cache_clear()
        logger.debug("Audio cache cleared")

    def set_volume(self, vol: float) -> None:
        """Set global volume."""
        self._volume = max(0.0, min(1.0, vol))
        logger.debug("Volume set to %.2f", self._volume)


# Global instance for backward compatibility
_global_player = AudioPlayer()


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


def clear_cache() -> None:
    """Clear cache (backward compatibility)."""
    _global_player.clear_cache()


def set_volume(vol: float) -> None:
    """Set volume (backward compatibility)."""
    _global_player.set_volume(vol)


def is_audio_available() -> bool:
    """Check if audio playback is available (miniaudio + audio backend)."""
    if not _MINIAUDIO_AVAILABLE:
        return False
    # Check for common audio backends on Linux
    if platform.system() == "Linux":
        # Check PulseAudio/PipeWire
        if os.environ.get("PULSE_SERVER") or os.path.exists("/run/user/%d/pulse/native" % os.getuid()):
            return True
        if os.environ.get("PIPEWIRE_RUNTIME_DIR") or os.path.exists("/run/user/%d/pipewire-0" % os.getuid()):
            return True
        # Check ALSA
        if os.path.exists("/dev/snd/pcmC0D0p"):
            return True
    return _MINIAUDIO_AVAILABLE
