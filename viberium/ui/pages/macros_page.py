"""Macros page: record, store and replay input sequences."""

from __future__ import annotations

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
from ..theme import ACCENT, DIM, GREEN, RED
from ..widgets import (
    Card,
    HotkeyButton,
    NumberInput,
    SliderRow,
    ToggleSwitch,
    divider,
    form_row,
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
    hotkey_changed = Signal(str, list)

    def __init__(
        self,
        name: str,
        meta: str,
        manager=None,
        binding: list[int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.name = name
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

        # Per-macro start/stop shortcut: assigned here, in the library
        self.hotkey_button = HotkeyButton(manager, binding)
        self.hotkey_button.setMinimumWidth(150)
        self.hotkey_button.setToolTip(tr("macros.hotkey.tooltip"))
        self.hotkey_button.changed.connect(lambda keys: self.hotkey_changed.emit(name, list(keys)))
        layout.addWidget(self.hotkey_button)

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
        self.ctx.recorder.state_changed.connect(self._set_recording)
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

        card.add(divider())
        self.record_moves_toggle = ToggleSwitch(
            bool(self.settings["macro"].get("record_moves", False))
        )
        self.record_moves_toggle.toggled.connect(
            lambda value: self.save("macro", "record_moves", bool(value))
        )
        card.add(
            form_row(
                tr("macros.record_moves"),
                self.record_moves_toggle,
                tr("macros.record_moves.hint"),
            )
        )
        self.hide_on_record_toggle = ToggleSwitch(
            bool(self.settings["macro"].get("hide_on_record", True))
        )
        self.hide_on_record_toggle.toggled.connect(
            lambda value: self.save("macro", "hide_on_record", bool(value))
        )
        card.add(
            form_row(
                tr("macros.hide_on_record"),
                self.hide_on_record_toggle,
                tr("macros.hide_on_record.hint"),
            )
        )
        card.add(hint(self._hotkey_text()))
        return card

    def _hotkey_text(self) -> str:
        from ...core.winapi import combo_label

        section = self.settings["hotkeys"].get("global") or {}
        combo = combo_label(section.get("record"))
        if not combo:
            return tr("macros.hotkey_hint.none")
        return tr("macros.hotkey_hint", hotkey=combo)

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
        card.add(hint(tr("macros.per_macro_hint")))

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
        per_macro = (self.settings.data["hotkeys"].get("macros") or {}).get("per_macro") or {}
        for name in names:
            macro = self.ctx.macros.load(name)
            if macro is None:
                continue
            meta = (
                f"{len(macro.events)} {tr('macros.actions')}  ·  "
                f"{format_time(macro.duration)}"
            )
            binding = list(((per_macro.get(name) or {}).get("play")) or [])
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 58))
            self.list.addItem(item)
            row = MacroRow(name, meta, self.ctx.hotkeys, binding)
            row.play_requested.connect(self._play)
            row.export_requested.connect(self._export_macro)
            row.delete_requested.connect(self._delete_macro)
            row.hotkey_changed.connect(self._on_macro_hotkey)
            self.list.setItemWidget(item, row)
        height = min(max(len(names), 1) * 62 + 4, 330)
        self.list.setFixedHeight(height if names else 0)

    def _on_macro_hotkey(self, macro_name: str, binding: list[int]) -> None:
        """Store the start/stop shortcut of one macro."""
        binding = [int(vk) for vk in (binding or [])]
        if binding:
            for context, name, other in self.ctx.hotkeys.all_bindings():
                if context == "macro" and name.startswith(f"{macro_name}#"):
                    continue  # the same macro's own other action may share it
                if list(other or []) == binding:
                    self.ctx.toast(tr("hotkey.conflict"), "error")
                    self.refresh()
                    return
        macros_section = self.settings.data["hotkeys"].setdefault("macros", {})
        per_macro = macros_section.setdefault("per_macro", {})
        actions = per_macro.setdefault(macro_name, {})
        if binding:
            actions["play"] = binding
        else:
            actions.pop("play", None)
        if not actions:
            per_macro.pop(macro_name, None)
        self.settings.save()
        self.ctx.hotkeys.reload()
        self.ctx.refresh_hints()

    # --------------------------------------------------------------- recording
    def _toggle_record(self) -> None:
        main = self.window()
        handler = getattr(main, "_start_macro_record", None)
        if handler is not None:
            if self.ctx.recorder.active:
                getattr(main, "_stop_macro_record", lambda *_: None)()
            else:
                handler(from_window=True)
            return
        # Fallback when the page is embedded without the main window
        if self.ctx.recorder.active:
            self.ctx.recorder.stop()
            return
        self.ctx.engine.stop(wait=True)
        self.ctx.player.stop()
        self.ctx.recorder.start(bool(self.settings["macro"].get("record_moves", False)))
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
        # Поднимаем окно к пользователю, чтобы сразу спросить название
        main = self.window()
        if not main.isVisible() or main.isMinimized():
            main.showNormal()
            main.raise_()
            main.activateWindow()
        self.ctx.refresh_hints()
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
    def play_selected_or_last(self) -> None:
        """Used by the play hotkey: plays the selected macro or the newest one."""
        item = self.list.currentItem()
        if item is not None:
            row = self.list.itemWidget(item)
            if row is not None:
                self._play(row.name)
                return
        names = self.ctx.macros.names()
        if names:
            self._play(names[-1])

    def play_macro(self, name: str) -> None:
        """Play one concrete macro (used by its own hotkey)."""
        self._play(name)

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
            main = self.window()
            notify = getattr(main, "notify", None)
            if notify is not None:
                notify(tr("notify.play_start"), name, "play", ACCENT, 1600)

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
            # Forget the deleted macro's own shortcut
            per_macro = (self.settings.data["hotkeys"].get("macros") or {}).get("per_macro") or {}
            if per_macro.pop(name, None):
                self.settings.save()
                self.ctx.hotkeys.reload()
            self.refresh()

    def cleanup(self) -> None:
        self.ctx.hotkeys.cancel_capture()
