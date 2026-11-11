"""Click / key press engine running in background threads."""

from __future__ import annotations

import random
import threading
import time
from collections import deque
from typing import Callable

from PySide6.QtCore import QObject, Signal

from . import winapi
from .winapi import IS_WINDOWS

CLICK_MULTIPLIER = {"single": 1, "double": 2, "triple": 3}


def precise_sleep(seconds: float, stop: threading.Event) -> bool:
    """Sleep for `seconds`, returning False if `stop` was set meanwhile."""
    if seconds <= 0:
        return not stop.is_set()
    deadline = time.perf_counter() + seconds
    while True:
        if stop.is_set():
            return False
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return True
        if remaining > 0.003:
            time.sleep(min(remaining - 0.002, 0.02))
        else:
            time.sleep(0)


class ClickEngine(QObject):
    """Runs one worker at a time (mouse or keyboard)."""

    state_changed = Signal(bool, str)          # running, mode
    stats = Signal(str, int, float, float)     # mode, count, cps, elapsed
    finished = Signal(str, str)                # mode, reason

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._mode = ""
        self._count = 0
        self._started_at = 0.0

    # ------------------------------------------------------------------ state
    @property
    def mode(self) -> str:
        return self._mode

    @property
    def count(self) -> int:
        return self._count

    def is_running(self, mode: str | None = None) -> bool:
        running = self._thread is not None and self._thread.is_alive()
        if mode is None:
            return running
        return running and self._mode == mode

    # ------------------------------------------------------------------ start
    def start_mouse(self, cfg: dict) -> bool:
        return self._start("mouse", lambda stop: self._mouse_worker(cfg, stop))

    def start_keyboard(self, cfg: dict) -> bool:
        return self._start("keyboard", lambda stop: self._keyboard_worker(cfg, stop))

    def _start(self, mode: str, target: Callable[[threading.Event], None]) -> bool:
        if self.is_running():
            return False
        self._stop = threading.Event()
        self._mode = mode
        self._count = 0
        self._started_at = time.perf_counter()
        self._thread = threading.Thread(target=self._guard, args=(mode, target), daemon=True)
        self._thread.start()
        self.state_changed.emit(True, mode)
        return True

    def _guard(self, mode: str, target: Callable[[threading.Event], None]) -> None:
        reason = "stopped"
        try:
            reason = target(self._stop) or "stopped"
        except Exception as exc:  # keep the UI alive on unexpected errors
            reason = f"error: {exc}"
        finally:
            # never leave a button or key stuck down
            winapi.mouse_up("left")
            winapi.mouse_up("right")
            winapi.mouse_up("middle")
            self._stop.set()
            self._thread = None
            self.state_changed.emit(False, mode)
            self.finished.emit(mode, reason)

    def _window_matches(self, target: str) -> bool:
        """Проверяет, совпадает ли заголовок активного окна с target (вхождение, без учёта регистра)."""
        if not IS_WINDOWS:
            return True
        try:
            title = winapi.get_foreground_window_title()
            return target.lower() in title.lower()
        except Exception:
            return False

    def stop(self, wait: bool = False) -> None:
        thread = self._thread
        if thread is not None:
            self._stop.set()
            if wait:
                thread.join(timeout=0.6)

    def toggle_mouse(self, cfg: dict) -> None:
        if self.is_running("mouse"):
            self.stop()
        else:
            self.stop()
            self.start_mouse(cfg)

    # ---------------------------------------------------------------- workers
    def _mouse_worker(self, cfg: dict, stop: threading.Event) -> str:
        button = cfg.get("button", "left")
        per_click = CLICK_MULTIPLIER.get(cfg.get("click_type", "single"), 1)
        interval = max(int(cfg.get("interval_ms", 100)), 1) / 1000.0
        spread = min(max(float(cfg.get("randomize", 0)), 0.0), 100.0) / 100.0
        hold = max(int(cfg.get("hold_ms", 0)), 0) / 1000.0
        jitter = max(int(cfg.get("jitter_px", 0)), 0)
        fixed = cfg.get("position_mode") == "fixed"
        fx, fy = int(cfg.get("fixed_x", 0)), int(cfg.get("fixed_y", 0))
        limit_clicks = max(int(cfg.get("limit_clicks", 0)), 0)
        limit_seconds = max(int(cfg.get("limit_seconds", 0)), 0)
        stop_on_move = bool(cfg.get("stop_on_move", False))
        delay = max(int(cfg.get("start_delay_ms", 0)), 0) / 1000.0
        target_process = cfg.get("target_process", "") or ""

        if delay and not precise_sleep(delay, stop):
            return "stopped"

        origin = winapi.cursor_pos()
        started = time.perf_counter()
        periods: deque[float] = deque(maxlen=25)
        count = 0
        last_emit = 0.0
        last_loop = started

        while not stop.is_set():
            # Если выбран целевой процесс и активное окно не совпадает — ждём
            if target_process and not self._window_matches(target_process):
                if not precise_sleep(0.05, stop):
                    break
                continue

            if fixed:
                x, y = fx, fy
                if jitter:
                    x += random.randint(-jitter, jitter)
                    y += random.randint(-jitter, jitter)
                winapi.set_cursor_pos(x, y)
            elif jitter:
                cx, cy = winapi.cursor_pos()
                winapi.set_cursor_pos(
                    cx + random.randint(-jitter, jitter),
                    cy + random.randint(-jitter, jitter),
                )

            for index in range(per_click):
                winapi.mouse_down(button)
                if hold:
                    if not precise_sleep(hold, stop):
                        winapi.mouse_up(button)
                        return "stopped"
                winapi.mouse_up(button)
                if index < per_click - 1 and not precise_sleep(0.025, stop):
                    return "stopped"

            now = time.perf_counter()
            periods.append(max(now - last_loop, 0.0005))
            last_loop = now
            count += per_click
            elapsed = now - started

            if limit_clicks and count >= limit_clicks:
                self._emit_stats("mouse", count, periods, elapsed)
                return "limit"
            if limit_seconds and elapsed >= limit_seconds:
                self._emit_stats("mouse", count, periods, elapsed)
                return "limit"
            if stop_on_move and not fixed:
                cx, cy = winapi.cursor_pos()
                if abs(cx - origin[0]) > 6 or abs(cy - origin[1]) > 6:
                    self._emit_stats("mouse", count, periods, elapsed)
                    return "moved"

            if now - last_emit >= 0.12:
                self._emit_stats("mouse", count, periods, elapsed)
                last_emit = now

            wait = interval * (1.0 + random.uniform(-spread, spread)) if spread else interval
            if not precise_sleep(max(wait, 0.001), stop):
                break

        self._emit_stats("mouse", count, periods, time.perf_counter() - started)
        return "stopped"

    def _keyboard_worker(self, cfg: dict, stop: threading.Event) -> str:
        vk = int(cfg.get("key", 32))
        interval = max(int(cfg.get("interval_ms", 100)), 1) / 1000.0
        spread = min(max(float(cfg.get("randomize", 0)), 0.0), 100.0) / 100.0
        hold = max(int(cfg.get("hold_ms", 0)), 0) / 1000.0
        limit_presses = max(int(cfg.get("limit_presses", 0)), 0)
        limit_seconds = max(int(cfg.get("limit_seconds", 0)), 0)
        delay = max(int(cfg.get("start_delay_ms", 0)), 0) / 1000.0
        target_process = cfg.get("target_process", "") or ""

        if delay and not precise_sleep(delay, stop):
            return "stopped"

        started = time.perf_counter()
        periods: deque[float] = deque(maxlen=25)
        count = 0
        last_emit = 0.0
        last_loop = started

        while not stop.is_set():
            # Если выбран целевой процесс и активное окно не совпадает — ждём
            if target_process and not self._window_matches(target_process):
                if not precise_sleep(0.05, stop):
                    break
                continue

            winapi.key_down(vk)
            if hold and not precise_sleep(hold, stop):
                winapi.key_up(vk)
                return "stopped"
            winapi.key_up(vk)

            now = time.perf_counter()
            periods.append(max(now - last_loop, 0.0005))
            last_loop = now
            count += 1
            elapsed = now - started

            if limit_presses and count >= limit_presses:
                self._emit_stats("keyboard", count, periods, elapsed)
                return "limit"
            if limit_seconds and elapsed >= limit_seconds:
                self._emit_stats("keyboard", count, periods, elapsed)
                return "limit"
            if now - last_emit >= 0.12:
                self._emit_stats("keyboard", count, periods, elapsed)
                last_emit = now

            wait = interval * (1.0 + random.uniform(-spread, spread)) if spread else interval
            if not precise_sleep(max(wait, 0.001), stop):
                break

        self._emit_stats("keyboard", count, periods, time.perf_counter() - started)
        return "stopped"

    # ------------------------------------------------------------------ stats
    def _emit_stats(self, mode: str, count: int, periods: deque, elapsed: float) -> None:
        self._count = count
        cps = 1.0 / (sum(periods) / len(periods)) if periods else 0.0
        self.stats.emit(mode, count, cps, elapsed)
