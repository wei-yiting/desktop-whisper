# recorder.py - Audio recording module

import tempfile
import threading
import wave
from typing import Optional

import numpy as np
import sounddevice as sd

# Audio settings for Qwen3-ASR compatibility
SAMPLE_RATE = 16000  # Hz
CHANNELS = 1  # Mono


class _RecorderState:
    """Internal state holder for the recorder."""

    def __init__(self):
        self._recording = False
        self._audio_data: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()

    def reset(self):
        """Reset state for a new recording session."""
        self._audio_data = []
        self._stream = None


# Module-level state
_state = _RecorderState()


def _audio_callback(indata: np.ndarray, frames: int, time_info, status) -> None:
    """Callback function for sounddevice stream."""
    if status:
        # Log any status messages (underflow, overflow, etc.)
        pass
    # Append a copy of the audio data
    _state._audio_data.append(indata.copy())


def start_recording() -> None:
    """Start recording audio from the microphone.

    This function is non-blocking. The recording happens in the background
    using sounddevice's callback mechanism.

    Raises:
        RuntimeError: If already recording.
    """
    with _state._lock:
        if _state._recording:
            raise RuntimeError("Already recording")

        _state.reset()
        _state._recording = True

        # Create and start the input stream
        _state._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=np.float32,
            callback=_audio_callback,
        )
        _state._stream.start()


def stop_recording() -> str:
    """Stop recording and save the audio to a temporary WAV file.

    Returns:
        Path to the saved WAV file.

    Raises:
        RuntimeError: If not currently recording.
    """
    with _state._lock:
        if not _state._recording:
            raise RuntimeError("Not currently recording")

        # Stop and close the stream
        if _state._stream is not None:
            _state._stream.stop()
            _state._stream.close()

        _state._recording = False

        # Concatenate all audio chunks
        if not _state._audio_data:
            audio = np.array([], dtype=np.float32)
        else:
            audio = np.concatenate(_state._audio_data, axis=0)

        # Convert float32 [-1.0, 1.0] to int16 for WAV file
        audio_int16 = (audio * 32767).astype(np.int16)

        # Save to temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
            prefix="recording_",
        )
        temp_path = temp_file.name
        temp_file.close()

        with wave.open(temp_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        return temp_path


def is_recording() -> bool:
    """Check if currently recording.

    Returns:
        True if recording is in progress, False otherwise.
    """
    with _state._lock:
        return _state._recording
