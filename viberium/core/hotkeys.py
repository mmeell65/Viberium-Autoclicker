"""Global hotkey handling: toggle, hold-to-run and emergency stop.

Supports keyboard keys and mouse side buttons (X1/X2).
Contexts: "mouse", "keyboard", "macros" — each has its own bindings.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .hooks import InputHub
from . import winapi
from .vkeys import MODIFIER_VKS, normalize_vk

VK_ESCAPE = 0x1B

# Keys the low-level hook may report with a side-specific code (left/right
# modifiers) or as separate XButtons. They are tracked verbatim in `_pressed`.
_SIDE_KEYS = frozenset({0x05, 0x06, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5})

# Every spelling of the same physical key: down may come as one code, up as the
# other (a raw left Ctrl down + a generic Ctrl up must not leave a stuck entry).
_SIDE_KEY_ALIASES = {
    0x05: (0x05,),
    0x06: (0x06,),
    0x10: (0xA0, 0xA1, 0x10),
    0x11: (0xA2, 0xA3, 0x11),
    0x12: (0xA4, 0xA5, 0x12),
    0xA0: (0xA0, 0x10),
    0xA1: (0xA1, 0x10),
    0xA2: (0xA2, 0x11),
    0xA3: (0xA3, 0x11),
    0xA4: (0xA4, 0x12),
    0xA5: (0xA5, 0x12),
}


def binding_matches(binding: frozenset[int], pressed: frozenset[int]) -> bool:
    """True when every key of `binding` is held.

    Extra *modifier* keys (Shift/Ctrl/Alt/Win) are ignored on purpose: a hotkey
    must keep working when the user happens to hold Shift or Ctrl for another
    action. Extra regular keys still cancel the match, so "Ctrl+S" does not fire
    while the user is typing "Ctrl+S+A". Mouse side buttons (X1/X2) are also
    ignored as extras, so holding X1 does not cancel an X2 binding.
    """
    if not binding or not binding <= pressed:
        return False
    extra = pressed - binding
    for vk in extra:
        if vk in MODIFIER_VKS or vk in (0x05, 0x06):
            continue
        return False
    return True


def _as_binding(pressed: set[int]) -> frozenset[int]:
    """Held keys with modifier spellings collapsed to their generic codes."""
    return frozenset(normalize_vk(vk) for vk in pressed)


def _binding_key_codes(binding: frozenset[int]) -> frozenset[int]:
    """Every code a bound key may arrive with (`Ctrl` = 0x11 and 0xA2/0xA3)."""
    codes: set[int] = set()
    for vk in binding:
        codes.add(vk)
        codes.update(_SIDE_KEY_ALIASES.get(vk, ()))
    return frozenset(codes)


class HotkeyManager(QObject):
    """Listens to the raw keyboard/mouse hooks and emits semantic actions."""

    toggle_triggered = Signal()
    hold_started = Signal()
    hold_ended = Signal()
    emergency_triggered = Signal()
    macro_record_triggered = Signal()
    play_triggered = Signal()
    record_triggered = Signal()
    macro_action_triggered = Signal(str, str)   # macro name, "play" | "record"
    captured = Signal(object)   # list[int] | None

    def __init__(self, settings, hub: InputHub, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.hub = hub
        self._pressed: set[int] = set()
        self._blocked: set[int] = set()
        self._modifier_aliases: dict[int, int] = {}
        self._hold_active = False
        self._capturing = False
        self._capture_keys: list[int] = []
        self._capture_widget = None  # QWidget currently in capture mode
        self._owner_hwnd: int | None = None
        self._context = "mouse"
        self.toggle_binding: frozenset[int] = frozenset()
        self.hold_binding: frozenset[int] = frozenset()
        self.emergency_binding: frozenset[int] = frozenset()
        self.extra_bindings: list[tuple[str, str, frozenset[int]]] = []
        # Physical keys (raw code + all spellings) of the last fired hotkey.
        # The macro recorder skips them, so the stop shortcut never ends up in
        # the recording. Keys stay skipped until released.
        self.suppressed: set[int] = set()
        self.block_keys = True
        self._block_keys_enabled = True
        self._sync_bindings()
        hub.add_key_listener(self._handle_key)
        hub.add_mouse_listener(self._handle_mouse)

    # ----------------------------------------------------------------- config
    @property
    def context(self) -> str:
        return self._context

    @context.setter
    def context(self, value: str) -> None:
        if value in ("mouse", "keyboard", "macros"):
            self._context = value
            self._sync_bindings()

    def reload(self) -> None:
        self._sync_bindings()

    def _sync_bindings(self) -> None:
        """Refresh every binding from the settings file.

        `_handle_key` calls this before each event, so a freshly assigned
        hotkey starts working immediately, without reopening pages.
        """
        hotkeys = self.settings["hotkeys"]
        section = hotkeys.get(self._context) or {}
        self.toggle_binding = frozenset(section.get("toggle") or [])
        self.hold_binding = (
            frozenset(section.get("hold") or [])
            if hotkeys.get("hold_enabled", True) and section.get("hold")
            else frozenset()
        )
        self.emergency_binding = frozenset(section.get("emergency") or [])
        self._block_keys_enabled = bool(hotkeys.get("block_keys", True))
        self.block_keys = self._block_keys_enabled
        extras: list[tuple[str, str, frozenset[int]]] = []
        global_section = hotkeys.get("global") or {}
        if global_section.get("record"):
            extras.append(("global", "record", frozenset(global_section["record"])))
        if self._context == "macros":
            play = (hotkeys.get("macros") or {}).get("play")
            if play:
                extras.append(("macros", "play", frozenset(play)))
        # Per-macro shortcuts are global, so they also work when another page
        # is selected or the window is minimized to the tray.
        per_macro = (hotkeys.get("macros") or {}).get("per_macro") or {}
        if isinstance(per_macro, dict):
            for macro_name in sorted(per_macro):
                actions = per_macro.get(macro_name) or {}
                if not isinstance(actions, dict):
                    continue
                for action in ("play", "record"):
                    keys = actions.get(action)
                    if keys:
                        extras.append(("macro", f"{macro_name}#{action}", frozenset(keys)))
        self.extra_bindings = extras


    def all_bindings(self) -> list[tuple[str, str, list[int]]]:
        """Every configured binding: [(context, name, keys), ...].

        The "global" section records keys that work on any page (macro record).
        Per-macro shortcuts are returned with the name "<macro>#<action>".
        """
        result: list[tuple[str, str, list[int]]] = []
        hold_enabled = bool(self.settings["hotkeys"].get("hold_enabled", True))
        for context in ("mouse", "keyboard", "macros", "global"):
            section = self.settings["hotkeys"].get(context) or {}
            for name, keys in section.items():
                if name == "per_macro":
                    continue
                keys = list(keys or [])
                if not keys:
                    continue
                if name == "hold" and not hold_enabled:
                    continue
                result.append((context, name, keys))
        per_macro = (self.settings["hotkeys"].get("macros") or {}).get("per_macro") or {}
        if isinstance(per_macro, dict):
            for macro_name in sorted(per_macro):
                actions = per_macro.get(macro_name) or {}
                if not isinstance(actions, dict):
                    continue
                for action in ("play", "record"):
                    keys = list(actions.get(action) or [])
                    if keys:
                        result.append(("macro", f"{macro_name}#{action}", keys))
        return result

    # ---------------------------------------------------------------- capture
    def begin_capture(self, widget) -> None:
        # Cancel any other widget's capture first
        if self._capturing and self._capture_widget is not widget:
            self._capturing = False
            self._capture_keys = []
            if self._capture_widget is not None:
                try:
                    self._capture_widget.capture_cancelled.emit()
                except Exception:
                    pass
        self._capturing = True
        self._capture_widget = widget
        self._capture_keys = []
        self._remember_owner()

    def cancel_capture(self) -> None:
        if self._capturing:
            self._capturing = False
            if self._capture_widget is not None:
                try:
                    self._capture_widget.capture_cancelled.emit()
                except Exception:
                    pass
            self._capture_widget = None
            self._capture_keys = []

    @property
    def capturing(self) -> bool:
        return self._capturing

    def is_owner_foreground(self) -> bool:
        """True when our own window is active (safe to swallow the hotkey).

        When another program is in front, swallowing the key just leaves the
        user's app without input, so the hotkey still fires but passes through.
        """
        try:
            if self._owner_hwnd is None:
                return True
            return winapi.foreground_hwnd() == self._owner_hwnd
        except Exception:
            return True

    def _remember_owner(self) -> None:
        try:
            self._owner_hwnd = winapi.foreground_hwnd()
        except Exception:
            self._owner_hwnd = None

    # ----------------------------------------------------------------- events
    def _handle_key(self, vk: int, down: bool, injected: bool, ts: float) -> bool:
        if injected:
            return False

        # Hooks report left/right modifier codes; use generic ones everywhere.
        raw_vk = int(vk)
        vk = normalize_vk(raw_vk)
        # Keep the physical code so both XButtons (and both Ctrl keys) map to
        # their own entry in `_pressed` instead of overwriting each other.
        track_vk = raw_vk if raw_vk in _SIDE_KEYS else vk

        self._sync_bindings()
        if self._capturing:
            self._capture_key(vk, down)
            return True

        if down:
            repeat = track_vk in self._pressed
            self._pressed.add(track_vk)
            pressed = frozenset(self._pressed)

            action = None
            matching = _as_binding(pressed)
            if binding_matches(self.emergency_binding, matching):
                action = "emergency"
            elif not repeat and binding_matches(self.toggle_binding, matching):
                action = "toggle"
            elif not repeat and binding_matches(self.hold_binding, matching):
                action = "hold"
            else:
                for context, name, binding in self.extra_bindings:
                    if not repeat and binding_matches(binding, matching):
                        action = f"{context}:{name}"
                        if action.endswith(":record") and binding_matches(self.emergency_binding, matching):
                            # The record shortcut IS the emergency shortcut: this
                            # press belongs to the emergency stop, not to record.
                            action = "emergency"
                        break
                if action is None:
                    # The macro-record shortcut works on every page, not only on
                    # the Macros page, so it is checked after the page bindings.
                    global_record = (self.settings["hotkeys"].get("global") or {}).get("record")
                    if (
                        not repeat
                        and global_record
                        and binding_matches(frozenset(global_record), matching)
                    ):
                        action = "global:record"

            if action:
                if self.is_owner_foreground() and self._block_keys_enabled:
                    self._blocked.add(track_vk)
                self._suppress_binding(action, matching, track_vk)
                if action == "emergency":
                    self.emergency_triggered.emit()
                elif action == "toggle":
                    self.toggle_triggered.emit()
                elif action == "hold":
                    self._hold_active = True
                    self.hold_started.emit()
                elif action.endswith(":record"):
                    self.record_triggered.emit()
                elif action.endswith(":play"):
                    self.play_triggered.emit()
                else:
                    context, _, name = action.partition(":")
                    if context == "macro":
                        macro_name, _, macro_action = name.rpartition("#")
                        self.macro_action_triggered.emit(macro_name, macro_action)
                return self.block_keys

            if repeat and track_vk in self._blocked:
                return True
            return False

        # key up — ALWAYS pass through so modifiers never stick
        self._blocked.discard(track_vk)
        # A modifier can be reported with a side-specific code on key down and a
        # generic one on key up: drop every spelling, or the key stays "held"
        # forever and every later hotkey that uses it stops matching.
        drop = {track_vk, vk}
        drop.update(_SIDE_KEY_ALIASES.get(raw_vk, ()))
        drop.update(_SIDE_KEY_ALIASES.get(vk, ()))
        self._pressed.difference_update(drop)
        if self.suppressed.difference_update(drop):
            # A whole combo fired: drop every key of it from `_pressed` so the
            # next press is a fresh action, not a "repeat".
            self._pressed.clear()
        if self._hold_active and not self.hold_binding <= _as_binding(self._pressed):
            self._hold_active = False
            self.hold_ended.emit()
        return False

    def _suppress_binding(self, action: str, matching: frozenset[int], track_vk: int) -> None:
        """Mark the keys of a fired hotkey as "not user input" for the recorder."""
        binding = frozenset()
        if action == "emergency":
            binding = self.emergency_binding
        elif action == "toggle":
            binding = self.toggle_binding
        elif action == "hold":
            binding = self.hold_binding
        else:
            context, _, name = action.partition(":")
            for ctx, candidate, keys in self.extra_bindings:
                if ctx == context and candidate == name:
                    binding = keys
                    break
            if not binding and context == "global" and name == "record":
                binding = frozenset((self.settings["hotkeys"].get("global") or {}).get("record") or [])
        if not binding or not binding <= matching:
            return
        for vk in binding:
            self.suppressed.add(vk)
            for alias in _SIDE_KEY_ALIASES.get(vk, ()):
                self.suppressed.add(alias)
        self.suppressed.add(track_vk)

    def is_suppressed(self, raw_vk: int) -> bool:
        """True when a key belongs to an application hotkey (or the one firing now).

        The macro recorder skips these keys, so the record/stop shortcut and the
        emergency stop never end up inside a macro.
        """
        raw_vk = int(raw_vk)
        vk = normalize_vk(raw_vk)
        if raw_vk in self.suppressed or vk in self.suppressed:
            return True
        # Modifiers may arrive with a side-specific code (left Ctrl = 0xA2).
        aliases = _SIDE_KEY_ALIASES.get(raw_vk) or _SIDE_KEY_ALIASES.get(vk) or ()
        if any(alias in self.suppressed for alias in aliases):
            return True
        bindings = [self.emergency_binding, self.toggle_binding, self.hold_binding]
        bindings.extend(binding for _, _, binding in self.extra_bindings)
        for context, name, keys in self.all_bindings():
            if context == "macro":
                bindings.append(frozenset(keys))
        for binding in bindings:
            if vk in _binding_key_codes(binding):
                return True
        return False

    def _handle_mouse(self, kind: str, x: int, y: int, delta: int, injected: bool, ts: float) -> bool:
        """Mouse events (move, clicks, wheel). X1/X2 already reached _handle_key."""
        if injected:
            return False
        # Non-X mouse buttons are not used for hotkeys; just ignore
        return False

    def _capture_key(self, vk: int, down: bool) -> None:
        if down:
            if vk == VK_ESCAPE:
                self._capturing = False
                if self._capture_widget is not None:
                    try:
                        self._capture_widget.capture_cancelled.emit()
                    except Exception:
                        pass
                self._capture_widget = None
                self._capture_keys = []
                self.captured.emit(None)
                return
            if vk in self._capture_keys:
                return
            self._capture_keys.append(vk)
            non_modifiers = [k for k in self._capture_keys if k not in MODIFIER_VKS]
            if non_modifiers:
                keys = list(self._capture_keys)
                self._capturing = False
                widget = self._capture_widget
                self._capture_widget = None
                self._capture_keys = []
                self.captured.emit(keys)
                if widget is not None:
                    try:
                        widget.capture_finished.emit()
                    except Exception:
                        pass
        else:
            if vk in self._capture_keys and vk not in MODIFIER_VKS:
                self._capture_keys.remove(vk)

    def trigger(self, context: str, name: str) -> bool:
        """Fire a binding programmatically (e.g. from an on-screen button)."""
        self._sync_bindings()
        section = self.settings["hotkeys"].get(context) or {}

        if not section.get(name):
            return False
        if name == "emergency":
            self.emergency_triggered.emit()
        elif name == "toggle":
            self.toggle_triggered.emit()
        elif name == "hold":
            self._hold_active = True
            self.hold_started.emit()
        elif name == "play":
            self.play_triggered.emit()
        elif name == "record":
            self.record_triggered.emit()
        else:
            return False
        return True

    def release_all(self) -> None:
        self._pressed.clear()
        self._blocked.clear()
        self.suppressed.clear()
        self._hold_active = False
