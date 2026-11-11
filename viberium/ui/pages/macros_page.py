"""Macros page: record, store and replay input sequences."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.macros import Macro, MacroStore
from ...i18n import tr
from .. import icons
from ..theme import ACCENT, DIM, GREEN, MUTED, RED, TEXT
from ..widgets import (
    Card,
    NumberInput,
    SliderRow,
    divider,
    hint,
    icon_label,
    label,
    repolish,
)
from .base import BasePage, Context
from .mouse_page import format_time


class MacroRow(QWidget):
    play_requested = Signal(str)
    export_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, name: str, meta: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(12)

        layout.addWidget(icon_label("macro", ACCENT, 18))

        texts = QVBoxLayout()
        texts.setSpacing(1)
        name_label = label(name, "CardTitle")
        name_label.setStyleSheet("font-size: 10pt;")
        texts.addWidget(name_label)
        texts.addWidget(label(meta, "Hint"))
        layout.addLayout(texts, 1)

        for icon_name, color, slot, tooltip in (
            ("play", GREEN, self.play_requested, tr("btn.play")),
            ("save", DIM, self.export_requested, tr("btn.export")),
            ("trash", RED, self.delete_requested, tr("btn.delete")),
        ):
            button = QPushButton()
            button.setObjectName("WinButton")
            button.setFixedSize(32, 30)
            button.setIcon(icons.icon(icon_name, color, 16))
            button.setIconSize(QSize(16, 16))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _checked=False, sig=slot: sig.emit(name))
            layout.addWidget(button)


class MacrosPage(BasePage):
    def __init__(self, ctx: Context, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        self.add_header(tr("macros.title"), tr("macros.subtitle"))

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.addWidget(self._build_recorder_card(), 0, 0)
        grid.addWidget(self._build_playback_card(), 0, 1)
        self.body.addLayout(grid)

        self.body.addWidget(
            self.hotkey_card(
                "macros",
                [
                    ("play", "settings.hotkey.macro_play", None),
                    ("record", "settings.hotkey.macro_record", None),
                ],
                title=tr("card.hotkeys"),
                icon_name="keyboard",
            )
        )
        self.body.addWidget(self._build_library_card())
        self.body.addStretch(1)

        self.ctx.recorder.finished.connect(self._on_recorded)
        self.ctx.recorder.tick.connect(self._on_record_tick)
        self.ctx.player.finished.connect(self._on_player_finished)
        self.refresh()

    # ------------------------------------------------------------------- cards
    def _build_recorder_card(self) -> QWidget:
        card = Card(tr("card.recorder"), icon_name="record")

        self.record_button = QPushButton(tr("macros.record"))
        self.record_button.setObjectName("PrimaryButton")
        self.record_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_button.setFixedHeight(48)
        self.record_button.setIcon(icons.icon("record", "#ffffff", 15))
        self.record_button.clicked.connect(self._toggle_record)
        card.add(self.record_button)

        self.record_status = label(tr("macros.recording_hint"), "Hint", wrap=True)
        card.add(self.record_status)

        self.record_meta = label("", "Mono")
        card.add(self.record_meta)
        return card

    def _build_playback_card(self) -> QWidget:
        card = Card(tr("card.playback"), tr("macros.playback_hint"), icon_name="play")

        speed_percent = int(float(self.settings["macro"].get("speed", 1.0)) * 100)
        self.speed_slider = SliderRow(tr("macros.speed"), 25, 400, speed_percent, "%")
        self.speed_slider.valueChanged.connect(self._on_speed)
        card.add(self.speed_slider)

        self.loops_input = NumberInput(
            int(self.settings["macro"].get("loops", 1)), 0, 100000, 1, width=136
        )
        self.loops_input.valueChanged.connect(lambda value: self.save("macro", "loops", value))
        card.add(self._row(tr("macros.loops"), self.loops_input, tr("macros.loops_infinite")))

        card.add(divider())

        status_row = QWidget()
        row = QHBoxLayout(status_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.playback_status = label(tr("macros.idle"), "Hint")
        row.addWidget(self.playback_status, 1)
        self.stop_button = QPushButton(tr("btn.stop"))
        self.stop_button.setObjectName("GhostButton")
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.ctx.player.stop)
        row.addWidget(self.stop_button)
        card.add(status_row)
        return card

    @staticmethod
    def _row(text: str, widget: QWidget, hint_text: str = "") -> QWidget:
        from ..widgets import form_row

        return form_row(text, widget, hint_text)

    def _build_library_card(self) -> QWidget:
        card = Card(tr("card.library"), icon_name="grid")

        top = QWidget()
        row = QHBoxLayout(top)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.library_count = label("", "Hint")
        row.addWidget(self.library_count, 1)
        import_button = QPushButton(tr("btn.import"))
        import_button.setObjectName("GhostButton")
        import_button.setCursor(Qt.CursorShape.PointingHandCursor)
        import_button.setIcon(icons.icon("folder", DIM, 15))
        import_button.clicked.connect(self._import_macro)
        row.addWidget(import_button)
        card.add(top)

        self.empty_label = label(tr("macros.empty"), "Hint", wrap=True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setMinimumHeight(60)
        card.add(self.empty_label)

        self.list = QListWidget()
        self.list.setSpacing(4)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setVisible(False)
        card.add(self.list)
        return card

    # ---------------------------------------------------------------- library
    def refresh(self) -> None:
        self.list.clear()
        names = self.ctx.macros.names()
        self.empty_label.setVisible(not names)
        self.list.setVisible(bool(names))
        self.library_count.setText(f"{len(names)}" if names else "")
        for name in names:
            macro = self.ctx.macros.load(name)
            if macro is None:
                continue
            meta = (
                f"{len(macro.events)} {tr('macros.actions')}  ·  "
                f"{format_time(macro.duration)}"
            )
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 58))
            self.list.addItem(item)
            row = MacroRow(name, meta)
            row.play_requested.connect(self._play)
            row.export_requested.connect(self._export_macro)
            row.delete_requested.connect(self._delete_macro)
            self.list.setItemWidget(item, row)
        height = min(max(len(names), 1) * 62 + 4, 330)
        self.list.setFixedHeight(height if names else 0)

    # --------------------------------------------------------------- recording
    def _toggle_record(self) -> None:
        if self.ctx.recorder.active:
            self.ctx.recorder.stop()
            return
        self.ctx.engine.stop(wait=True)
        self.ctx.player.stop()
        self.ctx.recorder.start()
        self._set_recording(True)

    def _set_recording(self, active: bool) -> None:
        self.record_button.setText(tr("macros.stop") if active else tr("macros.record"))
        self.record_button.setProperty("running", "true" if active else "false")
        self.record_button.setIcon(
            icons.icon("stop" if active else "record", RED if active else "#ffffff", 15)
        )
        repolish(self.record_button)
        self.record_status.setText(
            tr("macros.recording", n=0) if active else tr("macros.recording_hint")
        )
        if not active:
            self.record_meta.setText("")

    def _on_record_tick(self, actions: int, seconds: float) -> None:
        if not self.ctx.recorder.active:
            return
        self.record_status.setText(tr("macros.recording", n=actions))
        self.record_meta.setText(f"{format_time(seconds)}")

    def _on_recorded(self, macro: Macro) -> None:
        self._set_recording(False)
        if not macro.events:
            self.ctx.toast(tr("macros.empty"), "info")
            return
        name, ok = QInputDialog.getText(
            self, tr("macros.record"), tr("macros.name_prompt"), text=macro.name
        )
        if not ok:
            return
        name = (name or "").strip() or macro.name
        macro.name = self._unique_name(name)
        self.ctx.macros.save(macro)
        self.refresh()
        self.ctx.toast(tr("macros.saved", name=macro.name))

    def _unique_name(self, name: str) -> str:
        existing = set(self.ctx.macros.names())
        if name not in existing:
            return name
        index = 2
        while f"{name} ({index})" in existing:
            index += 1
        return f"{name} ({index})"

    # --------------------------------------------------------------- playback
    def _on_speed(self, percent: int) -> None:
        self.save("macro", "speed", round(percent / 100.0, 2))

    def _play(self, name: str) -> None:
        macro = self.ctx.macros.load(name)
        if macro is None:
            return
        if self.ctx.player.playing:
            self.ctx.player.stop()
        if self.ctx.engine.is_running():
            self.ctx.engine.stop(wait=True)
        speed = float(self.settings["macro"].get("speed", 1.0))
        loops = int(self.settings["macro"].get("loops", 1))
        if self.ctx.player.play(macro, speed, loops):
            self.playback_status.setText(f"{tr('status.playing')} · {name}")
            self.stop_button.setEnabled(True)

    def _on_player_finished(self) -> None:
        self.playback_status.setText(tr("macros.idle"))
        self.stop_button.setEnabled(False)

    def _export_macro(self, name: str) -> None:
        macro = self.ctx.macros.load(name)
        if macro is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("macros.export_title"), f"{name}.json", "JSON (*.json)"
        )
        if path:
            MacroStore.export(macro, path)
            self.ctx.toast(tr("macros.saved", name=Path(path).stem))

    def _import_macro(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("macros.import_title"), "", "JSON (*.json)"
        )
        if not path:
            return
        macro = MacroStore.load_path(Path(path))
        if macro is None:
            self.ctx.toast(tr("macros.import_error"), "error")
            return
        macro.name = self._unique_name(macro.name or Path(path).stem)
        self.ctx.macros.save(macro)
        self.refresh()
        self.ctx.toast(tr("macros.saved", name=macro.name))

    def _delete_macro(self, name: str) -> None:
        answer = QMessageBox.question(
            self,
            tr("btn.delete"),
            tr("macros.delete_confirm", name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.ctx.macros.delete(name)
            self.refresh()

    def cleanup(self) -> None:
        self.ctx.hotkeys.cancel_capture()
