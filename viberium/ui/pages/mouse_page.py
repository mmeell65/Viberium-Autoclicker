"""Mouse auto clicker page."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ...i18n import tr
from .. import icons
from ..theme import ACCENT
from ..widgets import (
    Card,
    HeroCard,
    NumberInput,
    SegmentedControl,
    SliderRow,
    ToggleSwitch,
    chip,
    divider,
    form_row,
    hint,
    label,
)
from .base import BasePage, Context, hotkey_hint

PRESETS = (10, 50, 100, 500)


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:0.1f} {tr('unit.sec')}"
    minutes, rest = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}:{rest:02d}"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{rest:02d}"


class MousePage(BasePage):
    def __init__(self, ctx: Context, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        cfg = self.settings["mouse"]

        self._picking = False
        self._countdown = 0
        self._pick_listener = self._on_pick_click
        self._pick_timer = QTimer(self)
        self._pick_timer.setInterval(1000)
        self._pick_timer.timeout.connect(self._tick_pick)

        self.add_header(tr("mouse.title"), tr("mouse.subtitle"))

        self.hero = HeroCard(
            [tr("stat.clicks"), tr("stat.cps"), tr("stat.time")],
            hotkey_hint(self.settings, "mouse"),
        )
        self.hero.start_clicked.connect(self._toggle)
        self.body.addWidget(self.hero)

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.addWidget(self._build_button_card(cfg), 0, 0)
        grid.addWidget(self._build_interval_card(cfg), 0, 1)
        grid.addWidget(self._build_position_card(cfg), 1, 0)
        grid.addWidget(self._build_limits_card(cfg), 1, 1)
        self.body.addLayout(grid)

        self.body.addWidget(
            self.hotkey_card(
                "mouse",
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
    def _build_button_card(self, cfg: dict) -> QWidget:
        card = Card(tr("card.button"), icon_name="mouse")

        self.button_seg = SegmentedControl(
            [
                ("left", tr("button.left")),
                ("right", tr("button.right")),
                ("middle", tr("button.middle")),
            ],
            cfg.get("button", "left"),
        )
        self.button_seg.changed.connect(lambda value: self.save("mouse", "button", value))
        card.add(self.button_seg)

        card.add(label(tr("card.click_type"), "FieldLabel"))
        self.type_seg = SegmentedControl(
            [
                ("single", tr("click.single")),
                ("double", tr("click.double")),
                ("triple", tr("click.triple")),
            ],
            cfg.get("click_type", "single"),
        )
        self.type_seg.changed.connect(lambda value: self.save("mouse", "click_type", value))
        card.add(self.type_seg)

        card.add(divider())
        self.hold_input = NumberInput(
            int(cfg.get("hold_ms", 0)), 0, 60000, 10, suffix=tr("unit.ms"), width=124
        )
        self.hold_input.valueChanged.connect(lambda value: self.save("mouse", "hold_ms", value))
        card.add(form_row(tr("hold.ms"), self.hold_input))
        return card

    def _build_interval_card(self, cfg: dict) -> QWidget:
        card = Card(tr("card.interval"), icon_name="clock")

        self.interval_input = NumberInput(
            int(cfg.get("interval_ms", 100)), 1, 3_600_000, 10, suffix=tr("unit.ms"), width=124
        )
        self.interval_input.valueChanged.connect(
            lambda value: self.save("mouse", "interval_ms", value)
        )
        card.add(form_row(tr("interval.ms"), self.interval_input))

        presets = QWidget()
        row = QHBoxLayout(presets)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        row.addWidget(label(tr("interval.presets"), "Hint"), 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        for preset in PRESETS:
            button = chip(f"{preset}")
            button.clicked.connect(lambda _checked=False, value=preset: self._apply_preset(value))
            row.addWidget(button)
        card.add(presets)

        self.random_slider = SliderRow(
            tr("interval.random"),
            0,
            100,
            int(cfg.get("randomize", 0)),
            "%",
            tr("interval.random.hint"),
        )
        self.random_slider.valueChanged.connect(lambda value: self.save("mouse", "randomize", value))
        card.add(self.random_slider)
        return card

    def _build_position_card(self, cfg: dict) -> QWidget:
        card = Card(tr("card.position"), icon_name="target")

        self.position_seg = SegmentedControl(
            [
                ("cursor", tr("position.cursor")),
                ("fixed", tr("position.fixed")),
            ],
            cfg.get("position_mode", "cursor"),
        )
        self.position_seg.changed.connect(self._on_position_mode)
        card.add(self.position_seg)

        coords = QWidget()
        coords_layout = QVBoxLayout(coords)
        coords_layout.setContentsMargins(0, 0, 0, 0)
        coords_layout.setSpacing(8)

        inputs = QWidget()
        inputs_layout = QHBoxLayout(inputs)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(8)

        self.x_input = NumberInput(
            int(cfg.get("fixed_x", 0)), -20000, 40000, 1, prefix="X", width=118
        )
        self.y_input = NumberInput(
            int(cfg.get("fixed_y", 0)), -20000, 40000, 1, prefix="Y", width=118
        )
        self.x_input.valueChanged.connect(lambda value: self.save("mouse", "fixed_x", value))
        self.y_input.valueChanged.connect(lambda value: self.save("mouse", "fixed_y", value))

        self.pick_button = QPushButton(tr("position.pick"))
        self.pick_button.setObjectName("GhostButton")
        self.pick_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pick_button.setIcon(icons.icon("target", ACCENT, 15))
        self.pick_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.pick_button.clicked.connect(self._start_pick)

        inputs_layout.addWidget(self.x_input)
        inputs_layout.addWidget(self.y_input)
        coords_layout.addWidget(inputs)
        coords_layout.addWidget(self.pick_button)
        card.add(coords)

        self.jitter_input = NumberInput(
            int(cfg.get("jitter_px", 0)), 0, 300, 1, suffix="px", width=124
        )
        self.jitter_input.valueChanged.connect(lambda value: self.save("mouse", "jitter_px", value))
        card.add(form_row(tr("position.jitter"), self.jitter_input))

        self._update_position_enabled(cfg.get("position_mode", "cursor"))
        return card

    def _build_limits_card(self, cfg: dict) -> QWidget:
        card = Card(tr("card.limits"), icon_name="shield")

        self.limit_clicks = NumberInput(
            int(cfg.get("limit_clicks", 0)), 0, 100_000_000, 10, width=124
        )
        self.limit_clicks.valueChanged.connect(
            lambda value: self.save("mouse", "limit_clicks", value)
        )
        card.add(form_row(tr("limits.clicks"), self.limit_clicks, tr("value.unlimited")))

        self.limit_seconds = NumberInput(
            int(cfg.get("limit_seconds", 0)), 0, 86400, 10, suffix=tr("unit.sec.short"), width=124
        )
        self.limit_seconds.valueChanged.connect(
            lambda value: self.save("mouse", "limit_seconds", value)
        )
        card.add(form_row(tr("limits.seconds"), self.limit_seconds, tr("value.unlimited")))

        self.stop_on_move = ToggleSwitch(bool(cfg.get("stop_on_move", False)))
        self.stop_on_move.toggled.connect(
            lambda checked: self.save("mouse", "stop_on_move", checked)
        )
        card.add(form_row(tr("limits.stop_on_move"), self.stop_on_move))

        card.add(divider())
        self.start_delay = NumberInput(
            int(cfg.get("start_delay_ms", 0)), 0, 60000, 100, suffix=tr("unit.ms"), width=124
        )
        self.start_delay.valueChanged.connect(
            lambda value: self.save("mouse", "start_delay_ms", value)
        )
        card.add(form_row(tr("start_delay.ms"), self.start_delay))
        return card

    # ----------------------------------------------------------------- actions
    def _apply_preset(self, value: int) -> None:
        self.interval_input.set_value(value)
        self.save("mouse", "interval_ms", value)

    def _on_position_mode(self, mode: str) -> None:
        self.save("mouse", "position_mode", mode)
        self._update_position_enabled(mode)

    def _update_position_enabled(self, mode: str) -> None:
        fixed = mode == "fixed"
        self.x_input.setEnabled(fixed)
        self.y_input.setEnabled(fixed)
        self.pick_button.setEnabled(fixed)

    def _start_pick(self) -> None:
        if self._picking:
            self._cancel_pick()
            return
        self._picking = True
        self._countdown = 3
        self.pick_button.setText(tr("position.picking", n=self._countdown))
        self.pick_button.setIcon(icons.icon("target", "#ffb454", 15))
        self._pick_timer.start()
        QTimer.singleShot(320, self._install_pick_listener)

    def _install_pick_listener(self) -> None:
        if self._picking:
            self.ctx.hub.add_mouse_listener(self._pick_listener)

    def _tick_pick(self) -> None:
        self._countdown -= 1
        if self._countdown <= 0:
            self._cancel_pick()
            return
        self.pick_button.setText(tr("position.picking", n=self._countdown))

    def _on_pick_click(self, kind: str, x: int, y: int, delta: int, injected: bool, ts: float) -> bool:
        if self._picking and kind == "left_down" and not injected:
            QTimer.singleShot(0, lambda: self._apply_pick(x, y))
        return False

    def _apply_pick(self, x: int, y: int) -> None:
        self._finish_pick()
        self.x_input.set_value(x)
        self.y_input.set_value(y)
        self.save("mouse", "fixed_x", x)
        self.save("mouse", "fixed_y", y)
        self.position_seg.set_value("fixed", emit=True)
        self.ctx.toast(tr("position.picked", x=x, y=y))

    def _finish_pick(self) -> None:
        self._picking = False
        self._pick_timer.stop()
        self.ctx.hub.remove_mouse_listener(self._pick_listener)
        self.pick_button.setText(tr("position.pick"))
        self.pick_button.setIcon(icons.icon("target", ACCENT, 15))

    def _cancel_pick(self) -> None:
        self._finish_pick()

    def cleanup(self) -> None:
        if self._picking:
            self._finish_pick()

    # ------------------------------------------------------------ engine hooks
    def _toggle(self) -> None:
        engine = self.ctx.engine
        if engine.is_running():
            engine.stop()
            return
        engine.stop(wait=True)
        engine.start_mouse(self.settings["mouse"])

    def on_engine_state(self, running: bool, mode: str) -> None:
        if mode == "mouse":
            self.hero.set_running(running)

    def on_stats(self, mode: str, count: int, cps: float, elapsed: float) -> None:
        if mode != "mouse":
            return
        self.hero.set_stats([f"{count:,}".replace(",", " "), f"{cps:0.1f}", format_time(elapsed)])
