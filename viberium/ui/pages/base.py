"""Shared page context and base class."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from ...config import Settings
from ...core.engine import ClickEngine
from ...core.hooks import InputHub
from ...core.hotkeys import HotkeyManager
from ...core.macros import MacroPlayer, MacroRecorder, MacroStore
from ...i18n import tr
from .. import icons
from ..widgets import hint, label, page_header


@dataclass
class Context:
    settings: Settings
    engine: ClickEngine
    hotkeys: HotkeyManager
    hub: InputHub
    macros: MacroStore
    recorder: MacroRecorder
    player: MacroPlayer
    toast: Callable[..., None] = lambda *args, **kwargs: None
    rebuild: Callable[[], None] = lambda: None
    refresh_hints: Callable[[], None] = lambda: None
    apply_flags: Callable[[], None] = lambda: None


class BasePage(QWidget):
    """Page with a scrollable content column."""

    def __init__(self, ctx: Context, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.settings = ctx.settings

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(250)
        self._save_timer.timeout.connect(self.settings.save)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.viewport().setAutoFillBackground(False)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.scroll)

        self.content = QWidget()
        self.content.setAutoFillBackground(False)
        self.scroll.setWidget(self.content)
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(22, 6, 14, 24)
        self.body.setSpacing(16)

    # ----------------------------------------------------------------- helpers
    def add_header(self, title: str, subtitle: str) -> None:
        self.body.addWidget(page_header(title, subtitle))

    def hotkey_card(
        self,
        context: str,
        fields: list[tuple[str, str, str | None]],
        title: str | None = None,
        icon_name: str = "keyboard",
    ) -> QWidget:
        from ..widgets import Card, HotkeyButton, divider, form_row

        card = Card(title or tr("card.hotkeys"), icon_name=icon_name)
        hotkeys_section = self.settings["hotkeys"].get(context) or {}

        self._hotkey_buttons: dict[str, HotkeyButton] = getattr(self, "_hotkey_buttons", {})
        self._hotkey_buttons[context] = {}

        for key, title_key, hint_key in fields:
            binding = hotkeys_section.get(key) or []
            button = HotkeyButton(self.ctx.hotkeys, binding)
            button.changed.connect(
                lambda binding, ctx=context, name=key: self._on_hotkey(ctx, name, binding)
            )
            button.reset_requested.connect(
                lambda ctx=context, name=key: self._reset_hotkey(ctx, name)
            )
            self._hotkey_buttons[context][key] = button
            hint_text = tr(hint_key) if hint_key else ""
            card.add(form_row(tr(title_key), button, hint_text))

        if title is None:
            card.add(divider())

        return card

    def _on_hotkey(self, context: str, name: str, binding: list[int]) -> None:
        section = self.settings.data["hotkeys"].get(context) or {}
        # пустая привязка — просто сбрасываем, без проверки конфликтов
        if binding:
            for other, other_binding in section.items():
                if other == name:
                    continue
                if list(other_binding or []) == list(binding):
                    self.ctx.toast(tr("hotkey.conflict"), "error")
                    self._hotkey_buttons[context][name].set_binding(list(section.get(name) or []))
                    return
        section[name] = list(binding)
        self.settings.data["hotkeys"][context] = section
        self.settings.save()
        self.ctx.hotkeys.reload()
        self.ctx.refresh_hints()

    def _reset_hotkey(self, context: str, name: str) -> None:
        section = self.settings.data["hotkeys"].get(context) or {}
        section[name] = []
        self.settings.data["hotkeys"][context] = section
        self.settings.save()
        self.ctx.hotkeys.reload()
        self.ctx.refresh_hints()
        self.ctx.toast(tr("hotkey.reset"))

    def save(self, section: str, key: str, value) -> None:
        self.settings.data.setdefault(section, {})[key] = value
        self._save_timer.start()

    def info_card(self, title: str, text: str) -> QWidget:
        from ..widgets import Card

        card = Card(title, icon_name="info")
        card.add(hint(text))
        return card

    # ------------------------------------------------------------ engine hooks
    def on_engine_state(self, running: bool, mode: str) -> None:
        pass

    def on_stats(self, mode: str, count: int, cps: float, elapsed: float) -> None:
        pass


def hotkey_hint(settings, context: str = "mouse") -> str:
    from ...core.winapi import combo_label
    from ...i18n import tr

    section = settings["hotkeys"].get(context) or {}
    parts: list[str] = []

    if context == "macros":
        play = combo_label(section.get("play"))
        if play:
            parts.append(f"{play} — {tr('short.macro_play').lower()}")
        record = combo_label(section.get("record"))
        if record:
            parts.append(f"{record} — {tr('short.macro_record').lower()}")
    else:
        toggle = combo_label(section.get("toggle"))
        if toggle:
            parts.append(f"{toggle} — {tr('short.toggle').lower()}")
        hold = combo_label(section.get("hold"))
        if hold and settings["hotkeys"].get("hold_enabled", True):
            parts.append(f"{hold} — {tr('short.hold').lower()}")

    return "     ·     ".join(parts)
