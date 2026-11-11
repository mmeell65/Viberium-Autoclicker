"""Global hotkey handling: toggle, hold-to-run and emergency stop.

Supports keyboard keys and mouse side buttons (X1/X2).
Contexts: "mouse", "keyboard", "macros" — each has its own bindings.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .hooks import InputHub

MODIFIER_VKS = {0x10, 0x11, 0x12, 0x5B, 0x5C}
VK_ESCAPE = 0x1B

MOUSE_X1 = 0x05
MOUSE_X2 = 0x06


class HotkeyManager(QObject):
    """Listens to the raw keyboard/mouse hooks and emits semantic actions."""

    toggle_triggered = Signal()
    hold_started = Signal()
    hold_ended = Signal()
    emergency_triggered = Signal()
    macro_record_triggered = Signal()
    captured = Signal(object)   # list[int] | None

    def __init__(self, settings, hub: InputHub, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.hub = hub
        self._pressed: set[int] = set()
        self._blocked: set[int] = set()
        self._hold_active = False
        self._capturing = False
        self._capture_keys: list[int] = []
        self._capture_widget = None  # QWidget currently in capture mode
        self._context = "mouse"
        self.toggle_binding: frozenset[int] = frozenset()
        self.hold_binding: frozenset[int] = frozenset()
        self.emergency_binding: frozenset[int] = frozenset()
        self.block_keys = True
        self.reload()
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
            self.reload()

    def reload(self) -> None:
        hotkeys = self.settings["hotkeys"]
        section = hotkeys.get(self._context) or {}
        self.toggle_binding = frozenset(section.get("toggle") or [])
        self.hold_binding = (
            frozenset(section.get("hold") or [])
            if hotkeys.get("hold_enabled", True)
            else frozenset()
        )
        self.emergency_binding = frozenset(section.get("emergency") or [])
        self.block_keys = bool(hotkeys.get("block_keys", True))

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

    # ----------------------------------------------------------------- events
    def _handle_key(self, vk: int, down: bool, injected: bool, ts: float) -> bool:
        if injected:
            return False

        if self._capturing:
            self._capture_key(vk, down)
            return True

        if down:
            repeat = vk in self._pressed
            self._pressed.add(vk)
            pressed = frozenset(self._pressed)

            action = None
            if self.emergency_binding and pressed == self.emergency_binding:
                action = "emergency"
            elif not repeat and self.toggle_binding and pressed == self.toggle_binding:
                action = "toggle"
            elif not repeat and self.hold_binding and pressed == self.hold_binding:
                action = "hold"

            if action:
                if self.block_keys:
                    self._blocked.add(vk)
                if action == "emergency":
                    self.emergency_triggered.emit()
                elif action == "toggle":
                    self.toggle_triggered.emit()
                else:
                    self._hold_active = True
                    self.hold_started.emit()
                return self.block_keys

            if repeat and vk in self._blocked:
                return True
            return False

        # key up — ALWAYS pass through so modifiers never stick
        self._pressed.discard(vk)
        self._blocked.discard(vk)
        if self._hold_active and not self.hold_binding <= self._pressed:
            self._hold_active = False
            self.hold_ended.emit()
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

    def release_all(self) -> None:
        self._pressed.clear()
        self._blocked.clear()
        self._hold_active = False
