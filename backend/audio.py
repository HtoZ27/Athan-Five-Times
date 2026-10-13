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


OUTPUT_SAMPLE_RATE = 48000
OUTPUT_CHANNELS = 2


class AudioPlayer:
    """Thread-safe streaming audio player for Azan playback.

    Singleton PlaybackDevice — created once, reused across calls.
    Uses miniaudio.stream_file() to decode on the fly — no full decode into RAM.
    """

    def __init__(self):
        self._device = None
        self._device_config: tuple | None = None
        self._current_gen = None
        self._lock = threading.RLock()
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

    def _create_stream(
        self, path: str, config: AudioConfig, stop_flag: Optional[threading.Event] = None
    ):
        """Create a processed streaming generator from a file.
        Decodes in chunks — never loads the entire file into RAM.
        Output is always OUTPUT_SAMPLE_RATE/OUTPUT_CHANNELS (converted in
        C by miniaudio) regardless of the source file's format.
        """
        file_stream = miniaudio.stream_file(
            path,
            sample_rate=OUTPUT_SAMPLE_RATE,
            nchannels=OUTPUT_CHANNELS,
            output_format=miniaudio.SampleFormat.SIGNED16,
        )
        sample_rate, nchannels = OUTPUT_SAMPLE_RATE, OUTPUT_CHANNELS

        fade_frames = int(config.fade_duration * sample_rate) if config.fade_in else 0
        takbeer_frames = int(3.0 * sample_rate) if config.takbeer_only else None
        frame_counter = 0  # decoded frames processed (fade ramp position)
        emitted_frames = 0  # frames handed to the device (takbeer cap)
        frame_size = nchannels * 2  # bytes per S16 frame
        pending = bytearray()
        src_exhausted = False

        def _pull():
            """Decode and process one decoder chunk into `pending`."""
            nonlocal frame_counter, src_exhausted
            try:
                raw_chunk = next(file_stream)
            except StopIteration:
                src_exhausted = True
                return
            chunk = array.array("h", raw_chunk)
            frames = len(chunk) // nchannels
            if frame_counter < fade_frames or config.volume < 1.0:
                vol = config.volume
                fade_left = fade_frames - frame_counter
                for i in range(frames):
                    if i < fade_left:
                        scale = vol * (frame_counter + i) / fade_frames
                    else:
                        scale = vol
                    if scale != 1.0:
                        base = i * nchannels
                        for c in range(nchannels):
                            chunk[base + c] = int(chunk[base + c] * scale)
            frame_counter += frames
            pending.extend(chunk.tobytes())

        def _stream():
            nonlocal emitted_frames, src_exhausted
            try:
                need = yield b""
                while True:
                    if self._stop_event.is_set() or (stop_flag and stop_flag.is_set()):
                        return
                    if not isinstance(need, int) or need <= 0:
                        need = 4096
                    if takbeer_frames is not None:
                        remaining_total = takbeer_frames - emitted_frames
                        if remaining_total <= 0:
                            return
                        need = min(need, remaining_total)
                    while len(pending) < need * frame_size and not src_exhausted:
                        _pull()
                        if self._stop_event.is_set() or (stop_flag and stop_flag.is_set()):
                            return
                    if not pending:
                        return  # clean end-of-stream -> device stops
                    take = min(len(pending), need * frame_size)
                    out = bytes(pending[:take])
                    del pending[:take]
                    if len(out) < need * frame_size:
                        out += b"\x00" * (need * frame_size - len(out))
                        emitted_frames += take // frame_size
                        yield out
                        return
                    emitted_frames += need
                    need = yield out
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
        self.stop(wait=True, timeout=3.0)
        self._stop_event.clear()

        def _play():
            device = None
            try:
                with self._lock:
                    self._done_event.clear()
                    if not os.path.isfile(azan_path):
                        logger.warning("Azan file not found: %s", azan_path)
                        self._done_event.set()
                        return

                    gen, sample_rate, nchannels = self._create_stream(azan_path, config, stop_flag)
                    try:
                        next(gen)
                    except StopIteration:
                        self._done_event.set()
                        return

                    if self._stop_event.is_set() or (stop_flag and stop_flag.is_set()):
                        gen.close()
                        self._done_event.set()
                        return

                    device = self._ensure_device(sample_rate, nchannels)

                    self._current_gen = gen

                    try:
                        device.stop()
                    except Exception:
                        pass

                    if self._stop_event.is_set() or (stop_flag and stop_flag.is_set()):
                        self._current_gen = None
                        gen.close()
                        self._done_event.set()
                        return

                    device.start(gen)

                if not self._done_event.wait(timeout=300.0):
                    logger.warning("Playback timed out after 300s, forcing stop")
                    with self._lock:
                        if self._current_gen is not None:
                            try:
                                self._current_gen.close()
                            except Exception:
                                pass
                            self._current_gen = None
                    if device is not None:
                        try:
                            device.stop()
                        except Exception:
                            pass

            except (RuntimeError, ValueError, AttributeError, KeyError, TypeError):
                logger.exception("Playback error")
            finally:
                with self._lock:
                    self._current_gen = None
                self._done_event.set()
                _cb = on_done
                if _cb:
                    try:
                        _cb()
                    except Exception:
                        logger.exception("on_done callback failed")

        self._playback_thread = threading.Thread(target=_play, daemon=True)
        self._playback_thread.start()

    def stop(self, wait: bool = True, timeout: float = 2.0) -> None:
        """Stop current playback. Singleton device is stopped but kept for reuse."""
        if not _MINIAUDIO_AVAILABLE:
            return
        self._stop_event.set()
        with self._lock:
            gen = self._current_gen
            self._current_gen = None
        if gen is not None:
            try:
                gen.close()
            except (AttributeError, RuntimeError, OSError, ValueError) as exc:
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
        with self._lock:
            done = self._done_event.is_set()
            has_thread = self._playback_thread is not None and self._playback_thread.is_alive()
        return not done and has_thread

    def set_volume(self, vol: float) -> None:
        """Set global volume."""
        self._volume = max(0.0, min(1.0, vol))
        logger.debug("Volume set to %.2f", self._volume)


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
) -> None:
    """Play azan (backward compatibility)."""
    config = AudioConfig(
        fade_in=fade_in,
        fade_duration=fade_duration,
        takbeer_only=takbeer_only,
        volume=_global_player._volume,
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
        if os.environ.get("PULSE_SERVER") or os.path.exists(
            "/run/user/%d/pulse/native" % os.getuid()
        ):
            return True
        if os.environ.get("PIPEWIRE_RUNTIME_DIR") or os.path.exists(
            "/run/user/%d/pipewire-0" % os.getuid()
        ):
            return True
        if os.path.exists("/dev/snd/pcmC0D0p"):
            return True
    return _MINIAUDIO_AVAILABLE
