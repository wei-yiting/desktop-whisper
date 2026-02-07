# app.py - Main application, integrates all modules

import enum
import logging
import os
import sys
import threading

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication

from src import asr, hotkey, output, recorder, ui

logger = logging.getLogger(__name__)

# Hotkey combination (configurable via environment variable)
HOTKEY = os.environ.get("VOICE_INPUT_HOTKEY", "<alt>+<space>")


class State(enum.Enum):
    """Application states."""

    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


class VoiceInputApp(QObject):
    """Main application controller.

    Integrates hotkey listener, audio recorder, ASR engine, floating UI,
    and text output into a state machine.  Qt signals bridge the pynput
    listener thread and the ASR worker thread back to the main event loop
    so that all UI calls happen on the main thread.
    """

    # Signals for cross-thread → main-thread communication
    hotkey_pressed = pyqtSignal()
    model_loaded = pyqtSignal()
    transcription_done = pyqtSignal(str)
    transcription_failed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._state = State.IDLE
        self._lock = threading.Lock()

        # Wire signals to slots (queued connection across threads)
        self.hotkey_pressed.connect(self._on_hotkey)
        self.model_loaded.connect(self._on_model_loaded)
        self.transcription_done.connect(self._on_transcription_done)
        self.transcription_failed.connect(self._on_transcription_failed)

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Show a loading spinner and begin loading the ASR model."""
        ui.show_transcribing_ui()
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self) -> None:
        """Load the ASR model (runs in a background thread)."""
        try:
            logger.info("Loading ASR model...")
            # Accessing the property triggers the lazy load
            _ = asr._engine.model
            logger.info("ASR model loaded")
        except Exception as e:
            logger.error("Failed to load ASR model: %s", e)
        self.model_loaded.emit()

    @pyqtSlot()
    def _on_model_loaded(self) -> None:
        """Hide the loading UI once the model is ready."""
        ui.hide_ui()
        logger.info("Ready — press %s to start recording", HOTKEY)

    # ------------------------------------------------------------------
    # Hotkey handling
    # ------------------------------------------------------------------

    def _hotkey_callback(self) -> None:
        """Called from the pynput thread; emits a signal to the main thread."""
        self.hotkey_pressed.emit()

    @pyqtSlot()
    def _on_hotkey(self) -> None:
        """Toggle between IDLE ↔ RECORDING on each hotkey press."""
        with self._lock:
            if self._state == State.IDLE:
                self._start_recording()
            elif self._state == State.RECORDING:
                self._stop_recording_and_transcribe()
            # Ignore presses while transcribing

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def _start_recording(self) -> None:
        self._state = State.RECORDING
        recorder.start_recording()
        ui.show_recording_ui()
        logger.info("Recording...")

    def _stop_recording_and_transcribe(self) -> None:
        self._state = State.TRANSCRIBING
        audio_path = recorder.stop_recording()
        ui.show_transcribing_ui()
        logger.info("Transcribing...")
        threading.Thread(
            target=self._run_transcription,
            args=(audio_path,),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------
    # ASR transcription
    # ------------------------------------------------------------------

    def _run_transcription(self, audio_path: str) -> None:
        """Run ASR in a background thread and emit the result."""
        try:
            text = asr.transcribe(audio_path)
            self.transcription_done.emit(text)
        except Exception as e:
            self.transcription_failed.emit(str(e))
        finally:
            try:
                os.remove(audio_path)
            except OSError:
                pass

    @pyqtSlot(str)
    def _on_transcription_done(self, text: str) -> None:
        ui.hide_ui()
        if text.strip():
            logger.info("Result: %s", text)
            output.paste_text(text)
        else:
            logger.warning("Empty transcription")
        self._state = State.IDLE

    @pyqtSlot(str)
    def _on_transcription_failed(self, error: str) -> None:
        ui.hide_ui()
        logger.error("Transcription failed: %s", error)
        self._state = State.IDLE


def main() -> None:
    """Entry point for the voice input tool."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # QApplication must live on the main thread
    qt_app = QApplication(sys.argv)

    app = VoiceInputApp()

    # Register hotkey and start the pynput listener in a daemon thread
    hotkey.register_hotkey(HOTKEY, app._hotkey_callback)
    threading.Thread(target=hotkey.start_listener, daemon=True).start()

    logger.info("Voice input tool started — press %s to toggle recording", HOTKEY)

    # Kick off model loading (shows loading UI while waiting)
    app.start()

    # Run the Qt event loop (blocks until the application quits)
    sys.exit(qt_app.exec())
