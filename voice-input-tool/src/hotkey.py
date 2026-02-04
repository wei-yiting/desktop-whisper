# hotkey.py - Hotkey listener

import threading
from typing import Callable, Optional

from pynput import keyboard
from pynput.keyboard import Key, KeyCode


class _HotkeyState:
    """Internal state holder for the hotkey listener."""

    def __init__(self):
        self._hotkeys: dict[frozenset[str], Callable] = {}
        self._pressed_keys: set[str] = set()
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()

    def reset(self):
        """Reset state."""
        self._pressed_keys = set()
        self._listener = None


# Module-level state
_state = _HotkeyState()


def _normalize_key(key: str) -> str:
    """Normalize key name to a consistent format.

    Args:
        key: Key name like "<alt>", "<space>", "a", etc.

    Returns:
        Normalized key name.
    """
    key = key.lower().strip()
    # Remove angle brackets if present
    if key.startswith("<") and key.endswith(">"):
        key = key[1:-1]
    # Normalize common aliases
    aliases = {
        "option": "alt",
        "opt": "alt",
        "cmd": "cmd",
        "command": "cmd",
        "ctrl": "ctrl",
        "control": "ctrl",
        "shift": "shift",
    }
    return aliases.get(key, key)


def _parse_key_combination(key_combination: str) -> frozenset[str]:
    """Parse a key combination string into a set of normalized keys.

    Args:
        key_combination: String like "<alt>+<space>" or "ctrl+a".

    Returns:
        Frozenset of normalized key names.
    """
    parts = key_combination.split("+")
    return frozenset(_normalize_key(part) for part in parts)


def _key_to_string(key) -> Optional[str]:
    """Convert a pynput key to a normalized string.

    Args:
        key: pynput Key or KeyCode object.

    Returns:
        Normalized key name or None if not recognized.
    """
    if isinstance(key, Key):
        key_map = {
            Key.alt: "alt",
            Key.alt_l: "alt",
            Key.alt_r: "alt",
            Key.alt_gr: "alt",
            Key.cmd: "cmd",
            Key.cmd_l: "cmd",
            Key.cmd_r: "cmd",
            Key.ctrl: "ctrl",
            Key.ctrl_l: "ctrl",
            Key.ctrl_r: "ctrl",
            Key.shift: "shift",
            Key.shift_l: "shift",
            Key.shift_r: "shift",
            Key.space: "space",
            Key.enter: "enter",
            Key.tab: "tab",
            Key.esc: "esc",
            Key.backspace: "backspace",
            Key.delete: "delete",
        }
        return key_map.get(key)
    elif isinstance(key, KeyCode):
        if key.char:
            return key.char.lower()
        elif key.vk is not None:
            # Handle special virtual key codes
            return None
    return None


def _on_press(key) -> None:
    """Handle key press event."""
    key_str = _key_to_string(key)
    if key_str is None:
        return

    with _state._lock:
        _state._pressed_keys.add(key_str)
        # Check if current pressed keys match any registered hotkey
        current_keys = frozenset(_state._pressed_keys)
        for hotkey_keys, callback in _state._hotkeys.items():
            if hotkey_keys == current_keys:
                # Execute callback in a separate thread to avoid blocking
                threading.Thread(target=callback, daemon=True).start()
                break


def _on_release(key) -> None:
    """Handle key release event."""
    key_str = _key_to_string(key)
    if key_str is None:
        return

    with _state._lock:
        _state._pressed_keys.discard(key_str)


def register_hotkey(key_combination: str, callback: Callable) -> None:
    """Register a hotkey with a callback function.

    Args:
        key_combination: Key combination string like "<alt>+<space>".
        callback: Function to call when the hotkey is pressed.
    """
    keys = _parse_key_combination(key_combination)
    with _state._lock:
        _state._hotkeys[keys] = callback


def start_listener() -> None:
    """Start the hotkey listener (blocking).

    This function blocks until stop_listener() is called.
    The listener runs in the current thread.
    """
    with _state._lock:
        if _state._listener is not None:
            raise RuntimeError("Listener already running")

        _state._listener = keyboard.Listener(
            on_press=_on_press,
            on_release=_on_release,
        )
        _state._listener.start()

    # Block until the listener is stopped
    _state._listener.join()


def stop_listener() -> None:
    """Stop the hotkey listener."""
    with _state._lock:
        if _state._listener is not None:
            _state._listener.stop()
            _state._listener = None
        _state.reset()
