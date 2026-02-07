#!/usr/bin/env python3
"""Generate VoiceInput.app icon (.icns) from the microphone emoji.

Renders the 🎙️ emoji at multiple resolutions using PyQt6 and converts
the resulting PNGs into a macOS .icns file via ``iconutil``.

Requirements:
    - PyQt6 (already a project dependency)
    - macOS with ``iconutil`` (ships with Xcode Command Line Tools)

Usage:
    python scripts/create_icon.py
"""

import os
import subprocess
import sys
import tempfile


def _render_icon(size: int, path: str) -> None:
    """Render the microphone emoji onto a *size* × *size* PNG."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap

    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Dark circular background
    painter.setBrush(QColor(30, 30, 30))
    painter.setPen(Qt.PenStyle.NoPen)
    margin = max(1, int(size * 0.04))
    painter.drawEllipse(margin, margin, size - 2 * margin, size - 2 * margin)

    # Microphone emoji
    font = QFont()
    font.setPixelSize(int(size * 0.60))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "\U0001f399\ufe0f")
    painter.end()

    pixmap.save(path, "PNG")


def main() -> None:
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)  # noqa: F841 — must stay alive

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    assets_dir = os.path.join(project_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # macOS iconset requires specific filenames and resolutions
    iconset_dir = os.path.join(tempfile.mkdtemp(), "VoiceInput.iconset")
    os.makedirs(iconset_dir)

    # Standard and @2x sizes required by iconutil
    icon_sizes = [
        (16,  "icon_16x16.png"),
        (32,  "icon_16x16@2x.png"),
        (32,  "icon_32x32.png"),
        (64,  "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]

    print(f"Rendering icons into {iconset_dir} ...")
    for size, filename in icon_sizes:
        _render_icon(size, os.path.join(iconset_dir, filename))

    icns_path = os.path.join(assets_dir, "icon.icns")

    try:
        subprocess.run(
            ["iconutil", "-c", "icns", iconset_dir, "-o", icns_path],
            check=True,
        )
        print(f"Created: {icns_path}")
    except FileNotFoundError:
        print(
            "iconutil not found — this script must run on macOS.\n"
            f"PNG files saved to: {iconset_dir}"
        )
    except subprocess.CalledProcessError as exc:
        print(f"iconutil failed ({exc}). PNG files saved to: {iconset_dir}")


if __name__ == "__main__":
    main()
