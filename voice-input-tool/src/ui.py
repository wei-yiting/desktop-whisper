# ui.py - Floating UI window
"""
Floating UI window for voice input tool.
Provides visual feedback during recording and transcription.
"""

import math
import random
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont

# Global window instance
_window: "FloatingWindow | None" = None


class SoundWaveWidget(QWidget):
    """Widget displaying animated sound wave bars."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bar_count = 7
        self.bar_heights = [0.3] * self.bar_count
        self.target_heights = [0.3] * self.bar_count

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_bars)

        self.setMinimumSize(150, 100)

    def start(self) -> None:
        """Start the animation."""
        self.timer.start(100)

    def stop(self) -> None:
        """Stop the animation."""
        self.timer.stop()

    def _update_bars(self) -> None:
        """Update bar heights with smooth animation."""
        for i in range(self.bar_count):
            # Generate new target heights randomly
            self.target_heights[i] = random.uniform(0.2, 1.0)
            # Smooth transition towards target
            self.bar_heights[i] += (self.target_heights[i] - self.bar_heights[i]) * 0.5
        self.update()

    def paintEvent(self, event) -> None:
        """Draw the sound wave bars."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        bar_width = width // (self.bar_count * 2 + 1)
        max_bar_height = height * 0.8

        # Center the bars
        total_width = bar_width * (self.bar_count * 2 - 1)
        start_x = (width - total_width) // 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(100, 200, 255))

        for i, h in enumerate(self.bar_heights):
            bar_height = int(max_bar_height * h)
            x = start_x + i * bar_width * 2
            y = (height - bar_height) // 2

            # Draw rounded rectangle
            painter.drawRoundedRect(x, y, bar_width, bar_height, bar_width // 2, bar_width // 2)


class SpinnerWidget(QWidget):
    """Widget displaying a loading spinner with text."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.angle = 0
        self.dot_count = 8

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_spinner)

        self.setMinimumSize(150, 100)

    def start(self) -> None:
        """Start the spinner animation."""
        self.timer.start(80)

    def stop(self) -> None:
        """Stop the spinner animation."""
        self.timer.stop()

    def _update_spinner(self) -> None:
        """Update spinner rotation."""
        self.angle = (self.angle + 30) % 360
        self.update()

    def paintEvent(self, event) -> None:
        """Draw the spinner and text."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2 - 15  # Offset up for text below

        radius = min(width, height) // 4
        dot_radius = 6

        # Draw spinning dots
        for i in range(self.dot_count):
            angle_rad = math.radians(self.angle + i * (360 / self.dot_count))
            x = center_x + int(radius * math.cos(angle_rad))
            y = center_y + int(radius * math.sin(angle_rad))

            # Fade opacity based on position
            opacity = int(255 * (1 - i / self.dot_count))
            color = QColor(100, 200, 255, opacity)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(x - dot_radius, y - dot_radius, dot_radius * 2, dot_radius * 2)

        # Draw text
        painter.setPen(QColor(255, 255, 255))
        font = QFont()
        font.setPointSize(14)
        painter.setFont(font)
        text_y = center_y + radius + 30
        painter.drawText(0, text_y, width, 30, Qt.AlignmentFlag.AlignCenter, "轉錄中...")


class FloatingWindow(QWidget):
    """Frameless floating window for UI feedback."""

    def __init__(self) -> None:
        super().__init__()
        self._setup_window()
        self._setup_widgets()

    def _setup_window(self) -> None:
        """Configure window properties."""
        # Frameless, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Semi-transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Set size
        self.setFixedSize(200, 200)

        # Center on screen
        self._center_on_screen()

    def _center_on_screen(self) -> None:
        """Position window at screen center."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _setup_widgets(self) -> None:
        """Create UI widgets."""
        self.layout_widget = QVBoxLayout(self)
        self.layout_widget.setContentsMargins(10, 10, 10, 10)

        # Sound wave widget
        self.sound_wave = SoundWaveWidget(self)
        self.sound_wave.hide()

        # Spinner widget
        self.spinner = SpinnerWidget(self)
        self.spinner.hide()

        self.layout_widget.addWidget(self.sound_wave)
        self.layout_widget.addWidget(self.spinner)

    def paintEvent(self, event) -> None:
        """Draw semi-transparent rounded background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark background
        painter.setBrush(QColor(30, 30, 30, 200))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)

    def show_recording(self) -> None:
        """Show recording UI with sound wave animation."""
        self.spinner.stop()
        self.spinner.hide()

        self.sound_wave.show()
        self.sound_wave.start()

        self.show()
        self.raise_()
        self.activateWindow()

    def show_transcribing(self) -> None:
        """Show transcribing UI with spinner animation."""
        self.sound_wave.stop()
        self.sound_wave.hide()

        self.spinner.show()
        self.spinner.start()

        self.show()
        self.raise_()
        self.activateWindow()

    def hide_window(self) -> None:
        """Hide the window and stop animations."""
        self.sound_wave.stop()
        self.spinner.stop()
        self.hide()


def _get_window() -> FloatingWindow:
    """Get or create the global window instance."""
    global _window
    if _window is None:
        _window = FloatingWindow()
    return _window


def show_recording_ui() -> None:
    """Show the recording UI with sound wave animation."""
    window = _get_window()
    window.show_recording()


def show_transcribing_ui() -> None:
    """Show the transcribing UI with loading spinner."""
    window = _get_window()
    window.show_transcribing()


def hide_ui() -> None:
    """Hide the UI window."""
    window = _get_window()
    window.hide_window()
