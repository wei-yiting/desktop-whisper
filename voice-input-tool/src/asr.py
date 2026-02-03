# asr.py - ASR inference module using Qwen3-ASR (singleton pattern with lazy loading)

import os
import logging
from typing import Optional

import torch

logger = logging.getLogger(__name__)

# Model ID - using the 0.6B variant (smallest available Qwen3-ASR model)
MODEL_ID = os.environ.get("ASR_MODEL_ID", "Qwen/Qwen3-ASR-0.6B")


def _select_device() -> str:
    """Select the best available device: MPS > CUDA > CPU."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda:0"
    return "cpu"


def _select_dtype(device: str) -> torch.dtype:
    """Select appropriate dtype based on device capabilities.

    MPS does not support bfloat16, so we use float16 there.
    CUDA supports bfloat16 natively. CPU falls back to float32.
    """
    if device == "mps":
        return torch.float16
    if device.startswith("cuda"):
        return torch.bfloat16
    return torch.float32


class ASREngine:
    """Singleton ASR engine wrapping Qwen3-ASR for speech-to-text inference.

    The model is loaded lazily on the first call to `transcribe()` and
    kept in memory for subsequent calls.
    """

    _instance: Optional["ASREngine"] = None

    def __new__(cls) -> "ASREngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
        return cls._instance

    def _load_model(self) -> None:
        """Load the Qwen3-ASR model into memory."""
        from qwen_asr import Qwen3ASRModel

        device = _select_device()
        dtype = _select_dtype(device)
        logger.info("Loading ASR model %s on device=%s dtype=%s", MODEL_ID, device, dtype)

        self._model = Qwen3ASRModel.from_pretrained(
            MODEL_ID,
            dtype=dtype,
            device_map=device,
        )
        logger.info("ASR model loaded successfully")

    @property
    def model(self):
        """Return the loaded model, initializing on first access."""
        if self._model is None:
            self._load_model()
        return self._model

    def transcribe(self, audio_path: str) -> str:
        """Transcribe a WAV file to text.

        Args:
            audio_path: Path to a WAV audio file.

        Returns:
            Transcribed text string.

        Raises:
            FileNotFoundError: If the audio file does not exist.
            RuntimeError: If transcription fails.
        """
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            results = self.model.transcribe(audio=audio_path)
        except Exception as e:
            raise RuntimeError(f"Transcription failed for {audio_path}: {e}") from e

        # The transcribe() API returns a list of result objects.
        # Each result has a .text attribute containing the transcribed text.
        if isinstance(results, list):
            return results[0].text if results else ""
        # Single result object
        return results.text


# Module-level singleton instance
_engine = ASREngine()


def transcribe(audio_path: str) -> str:
    """Transcribe a WAV file to text using the Qwen3-ASR model.

    This is the main public API. The model is loaded lazily on the first
    call and reused for all subsequent calls.

    Args:
        audio_path: Path to a WAV audio file.

    Returns:
        Transcribed text string.

    Example:
        >>> from src.asr import transcribe
        >>> text = transcribe("test.wav")
        >>> print(text)
    """
    return _engine.transcribe(audio_path)
