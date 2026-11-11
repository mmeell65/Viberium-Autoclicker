"""Main application window: frameless shell, sidebar, tray integration."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QEvent, QPoint, QSize, QTimer, Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..config import APP_VERSION, Settings
from ..core.engine import ClickEngine
from ..core.hooks import InputHub
from ..core.hotkeys import HotkeyManager
from ..core.macros import MacroPlayer, MacroRecorder, MacroStore
from ..core import winapi
from ..core.winapi import IS_WINDOWS
from ..i18n import tr
from . import icons
from .appicon import app_icon, icon_pixmap
from .pages.base import Context, hotkey_hint
from .pages.keyboard_page import KeyboardPage
from .pages.macros_page import MacrosPage
from .pages.mouse_page import MousePage
from .pages.settings_page import SettingsPage
from .theme import ACCENT, add_shadow, remove_shadow
from .widgets import NavButton, TitleBar, Toast, label, repolish

NAV_ITEMS = (
    ("cursor", "nav.mouse"),
    ("keyboard", "nav.keyboard"),
    ("macro", "nav.macros"),
    ("settings", "nav.settings"),
)



class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings()
        tr.set_language(self.settings.get_value("language", "ru"))

        self.hub = InputHub()
        self.hub.start()
        self.engine = ClickEngine(self)
        self.hotkeys = HotkeyManager(self.settings, self.hub, self)
        self.macros = MacroStore()
        self.recorder = MacroRecorder(self.hub, self)
        self.player = MacroPlayer(self)

        self.ctx = Context(
            settings=self.settings,
            engine=self.engine,
            hotkeys=self.hotkeys,
            hub=self.hub,
            macros=self.macros,
            recorder=self.recorder,
            player=self.player,
        )
        self.ctx.toast = self.toast
        self.ctx.rebuild = self.rebuild_ui
        self.ctx.refresh_hints = self.refresh_hints
        self.ctx.apply_flags = self.apply_flags

        self._pages: list[QWidget] = []
        self._page_index = 0
        self._root: QFrame | None = None
        self._toast: Toast | None = None
        self._hold_owns_engine = False
        self._force_quit = False
        self._tray_hint_shown = False
        self._tray: QSystemTrayIcon | None = None

        self.setWindowTitle("Viberium")
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(1000, 660)
        self.resize(1140, 780)

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(24, 20, 24, 28)
        self._outer.setSpacing(0)

        self._build_ui()
        self._connect_engine()
        self._create_tray()
        self.apply_flags()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        self._destroy_ui()

        self._root = QFrame()
        self._root.setObjectName("Root")
        add_shadow(self._root, 34, 80, 4)
        self._outer.addWidget(self._root)

        shell = QHBoxLayout(self._root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_sidebar())

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        self.titlebar = TitleBar()
        self.titlebar.minimize_clicked.connect(self.showMinimized)
        self.titlebar.maximize_clicked.connect(self.toggle_maximize)
        self.titlebar.close_clicked.connect(self.close)
        right.addWidget(self.titlebar)

        # Link the process bubble from titlebar
        self.process_label = self.titlebar.process_label

        # Target process controls: a row under the titlebar, aligned with the bubble
        self.target_controls = QWidget()
        target_controls_layout = QVBoxLayout(self.target_controls)
        target_controls_layout.setContentsMargins(20, 2, 20, 2)
        target_controls_layout.setSpacing(0)

        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)

        self.pick_target_button = QPushButton(tr("target.process.pick"))
        self.pick_target_button.setObjectName("GhostButton")
        self.pick_target_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pick_target_button.setIcon(icons.icon("target", ACCENT, 14))
        self.pick_target_button.setFixedSize(100, 30)
        self.pick_target_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.pick_target_button.clicked.connect(self._open_target_menu)
        buttons_layout.addWidget(self.pick_target_button)

        self.clear_target_button = QPushButton(tr("target.process.clear"))
        self.clear_target_button.setObjectName("GhostButton")
        self.clear_target_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_target_button.setFixedSize(90, 30)
        self.clear_target_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clear_target_button.clicked.connect(self._clear_target)
        buttons_layout.addWidget(self.clear_target_button)

        buttons_layout.addStretch(1)
        target_controls_layout.addWidget(buttons)
        right.addWidget(self.target_controls)

        # Target status timer
        self._target_status_timer = QTimer(self)
        self._target_status_timer.setInterval(500)
        self._target_status_timer.timeout.connect(self._update_target_status)
        self._target_status_timer.start()
        self._update_target_status()

        self.stack = QStackedWidget()
        self._pages = [
            MousePage(self.ctx),
            KeyboardPage(self.ctx),
            MacrosPage(self.ctx),
            SettingsPage(self.ctx),
        ]
        for page in self._pages:
            self.stack.addWidget(page)
        right.addWidget(self.stack, 1)

        shell.addLayout(right, 1)

        self._toast = Toast(self)
        self._switch(self._page_index)
        self._sync_engine_ui(self.engine.is_running(), self.engine.mode)

    def _destroy_ui(self) -> None:
        for page in self._pages:
            cleanup = getattr(page, "cleanup", None)
            if callable(cleanup):
                try:
                    cleanup()
                except Exception:
                    pass
        self._pages = []
        if self._toast is not None:
            self._toast.setParent(None)
            self._toast.deleteLater()
            self._toast = None
        if self._root is not None:
            self._outer.removeWidget(self._root)
            self._root.setParent(None)
            self._root.deleteLater()
            self._root = None

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(218)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(6)

        brand = QWidget()
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(11)
        logo = QLabel()
        logo.setPixmap(icon_pixmap(34))
        logo.setFixedSize(34, 34)
        brand_layout.addWidget(logo)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        texts.addWidget(label("Viberium", "Brand"))
        texts.addWidget(label("AUTO CLICKER", "BrandSub"))
        brand_layout.addLayout(texts, 1)
        layout.addWidget(brand)
        layout.addSpacing(20)

        self.nav_buttons: list[NavButton] = []
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, (icon_name, key) in enumerate(NAV_ITEMS):
            button = NavButton(icon_name, tr(key))
            button.clicked.connect(lambda _checked=False, idx=index: self._switch(idx))
            group.addButton(button)
            layout.addWidget(button)
            self.nav_buttons.append(button)

        layout.addStretch(1)
        layout.addSpacing(6)
        layout.addWidget(label(tr("settings.version", v=APP_VERSION), "Version"))
        return sidebar

    def rebuild_ui(self) -> None:
        self._build_ui()

    def refresh_hints(self) -> None:
        for page in self._pages:
            hero = getattr(page, "hero", None)
            hint_label = getattr(hero, "hint_label", None)
            if hint_label is not None:
                page_contexts = ("mouse", "keyboard", "macros", "mouse")
                ctx = page_contexts[self._page_index] if hasattr(self, "_page_index") else "mouse"
                hint_label.setText(hotkey_hint(self.settings, ctx))

    def _create_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = QSystemTrayIcon(app_icon(), self)
        menu = QMenu()
        show_action = QAction(tr("tray.show"), menu)
        show_action.triggered.connect(self.show_window)
        toggle_action = QAction(tr("tray.toggle"), menu)
        toggle_action.triggered.connect(self.toggle_target)
        exit_action = QAction(tr("tray.exit"), menu)
        exit_action.triggered.connect(self.quit_app)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(toggle_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self._tray.setContextMenu(menu)
        self._tray.setToolTip(tr("tray.idle"))
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    # -------------------------------------------------------------- navigation
    def _switch(self, index: int) -> None:
        if not self._pages:
            return
        index = max(0, min(index, len(self._pages) - 1))
        self._page_index = index
        self.stack.setCurrentIndex(index)
        for position, button in enumerate(self.nav_buttons):
            button.setChecked(position == index)
        # Switch hotkey context based on the active page
        contexts = ("mouse", "keyboard", "macros", "mouse")
        self.ctx.hotkeys.context = contexts[index]

    def rebuild_ui(self) -> None:
        self._build_ui()

    def refresh_hints(self) -> None:
        for page in self._pages:
            hero = getattr(page, "hero", None)
            hint_label = getattr(hero, "hint_label", None)
            if hint_label is not None:
                page_contexts = ("mouse", "keyboard", "macros", "mouse")
                ctx = page_contexts[self._page_index] if hasattr(self, "_page_index") else "mouse"
                hint_label.setText(hotkey_hint(self.settings, ctx))

    # ------------------------------------------------------------------ toast
    def toast(self, text: str, kind: str = "success") -> None:
        if self._toast is not None:
            self._toast.show_message(text, kind)

    # ----------------------------------------------------------------- engine
    def _connect_engine(self) -> None:
        self.engine.state_changed.connect(self._on_engine_state)
        self.engine.stats.connect(self._on_stats)
        self.engine.finished.connect(self._on_finished)
        self.hotkeys.toggle_triggered.connect(self.toggle_target)
        self.hotkeys.hold_started.connect(self._on_hold_start)
        self.hotkeys.hold_ended.connect(self._on_hold_end)
        self.hotkeys.emergency_triggered.connect(self.emergency_stop)
        self.hotkeys.macro_record_triggered.connect(self._toggle_macro_record)

    # ----------------------------------------------------------------- engine
    def _start_target(self) -> bool:
        target = self.settings["hotkeys"].get("target", "mouse")
        if self.engine.is_running():
            return False
        self.engine.stop(wait=True)
        if target == "keyboard":
            return self.engine.start_keyboard(self.settings["keyboard"])
        return self.engine.start_mouse(self.settings["mouse"])

    def toggle_target(self) -> None:
        if self.engine.is_running():
            self.engine.stop()
        else:
            self._start_target()

    def _toggle_macro_record(self) -> None:
        if self.ctx.recorder.active:
            self.ctx.recorder.stop()
        else:
            self.ctx.engine.stop(wait=True)
            self.ctx.player.stop()
            self.ctx.recorder.start()

    def _on_hold_start(self) -> None:
        if not self.engine.is_running():
            self._hold_owns_engine = self._start_target()

    def _on_hold_end(self) -> None:
        self._hold_owns_engine = False
        self.engine.stop()
        self.ctx.hotkeys.release_all()

    def emergency_stop(self) -> None:
        self._hold_owns_engine = False
        self.engine.stop()
        self.player.stop()
        self.ctx.hotkeys.release_all()
        if self.recorder.active:
            self.recorder.stop()

    def _on_engine_state(self, running: bool, mode: str) -> None:
        self._sync_engine_ui(running, mode)

    def _sync_engine_ui(self, running: bool, mode: str) -> None:
        if self._tray is not None:
            self._tray.setToolTip(tr("tray.running") if running else tr("tray.idle"))
        for page in self._pages:
            page.on_engine_state(running, mode)

    def _on_stats(self, mode: str, count: int, cps: float, elapsed: float) -> None:
        for page in self._pages:
            page.on_stats(mode, count, cps, elapsed)
        if self._tray is not None:
            self._tray.setToolTip(f"{tr('tray.running')} · {count}")

    def _on_finished(self, mode: str, reason: str) -> None:
        if reason == "limit":
            self.toast(tr("msg.limit_reached"))
        elif reason.startswith("error"):
            self.toast(f"{tr('msg.error')}: {reason[7:]}", "error")

    # ----------------------------------------------------------------- target window
    def _open_target_menu(self) -> None:
        """Показывает выпадающий список окон для выбора целевого процесса (блок из кнопки)."""
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.setObjectName("TargetMenu")
        windows = winapi.get_open_windows()
        if not windows:
            action = menu.addItem(tr("target.process.no_windows"))
            action.setEnabled(False)
        else:
            for hwnd, title in windows:
                action = menu.addAction(title)
                action.triggered.connect(lambda checked=False, t=title: self._set_target(t))
        menu.exec(self.pick_target_button.mapToGlobal(self.pick_target_button.rect().bottomLeft()))

    def _set_target(self, title: str) -> None:
        page_contexts = ("mouse", "keyboard", "macros", "mouse")
        active_ctx = page_contexts[self._page_index] if hasattr(self, "_page_index") else "mouse"
        if active_ctx in ("mouse", "keyboard"):
            section = self.settings.data.get(active_ctx, {})
            section["target_process"] = title
            self.settings.data[active_ctx] = section
            self.settings.save()
        self.ctx.toast(tr("target.process.active", title=title))
        self._update_target_status()

    def _clear_target(self) -> None:
        page_contexts = ("mouse", "keyboard", "macros", "mouse")
        active_ctx = page_contexts[self._page_index] if hasattr(self, "_page_index") else "mouse"
        if active_ctx in ("mouse", "keyboard"):
            section = self.settings.data.get(active_ctx, {})
            section["target_process"] = ""
            self.settings.data[active_ctx] = section
            self.settings.save()
        self.ctx.toast(tr("target.process.cleared"))
        self._update_target_status()

    def _update_target_status(self) -> None:
        page_contexts = ("mouse", "keyboard", "macros", "mouse")
        active_ctx = page_contexts[self._page_index] if hasattr(self, "_page_index") else "mouse"
        target = ""
        if active_ctx in ("mouse", "keyboard"):
            section = self.settings.data.get(active_ctx, {})
            target = section.get("target_process", "") or ""

        if not target:
            self.process_label.setText(tr("target.process.status.not_selected"))
            self.process_label.setProperty("active", "false")
        else:
            # Show just the process name; green when selected (regardless of active state)
            self.process_label.setText(target)
            self.process_label.setProperty("active", "true")
        repolish(self.process_label)
        self.process_label.adjustSize()

    # ----------------------------------------------------------------- window
    def apply_flags(self) -> None:
        on_top = bool(self.settings["general"].get("always_on_top", False))
        flags = self.windowFlags()
        if on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

    def toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.WindowStateChange and self._root is not None:
            maximized = self.isMaximized()
            self.titlebar.set_maximized(maximized)
            self._root.setProperty("maximized", "true" if maximized else "false")
            repolish(self._root)
            if maximized:
                remove_shadow(self._root)
                self._outer.setContentsMargins(0, 0, 0, 0)
            else:
                add_shadow(self._root, 34, 80, 4)
                self._outer.setContentsMargins(24, 20, 24, 28)
        super().changeEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._toast is not None and self._toast.isVisible():
            self._toast._reposition()

    def nativeEvent(self, event_type, message):
        try:
            if bytes(event_type) == b"windows_generic_MSG" and not self.isMaximized():
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x0084 and self._root is not None:  # WM_NCHITTEST
                    x = ctypes.c_short(msg.lParam & 0xFFFF).value
                    y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
                    local = self.mapFromGlobal(QPoint(x, y))
                    area = self._root.geometry()
                    border = 7
                    left = area.left() - 2 <= local.x() <= area.left() + border
                    right = area.right() - border <= local.x() <= area.right() + 2
                    top = area.top() - 2 <= local.y() <= area.top() + border
                    bottom = area.bottom() - border <= local.y() <= area.bottom() + 2
                    code = 0
                    if top and left:
                        code = 13  # HTTOPLEFT
                    elif top and right:
                        code = 14  # HTTOPRIGHT
                    elif bottom and left:
                        code = 16  # HTBOTTOMLEFT
                    elif bottom and right:
                        code = 17  # HTBOTTOMRIGHT
                    elif left:
                        code = 10  # HTLEFT
                    elif right:
                        code = 11  # HTRIGHT
                    elif top:
                        code = 12  # HTTOP
                    elif bottom:
                        code = 15  # HTBOTTOM
                    if code:
                        return True, code
        except Exception:
            pass
        return super().nativeEvent(event_type, message)

    # ------------------------------------------------------------------- tray
    def _on_tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window()

    def closeEvent(self, event) -> None:
        to_tray = bool(self.settings["general"].get("minimize_to_tray", True))
        if to_tray and self._tray is not None and self._tray.isVisible() and not self._force_quit:
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self._tray.showMessage(
                    "Viberium",
                    tr("tray.idle"),
                    QSystemTrayIcon.MessageIcon.Information,
                    2500,
                )
            return
        self.shutdown()
        super().closeEvent(event)

    def quit_app(self) -> None:
        self._force_quit = True
        self.shutdown()
        self.close()
        QApplication.quit()

    def shutdown(self) -> None:
        try:
            self.engine.stop(wait=True)
            self.player.stop()
            if self.recorder.active:
                self.recorder.stop()
            self.hub.stop()
        finally:
            if self._tray is not None:
                self._tray.hide()
