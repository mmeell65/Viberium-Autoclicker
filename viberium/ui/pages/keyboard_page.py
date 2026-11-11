"""Keyboard auto clicker page."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ...core.hotkeys import MODIFIER_VKS
from ...core.winapi import vk_name
from ...i18n import tr
from .. import icons
from ..theme import ACCENT
from ..widgets import (
    Card,
    HeroCard,
    NumberInput,
    SegmentedControl,
    SliderRow,
    chip,
    divider,
    form_row,
    hint,
    label,
    repolish,
)
from .base import BasePage, Context, hotkey_hint
from .mouse_page import format_time

PRESET_KEYS = (0x20, 0x0D, 0x45, 0x51, 0x46, 0x31)


class KeyButton(QPushButton):
    changed = Signal(int)
    capture_cancelled = Signal()

    def __init__(self, manager, vk: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._vk = int(vk)
        self._waiting = False
        self.setObjectName("KeyTile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(50)
        self.clicked.connect(self._begin)
        self.manager.captured.connect(self._on_captured)
        self.capture_cancelled.connect(self._on_capture_cancelled)
        self._refresh()

    def _on_capture_cancelled(self) -> None:
        if self._waiting:
            self._waiting = False
            self.setProperty("capturing", "false")
            repolish(self)
            self._refresh()

    def _begin(self) -> None:
        if self._waiting:
            self.manager.cancel_capture()
            self._waiting = False
            self._refresh()
            return
        self._waiting = True
        self.setProperty("capturing", "true")
        repolish(self)
        self.setText(tr("keyboard.press"))
        self.manager.begin_capture(self)

    def _on_captured(self, keys) -> None:
        if not self._waiting:
            return
        self._waiting = False
        if keys:
            candidates = [key for key in keys if key not in MODIFIER_VKS]
            if candidates:
                self._vk = candidates[-1]
                self.changed.emit(self._vk)
        self._refresh()

    def _refresh(self) -> None:
        self.setProperty("capturing", "false")
        repolish(self)
        self.setText(vk_name(self._vk))

    def key_vk(self) -> int:
        return self._vk

    def set_key(self, vk: int) -> None:
        self._vk = int(vk)
        self._refresh()


class KeyboardPage(BasePage):
    def __init__(self, ctx: Context, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        cfg = self.settings["keyboard"]

        self.add_header(tr("keyboard.title"), tr("keyboard.subtitle"))
        self.hero = HeroCard(
            [tr("stat.presses"), tr("stat.pps"), tr("stat.time")],
            hotkey_hint(self.settings, "keyboard"),
        )
        self.hero.start_clicked.connect(self._toggle)
        self.body.addWidget(self.hero)

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.addWidget(self._build_key_card(cfg), 0, 0)
        grid.addWidget(self._build_interval_card(cfg), 0, 1)
        grid.addWidget(self._build_limits_card(cfg), 1, 0)
        grid.addWidget(self._build_timing_card(cfg), 1, 1)
        self.body.addLayout(grid)

        self.body.addWidget(
            self.hotkey_card(
                "keyboard",
                [
                    ("toggle", "settings.hotkey.toggle", None),
                    ("hold", "settings.hotkey.hold", "settings.hotkey.hold.hint"),
                    ("emergency", "settings.hotkey.emergency", "settings.hotkey.emergency.hint"),
                ],
                title=tr("card.hotkeys"),
                icon_name="keyboard",
            )
        )
        self.body.addStretch(1)

    # ------------------------------------------------------------------- cards
    def _build_key_card(self, cfg: dict) -> QWidget:
        card = Card(tr("card.key"), icon_name="keyboard")

        self.key_button = KeyButton(self.ctx.hotkeys, int(cfg.get("key", 32)))
        self.key_button.changed.connect(lambda vk: self.save("keyboard", "key", vk))
        card.add(self.key_button)

        presets = QWidget()
        row = QHBoxLayout(presets)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(label(tr("keyboard.presets"), "Hint"), 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        for vk in PRESET_KEYS:
            button = chip(vk_name(vk))
            button.clicked.connect(lambda _checked=False, code=vk: self._apply_preset(code))
            row.addWidget(button)
        card.add(presets)

        card.add(divider())
        card.add(hint(tr("keyboard.hint")))
        return card

    def _build_interval_card(self, cfg: dict) -> QWidget:
        card = Card(tr("card.interval"), icon_name="clock")

        self.interval_input = NumberInput(
            int(cfg.get("interval_ms", 100)), 1, 3_600_000, 10, suffix=tr("unit.ms"), width=124
        )
        self.interval_input.valueChanged.connect(
            lambda value: self.save("keyboard", "interval_ms", value)
        )
        card.add(form_row(tr("keyboard.interval"), self.interval_input))

        self.random_slider = SliderRow(
            tr("interval.random"),
            0,
            100,
            int(cfg.get("randomize", 0)),
            "%",
            tr("interval.random.hint"),
        )
        self.random_slider.valueChanged.connect(
            lambda value: self.save("keyboard", "randomize", value)
        )
        card.add(self.random_slider)
        return card

    def _build_limits_card(self, cfg: dict) -> QWidget:
        card = Card(tr("card.limits"), icon_name="shield")

        self.limit_presses = NumberInput(
            int(cfg.get("limit_presses", 0)), 0, 100_000_000, 10, width=124
        )
        self.limit_presses.valueChanged.connect(
            lambda value: self.save("keyboard", "limit_presses", value)
        )
        card.add(form_row(tr("keyboard.limit_presses"), self.limit_presses, tr("value.unlimited")))

        self.limit_seconds = NumberInput(
            int(cfg.get("limit_seconds", 0)), 0, 86400, 10, suffix=tr("unit.sec.short"), width=124
        )
        self.limit_seconds.valueChanged.connect(
            lambda value: self.save("keyboard", "limit_seconds", value)
        )
        card.add(form_row(tr("limits.seconds"), self.limit_seconds, tr("value.unlimited")))
        return card

    def _build_timing_card(self, cfg: dict) -> QWidget:
        card = Card(tr("card.timing"), icon_name="bolt")

        self.hold_input = NumberInput(
            int(cfg.get("hold_ms", 0)), 0, 60000, 10, suffix=tr("unit.ms"), width=124
        )
        self.hold_input.valueChanged.connect(lambda value: self.save("keyboard", "hold_ms", value))
        card.add(form_row(tr("hold.ms"), self.hold_input))

        self.start_delay = NumberInput(
            int(cfg.get("start_delay_ms", 0)), 0, 60000, 100, suffix=tr("unit.ms"), width=124
        )
        self.start_delay.valueChanged.connect(
            lambda value: self.save("keyboard", "start_delay_ms", value)
        )
        card.add(form_row(tr("start_delay.ms"), self.start_delay))
        return card

    # ----------------------------------------------------------------- actions
    def _apply_preset(self, vk: int) -> None:
        self.key_button.set_key(vk)
        self.save("keyboard", "key", vk)

    def _toggle(self) -> None:
        engine = self.ctx.engine
        if engine.is_running():
            engine.stop()
            return
        engine.stop(wait=True)
        engine.start_keyboard(self.settings["keyboard"])

    def cleanup(self) -> None:
        self.ctx.hotkeys.cancel_capture()

    # ------------------------------------------------------------ engine hooks
    def on_engine_state(self, running: bool, mode: str) -> None:
        if mode == "keyboard":
            self.hero.set_running(running)

    def on_stats(self, mode: str, count: int, cps: float, elapsed: float) -> None:
        if mode != "keyboard":
            return
        self.hero.set_stats([f"{count:,}".replace(",", " "), f"{cps:0.1f}", format_time(elapsed)])
