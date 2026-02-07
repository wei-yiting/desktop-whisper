# app.py - Main application, integrates all modules

import enum
import logging
import os
import sys
import threading

from PyQt6.QtCore import Qt, QObject, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QIcon, QPainter, QPixmap, QFont
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

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

        # System tray icon
        self._tray: QSystemTrayIcon | None = None

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
    # System tray icon
    # ------------------------------------------------------------------

    def _setup_tray(self) -> None:
        """Create the system tray icon and its context menu."""
        self._tray = QSystemTrayIcon(self._create_tray_icon(), parent=self)

        menu = QMenu()

        # Toggle recording action — label updates based on state
        self._toggle_action = QAction("開始錄音", menu)
        self._toggle_action.triggered.connect(self._on_hotkey)
        menu.addAction(self._toggle_action)

        menu.addSeparator()

        # Show current hotkey
        hotkey_action = QAction(f"快捷鍵：{HOTKEY}", menu)
        hotkey_action.setEnabled(False)
        menu.addAction(hotkey_action)

        # About
        about_action = QAction("關於", menu)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("結束", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.setToolTip("Desktop Whisper — 語音輸入工具")
        self._tray.show()
        logger.info("System tray icon ready")

    @staticmethod
    def _create_tray_icon() -> QIcon:
        """Render a microphone emoji onto a pixmap and return it as a QIcon."""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        font = QFont()
        font.setPixelSize(56)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🎙️")
        painter.end()
        return QIcon(pixmap)

    def _update_toggle_label(self) -> None:
        """Update the toggle menu item text based on current state."""
        if self._state == State.RECORDING:
            self._toggle_action.setText("停止錄音")
        else:
            self._toggle_action.setText("開始錄音")

    def _show_about(self) -> None:
        """Show an about dialog."""
        QMessageBox.information(
            None,
            "關於 Desktop Whisper",
            "Desktop Whisper v0.1.0\n\n"
            "語音輸入工具 — 按下快捷鍵即可錄音並轉文字。\n\n"
            f"快捷鍵：{HOTKEY}\n"
            "ASR 引擎：Qwen3-ASR",
        )

    @staticmethod
    def _quit() -> None:
        """Quit the application."""
        logger.info("Quitting application")
        hotkey.stop_listener()
        QApplication.quit()

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
        self._update_toggle_label()
        recorder.start_recording()
        ui.show_recording_ui()
        logger.info("Recording...")

    def _stop_recording_and_transcribe(self) -> None:
        self._state = State.TRANSCRIBING
        self._update_toggle_label()
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
        self._update_toggle_label()

    @pyqtSlot(str)
    def _on_transcription_failed(self, error: str) -> None:
        ui.hide_ui()
        logger.error("Transcription failed: %s", error)
        self._state = State.IDLE
        self._update_toggle_label()


def main() -> None:
    """Entry point for the voice input tool."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # QApplication must live on the main thread
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    app = VoiceInputApp()

    # Set up the menu bar / system tray icon
    app._setup_tray()

    # Register hotkey and start the pynput listener in a daemon thread
    hotkey.register_hotkey(HOTKEY, app._hotkey_callback)
    threading.Thread(target=hotkey.start_listener, daemon=True).start()

    logger.info("Voice input tool started — press %s to toggle recording", HOTKEY)

    # Kick off model loading (shows loading UI while waiting)
    app.start()

    # Run the Qt event loop (blocks until the application quits)
    sys.exit(qt_app.exec())
