"""Macro recording, storage and playback."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ..config import appdata_dir
from . import winapi
from .hooks import InputHub

BUTTON_BY_KIND = {
    "left_down": "left",
    "left_up": "left",
    "right_down": "right",
    "right_up": "right",
    "middle_down": "middle",
    "middle_up": "middle",
}


@dataclass
class Macro:
    name: str
    events: list[dict] = field(default_factory=list)
    duration: float = 0.0
    created: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration": round(self.duration, 3),
            "created": self.created or datetime.now().isoformat(timespec="seconds"),
            "events": self.events,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Macro":
        events = data.get("events") or []
        if not isinstance(events, list):
            events = []
        return cls(
            name=str(data.get("name") or "macro"),
            events=events,
            duration=float(data.get("duration") or 0.0),
            created=str(data.get("created") or ""),
        )


class MacroStore:
    def __init__(self, directory: Path | None = None) -> None:
        self.dir = directory or (appdata_dir() / "macros")

    def names(self) -> list[str]:
        if not self.dir.exists():
            return []
        return sorted(path.stem for path in self.dir.glob("*.json"))

    def path_for(self, name: str) -> Path:
        return self.dir / f"{name}.json"

    def load(self, name: str) -> Macro | None:
        return self.load_path(self.path_for(name))

    @staticmethod
    def load_path(path: Path) -> Macro | None:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        return Macro.from_dict(data)

    def save(self, macro: Macro) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path_for(macro.name).write_text(
            json.dumps(macro.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def delete(self, name: str) -> None:
        try:
            self.path_for(name).unlink()
        except OSError:
            pass

    @staticmethod
    def export(macro: Macro, path: str) -> None:
        Path(path).write_text(
            json.dumps(macro.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )


class MacroRecorder(QObject):
    tick = Signal(int, float)       # actions, seconds
    finished = Signal(object)       # Macro

    def __init__(self, hub: InputHub, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.hub = hub
        self._events: list[dict] = []
        self._active = False
        self._start = 0.0
        self._last_move = (0.0, 0, 0)
        self._last_tick = 0.0
        self._lock = threading.Lock()
        self.record_moves = True

    @property
    def active(self) -> bool:
        return self._active

    def start(self) -> None:
        if self._active:
            return
        self._events = []
        self._active = True
        self._start = time.perf_counter()
        self._last_move = (0.0, 0, 0)
        self.hub.add_key_listener(self._on_key)
        self.hub.add_mouse_listener(self._on_mouse)

    def stop(self) -> Macro | None:
        if not self._active:
            return None
        self._active = False
        self.hub.remove_key_listener(self._on_key)
        self.hub.remove_mouse_listener(self._on_mouse)
        duration = time.perf_counter() - self._start
        macro = Macro(
            name=datetime.now().strftime("%Y-%m-%d %H-%M-%S"),
            events=self._events,
            duration=duration,
            created=datetime.now().isoformat(timespec="seconds"),
        )
        self.finished.emit(macro)
        return macro

    # ------------------------------------------------------- hook callbacks
    def _stamp(self, ts: float) -> float:
        return round(max(ts - self._start, 0.0), 4)

    def _maybe_tick(self, ts: float) -> None:
        if ts - self._last_tick < 0.15:
            return
        self._last_tick = ts
        self.tick.emit(len(self._events), round(ts - self._start, 2))

    def _on_key(self, vk: int, down: bool, injected: bool, ts: float) -> bool:
        if not self._active or injected:
            return False
        event = {"t": self._stamp(ts), "type": "key_down" if down else "key_up", "vk": int(vk)}
        with self._lock:
            self._events.append(event)
        self._maybe_tick(ts)
        return False

    def _on_mouse(self, kind: str, x: int, y: int, delta: int, injected: bool, ts: float) -> bool:
        if not self._active or injected:
            return False
        if kind == "wheel" or kind == "hwheel":
            with self._lock:
                self._events.append(
                    {"t": self._stamp(ts), "type": "wheel", "delta": int(delta), "x": x, "y": y}
                )
            self._maybe_tick(ts)
            return False
        button = BUTTON_BY_KIND.get(kind)
        if button is None:
            if kind == "move" and self.record_moves:
                last_ts, last_x, last_y = self._last_move
                if ts - last_ts < 0.035 and abs(x - last_x) < 6 and abs(y - last_y) < 6:
                    return False
                self._last_move = (ts, x, y)
                with self._lock:
                    self._events.append(
                        {"t": self._stamp(ts), "type": "move", "x": int(x), "y": int(y)}
                    )
                self._maybe_tick(ts)
            return False
        with self._lock:
            self._events.append(
                {
                    "t": self._stamp(ts),
                    "type": "down" if kind.endswith("_down") else "up",
                    "button": button,
                    "x": int(x),
                    "y": int(y),
                }
            )
        self._maybe_tick(ts)
        return False


class MacroPlayer(QObject):
    finished = Signal()
    progress = Signal(float)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def playing(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def play(self, macro: Macro, speed: float = 1.0, loops: int = 1) -> bool:
        if self.playing or not macro.events:
            return False
        speed = max(float(speed), 0.1)
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, args=(macro, speed, max(int(loops), 1)), daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    def _run(self, macro: Macro, speed: float, loops: int) -> None:
        total = max(macro.duration, 0.001)
        try:
            for _ in range(loops):
                start = time.perf_counter()
                for event in macro.events:
                    if self._stop.is_set():
                        return
                    target = start + float(event.get("t", 0.0)) / speed
                    while True:
                        remaining = target - time.perf_counter()
                        if remaining <= 0:
                            break
                        if self._stop.wait(min(remaining, 0.02)):
                            return
                    self._apply(event)
                    self.progress.emit(min(float(event.get("t", 0.0)) / total, 1.0))
        finally:
            self._release()
            self._thread = None
            self.finished.emit()

    @staticmethod
    def _apply(event: dict) -> None:
        kind = event.get("type")
        if kind == "move":
            winapi.set_cursor_pos(int(event.get("x", 0)), int(event.get("y", 0)))
        elif kind == "down":
            winapi.mouse_down(str(event.get("button", "left")))
        elif kind == "up":
            winapi.mouse_up(str(event.get("button", "left")))
        elif kind == "wheel":
            winapi.mouse_wheel(int(event.get("delta", 0)))
        elif kind == "key_down":
            winapi.key_down(int(event.get("vk", 0)))
        elif kind == "key_up":
            winapi.key_up(int(event.get("vk", 0)))

    @staticmethod
    def _release() -> None:
        for button in ("left", "right", "middle"):
            winapi.mouse_up(button)
