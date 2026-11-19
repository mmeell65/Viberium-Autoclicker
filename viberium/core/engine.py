"""Click / key press engine running in background threads."""

from __future__ import annotations

import random
import threading
import time
from collections import deque
from typing import Callable

from PySide6.QtCore import QObject, Signal

from . import winapi
from .vkeys import normalize_vk
from .winapi import IS_WINDOWS

CLICK_MULTIPLIER = {"single": 1, "double": 2, "triple": 3}


def normalize_keyboard_combinations(cfg: dict) -> list[list[int]]:
    """Normalize saved key combinations, including legacy single-key configs."""
    raw_keys = cfg.get("keys")
    if raw_keys is None:
        raw_keys = [[cfg.get("key", 32)]]
    if not isinstance(raw_keys, (list, tuple)):
        raw_keys = [raw_keys]
    combinations: list[list[int]] = []
    for item in raw_keys:
        values = item if isinstance(item, (list, tuple)) else [item]
        combo: list[int] = []
        for value in values:
            try:
                vk = normalize_vk(int(value))
            except (TypeError, ValueError):
                continue
            if vk > 0 and vk not in combo:
                combo.append(vk)
        if combo:
            combinations.append(combo)
    return combinations


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


def target_process_of(settings) -> str:
    """Одно целевое окно для всех вкладок ("" — работать в любом окне)."""
    try:
        return str((settings["hotkeys"] or {}).get("target_process") or "")
    except Exception:
        return ""


def window_title_matches(target: str, title: str) -> bool:
    """True, если заголовок окна подходит под выбранный процесс (вхождение)."""
    target = (target or "").strip().lower()
    if not target:
        return True
    return target in (title or "").lower()


_TARGET_LOCK = threading.Lock()
_TARGET_PROCESS = ""


def set_target_process(value: str) -> None:
    """Задаёт общее целевое окно и сохраняет его в настройках."""
    global _TARGET_PROCESS
    with _TARGET_LOCK:
        _TARGET_PROCESS = str(value or "").strip()


def current_target_process() -> str:
    with _TARGET_LOCK:
        return _TARGET_PROCESS


def sync_target_process(settings) -> str:
    """Читает сохранённый таргет и запоминает его для рабочих потоков."""
    set_target_process(target_process_of(settings))
    return current_target_process()


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
            return window_title_matches(target, winapi.get_foreground_window_title())
        except Exception:
            return False

    def stop(self, wait: bool = False) -> None:
        thread = self._thread
        if thread is not None:
            self._stop.set()
            if wait:
                thread.join(timeout=0.6)

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
        target_process = current_target_process()
        ignore_modifiers = bool(cfg.get("ignore_modifiers", False))

        if delay and not precise_sleep(delay, stop):
            return "stopped"

        origin = winapi.cursor_pos()
        started = time.perf_counter()
        periods: deque[float] = deque(maxlen=25)
        count = 0
        last_emit = 0.0
        last_loop = started
        failures = 0

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

            # Shift/Ctrl/Alt physically held by the user turn an injected click
            # into a *modified* click, which many programs ignore or handle
            # differently. In that mode the modifiers are lifted for the click
            # and pressed back right after it.
            released = winapi.release_modifiers() if ignore_modifiers else []
            try:
                accepted = True
                for index in range(per_click):
                    accepted = winapi.mouse_down(button) and accepted
                    if hold:
                        if not precise_sleep(hold, stop):
                            winapi.mouse_up(button)
                            return "stopped"
                    accepted = winapi.mouse_up(button) and accepted
                    if index < per_click - 1 and not precise_sleep(0.025, stop):
                        return "stopped"
            finally:
                winapi.restore_modifiers(released)

            if not accepted:
                failures += 1
                if failures >= 5:
                    self._emit_stats("mouse", count, periods, time.perf_counter() - started)
                    return "error: input_blocked"
            else:
                failures = 0

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
        combinations = normalize_keyboard_combinations(cfg)
        if not combinations:
            try:
                fallback = normalize_vk(int(cfg.get("key", 32)))
            except (TypeError, ValueError):
                fallback = 32
            combinations = [[fallback if fallback > 0 else 32]]
        mode = str(cfg.get("key_mode", "simultaneous"))
        sequence_delay = max(int(cfg.get("sequence_delay_ms", 25)), 0) / 1000.0
        interval = max(int(cfg.get("interval_ms", 100)), 1) / 1000.0
        spread = min(max(float(cfg.get("randomize", 0)), 0.0), 100.0) / 100.0
        hold = max(int(cfg.get("hold_ms", 0)), 0) / 1000.0
        limit_presses = max(int(cfg.get("limit_presses", 0)), 0)
        limit_seconds = max(int(cfg.get("limit_seconds", 0)), 0)
        delay = max(int(cfg.get("start_delay_ms", 0)), 0) / 1000.0
        target_process = current_target_process()

        if delay and not precise_sleep(delay, stop):
            return "stopped"

        started = time.perf_counter()
        periods: deque[float] = deque(maxlen=25)
        count = 0
        last_emit = 0.0
        last_loop = started

        pressed: list[int] = []
        try:
            while not stop.is_set():
                # Если выбран целевой процесс и активное окно не совпадает — ждём
                if target_process and not self._window_matches(target_process):
                    if not precise_sleep(0.05, stop):
                        break
                    continue

                if mode == "sequence":
                    press_groups = combinations
                else:
                    # In simultaneous mode all configured keys are held together.
                    merged: list[int] = []
                    for combo in combinations:
                        for vk in combo:
                            if vk not in merged:
                                merged.append(vk)
                    press_groups = [merged]

                for group_index, combo in enumerate(press_groups):
                    for vk in combo:
                        winapi.key_down(vk)
                        pressed.append(vk)
                    if hold and not precise_sleep(hold, stop):
                        for vk in reversed(combo):
                            winapi.key_up(vk)
                            if vk in pressed:
                                pressed.remove(vk)
                        return "stopped"
                    for vk in reversed(combo):
                        winapi.key_up(vk)
                        if vk in pressed:
                            pressed.remove(vk)
                    if (
                        mode == "sequence"
                        and group_index < len(press_groups) - 1
                        and not precise_sleep(sequence_delay, stop)
                    ):
                        return "stopped"

                now = time.perf_counter()
                periods.append(max(now - last_loop, 0.0005))
                last_loop = now
                count += len(combinations) if mode == "sequence" else 1
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
        finally:
            # Never leave a key stuck down if the worker stops unexpectedly.
            for vk in reversed(pressed):
                winapi.key_up(vk)

        self._emit_stats("keyboard", count, periods, time.perf_counter() - started)
        return "stopped"

    # ------------------------------------------------------------------ stats
    def _emit_stats(self, mode: str, count: int, periods: deque, elapsed: float) -> None:
        self._count = count
        cps = 1.0 / (sum(periods) / len(periods)) if periods else 0.0
        self.stats.emit(mode, count, cps, elapsed)
