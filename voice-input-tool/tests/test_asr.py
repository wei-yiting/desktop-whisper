# test_asr.py - ASR module tests

import os
import wave
import struct
import tempfile
from unittest.mock import patch, MagicMock

import pytest


class TestASREngine:
    """Unit tests for the ASR engine (model loading is mocked)."""

    def test_transcribe_file_not_found(self):
        """transcribe() should raise FileNotFoundError for missing files."""
        from src.asr import ASREngine

        # Reset singleton so we get a fresh instance
        ASREngine._instance = None
        engine = ASREngine()

        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            engine.transcribe("/nonexistent/path/audio.wav")

    def test_transcribe_returns_text(self, tmp_path):
        """transcribe() should return text from the model result."""
        from src.asr import ASREngine

        # Create a minimal valid WAV file
        wav_path = str(tmp_path / "test.wav")
        _create_silent_wav(wav_path, duration_s=0.5, sample_rate=16000)

        # Mock the model and its transcribe method
        mock_result = MagicMock()
        mock_result.text = "hello world"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = [mock_result]

        ASREngine._instance = None
        engine = ASREngine()
        engine._model = mock_model

        text = engine.transcribe(wav_path)
        assert text == "hello world"
        mock_model.transcribe.assert_called_once_with(audio=wav_path)

    def test_singleton_returns_same_instance(self):
        """ASREngine should always return the same singleton instance."""
        from src.asr import ASREngine

        ASREngine._instance = None
        a = ASREngine()
        b = ASREngine()
        assert a is b

    def test_transcribe_runtime_error(self, tmp_path):
        """transcribe() should wrap model errors in RuntimeError."""
        from src.asr import ASREngine

        wav_path = str(tmp_path / "test.wav")
        _create_silent_wav(wav_path, duration_s=0.5, sample_rate=16000)

        mock_model = MagicMock()
        mock_model.transcribe.side_effect = Exception("model crashed")

        ASREngine._instance = None
        engine = ASREngine()
        engine._model = mock_model

        with pytest.raises(RuntimeError, match="Transcription failed"):
            engine.transcribe(wav_path)


class TestModuleLevelAPI:
    """Tests for the module-level transcribe() function."""

    def test_module_transcribe_delegates_to_engine(self, tmp_path):
        """The module-level transcribe() should delegate to the singleton."""
        from src import asr

        wav_path = str(tmp_path / "test.wav")
        _create_silent_wav(wav_path, duration_s=0.5, sample_rate=16000)

        mock_result = MagicMock()
        mock_result.text = "module level works"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = [mock_result]

        # Inject mock model into the module-level engine
        asr._engine._model = mock_model

        text = asr.transcribe(wav_path)
        assert text == "module level works"


class TestDeviceSelection:
    """Tests for device and dtype selection helpers."""

    def test_select_device_cpu_fallback(self):
        """Should fall back to CPU when no accelerator is available."""
        from src.asr import _select_device

        with patch("torch.backends.mps.is_available", return_value=False), \
             patch("torch.cuda.is_available", return_value=False):
            assert _select_device() == "cpu"

    def test_select_device_mps(self):
        """Should prefer MPS when available."""
        from src.asr import _select_device

        with patch("torch.backends.mps.is_available", return_value=True):
            assert _select_device() == "mps"

    def test_select_dtype_mps_uses_float16(self):
        """MPS should use float16 (bfloat16 is unsupported)."""
        import torch
        from src.asr import _select_dtype

        assert _select_dtype("mps") == torch.float16

    def test_select_dtype_cuda_uses_bfloat16(self):
        """CUDA should use bfloat16."""
        import torch
        from src.asr import _select_dtype

        assert _select_dtype("cuda:0") == torch.bfloat16

    def test_select_dtype_cpu_uses_float32(self):
        """CPU should use float32."""
        import torch
        from src.asr import _select_dtype

        assert _select_dtype("cpu") == torch.float32


# --- Helpers ---

def _create_silent_wav(path: str, duration_s: float = 1.0, sample_rate: int = 16000):
    """Create a silent WAV file for testing purposes."""
    n_frames = int(sample_rate * duration_s)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))
