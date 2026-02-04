# output.py - Text output (paste)
#
# NOTE: On macOS, this module requires "Accessibility" permission.
# Go to System Preferences > Security & Privacy > Privacy > Accessibility
# and add your terminal app or Python interpreter.

import platform
import time

import pyautogui
import pyperclip


def paste_text(text: str) -> None:
    """Copy text to clipboard and paste it at the current cursor position.

    This function:
    1. Copies the given text to the system clipboard
    2. Waits a short delay to ensure the clipboard is updated
    3. Simulates pressing Cmd+V (macOS) or Ctrl+V (Linux/Windows) to paste

    Args:
        text: The text to paste.

    Note:
        On macOS, this requires "Accessibility" permission to be granted
        to your terminal app or Python interpreter in:
        System Preferences > Security & Privacy > Privacy > Accessibility
    """
    # Copy text to clipboard
    pyperclip.copy(text)

    # Short delay to ensure clipboard is updated
    time.sleep(0.1)

    # Simulate paste keyboard shortcut
    if platform.system() == "Darwin":
        # macOS: Cmd+V
        pyautogui.hotkey("command", "v")
    else:
        # Linux/Windows: Ctrl+V
        pyautogui.hotkey("ctrl", "v")
