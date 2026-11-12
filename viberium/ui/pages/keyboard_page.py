"""Keyboard auto clicker page."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.vkeys import MODIFIER_VKS, normalize_vk
from ...core.winapi import combo_label, vk_name
from ...i18n import tr
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
    changed = Signal(object)
    capture_cancelled = Signal()

    def __init__(self, manager, vk: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._vk = int(vk)
        self._combo: list[int] = [int(vk)] if vk else []
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
        combo: list[int] = []
        if keys:
            for key in keys:
                code = normalize_vk(key)
                if code > 0 and code not in combo:
                    combo.append(code)
            candidates = [key for key in combo if key not in MODIFIER_VKS]
            self._vk = candidates[-1] if candidates else combo[-1]
            self._combo = combo
        self._refresh()
        if combo:
            self.changed.emit(list(self._combo))

    def _refresh(self) -> None:
        self.setProperty("capturing", "false")
        repolish(self)
        if self._combo:
            self.setText(combo_label(self._combo))
        else:
            self.setText(tr("keyboard.press"))

    def set_key(self, vk: int) -> None:
        self.set_combo([vk])

    def set_combo(self, combo: list[int]) -> None:
        self._combo = []
        for value in combo:
            code = normalize_vk(value)
            if code > 0 and code not in self._combo:
                self._combo.append(code)
        self._vk = self._combo[-1] if self._combo else 0
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

        self._cfg = cfg
        self._key_rows_layout = QVBoxLayout()
        self._key_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._key_rows_layout.setSpacing(8)
        card.body.addLayout(self._key_rows_layout)
        self.key_buttons: list[KeyButton] = []
        self.key_row_widgets: list[QWidget] = []
        self.key_labels: list[QLabel] = []
        self.up_buttons: list[QPushButton] = []
        self.down_buttons: list[QPushButton] = []
        self.remove_buttons: list[QPushButton] = []

        add_button = QPushButton("+  " + tr("keyboard.add_key"))
        add_button.setObjectName("GhostButton")
        add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_button.clicked.connect(lambda: self._add_key_row([]))
        card.add(add_button)

        self.mode_control = SegmentedControl(
            [
                ("simultaneous", tr("keyboard.mode.simultaneous")),
                ("sequence", tr("keyboard.mode.sequence")),
            ],
            str(cfg.get("key_mode", "simultaneous")),
        )
        self.mode_control.changed.connect(self._set_mode)
        card.add(form_row(tr("keyboard.mode"), self.mode_control))

        self.mode_hint = hint("")
        card.add(self.mode_hint)

        self.sequence_delay_input = NumberInput(
            int(cfg.get("sequence_delay_ms", 25)), 0, 5000, 5,
            suffix=tr("unit.ms"), width=124,
        )
        self.sequence_delay_input.valueChanged.connect(
            lambda value: self.save("keyboard", "sequence_delay_ms", value)
        )
        card.add(form_row(tr("keyboard.sequence_delay"), self.sequence_delay_input))
        self._update_mode_state()

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
        card.add(hint(tr("keyboard.combo_hint")))

        saved_keys = cfg.get("keys")
        if not saved_keys:
            saved_keys = [[int(cfg.get("key", 32))]]
        for combo in saved_keys:
            if isinstance(combo, (list, tuple)):
                self._add_key_row([int(vk) for vk in combo])
            else:
                self._add_key_row([int(combo)])
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
    def _add_key_row(self, combo: list[int]) -> None:
        index = len(self.key_buttons)
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        button = KeyButton(self.ctx.hotkeys, combo[-1] if combo else 0)
        button.setMinimumHeight(42)
        button.set_combo(combo)
        button.changed.connect(lambda combo, b=button: self._combo_captured(b, combo))
        name_label = label(tr("keyboard.combo", n=index + 1), "Hint")
        row.addWidget(name_label)
        row.addWidget(button, 1)

        up = QPushButton("↑")
        up.setObjectName("IconButton")
        up.setCursor(Qt.CursorShape.PointingHandCursor)
        up.setFixedWidth(34)
        up.setToolTip(tr("keyboard.move_up"))
        up.clicked.connect(lambda _checked=False, b=button: self._move_key(b, -1))
        row.addWidget(up)

        down = QPushButton("↓")
        down.setObjectName("IconButton")
        down.setCursor(Qt.CursorShape.PointingHandCursor)
        down.setFixedWidth(34)
        down.setToolTip(tr("keyboard.move_down"))
        down.clicked.connect(lambda _checked=False, b=button: self._move_key(b, 1))
        row.addWidget(down)

        remove = QPushButton("×")
        remove.setObjectName("IconButton")
        remove.setCursor(Qt.CursorShape.PointingHandCursor)
        remove.setFixedWidth(34)
        remove.setToolTip(tr("keyboard.remove_key"))
        remove.clicked.connect(lambda _checked=False, b=button: self._remove_key(b))
        row.addWidget(remove)

        self.key_buttons.append(button)
        self.key_row_widgets.append(row_widget)
        self.key_labels.append(name_label)
        self.up_buttons.append(up)
        self.down_buttons.append(down)
        self.remove_buttons.append(remove)
        self._key_rows_layout.addWidget(row_widget)
        self._renumber_rows()
        self._save_keys()

    def _combo_captured(self, button: KeyButton, combo: list[int]) -> None:
        self._save_keys()

    def _save_keys(self) -> None:
        keys = [list(getattr(button, "_combo", [])) for button in self.key_buttons]
        keys = [combo for combo in keys if combo]
        self.save("keyboard", "keys", keys)
        if keys:
            self.save("keyboard", "key", keys[0][-1])

    def _move_key(self, button: KeyButton, delta: int) -> None:
        index = self.key_buttons.index(button)
        target = index + delta
        if not 0 <= target < len(self.key_buttons):
            return
        for items in (self.key_buttons, self.key_row_widgets, self.key_labels):
            items[index], items[target] = items[target], items[index]
        self._rebuild_rows()
        self._save_keys()

    def _remove_key(self, button: KeyButton) -> None:
        if len(self.key_buttons) <= 1:
            return
        index = self.key_buttons.index(button)
        self.key_buttons.pop(index)
        self.key_labels.pop(index)
        self.up_buttons.pop(index)
        self.down_buttons.pop(index)
        self.remove_buttons.pop(index)
        widget = self.key_row_widgets.pop(index)
        self._key_rows_layout.removeWidget(widget)
        widget.deleteLater()
        self._renumber_rows()
        self._save_keys()

    def _rebuild_rows(self) -> None:
        for widget in self.key_row_widgets:
            self._key_rows_layout.removeWidget(widget)
        for widget in self.key_row_widgets:
            self._key_rows_layout.addWidget(widget)
        self._renumber_rows()

    def _renumber_rows(self) -> None:
        count = len(self.key_buttons)
        for index, name_label in enumerate(self.key_labels):
            name_label.setText(tr("keyboard.combo", n=index + 1))
        for index, up in enumerate(self.up_buttons):
            up.setEnabled(index > 0)
        for index, down in enumerate(self.down_buttons):
            down.setEnabled(index < count - 1)
        for remove in self.remove_buttons:
            remove.setEnabled(count > 1)

    def _set_mode(self, mode: str) -> None:
        self.save("keyboard", "key_mode", mode)
        self._update_mode_state()

    def _update_mode_state(self) -> None:
        sequence = self.mode_control.value() == "sequence"
        self.sequence_delay_input.setEnabled(sequence)
        self.mode_hint.setText(
            tr("keyboard.mode.sequence.hint" if sequence else "keyboard.mode.simultaneous.hint")
        )

    def _apply_preset(self, vk: int) -> None:
        if not self.key_buttons:
            self._add_key_row([vk])
            return
        button = self.key_buttons[-1]
        button.set_combo([vk])
        self._save_keys()

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
