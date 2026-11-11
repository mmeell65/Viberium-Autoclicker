"""Settings page: general options, profiles and about."""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QApplication,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...config import APP_VERSION, GITHUB_URL
from ...i18n import tr
from ...utils import is_autostart_enabled, set_autostart
from .. import icons
from ..appicon import icon_pixmap
from ..theme import ACCENT, DIM, TEXT, apply_theme
from ..widgets import (
    Card,
    SegmentedControl,
    ToggleSwitch,
    divider,
    form_row,
    hint,
    icon_label,
    label,
    repolish,
)
from .base import BasePage, Context


class SettingsPage(BasePage):
    def __init__(self, ctx: Context, parent: QWidget | None = None) -> None:
        super().__init__(ctx, parent)
        self.add_header(tr("settings.title"), tr("settings.subtitle"))

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.addWidget(self._build_general_card(), 0, 0)
        grid.addWidget(self._build_profiles_card(), 1, 0)
        grid.addWidget(self._build_about_card(), 0, 1)
        grid.addWidget(QWidget(), 1, 1)  # empty spacer
        self.body.addLayout(grid)
        self.body.addStretch(1)

    # ------------------------------------------------------------------ cards
    def _build_general_card(self) -> QWidget:
        card = Card(tr("card.general"), icon_name="settings")
        general = self.settings["general"]

        self.language_seg = SegmentedControl(
            [("ru", "Русский"), ("en", "English")],
            self.settings.get_value("language", "ru"),
        )
        self.language_seg.setFixedWidth(210)
        self.language_seg.changed.connect(self._on_language)
        card.add(form_row(tr("settings.language"), self.language_seg))

        card.add(divider())

        self.theme_seg = SegmentedControl(
            [
                ("dark", tr("settings.theme.dark")),
                ("light", tr("settings.theme.light")),
            ],
            self.settings.get_value("theme", "dark"),
        )
        self.theme_seg.setFixedWidth(210)
        self.theme_seg.changed.connect(self._on_theme)
        card.add(form_row(tr("settings.theme"), self.theme_seg))

        card.add(divider())

        self.tray_toggle = ToggleSwitch(bool(general.get("minimize_to_tray", True)))
        self.tray_toggle.toggled.connect(lambda value: self.save("general", "minimize_to_tray", value))
        card.add(
            form_row(
                tr("settings.minimize_to_tray"),
                self.tray_toggle,
                tr("settings.minimize_to_tray.hint"),
            )
        )

        self.top_toggle = ToggleSwitch(bool(general.get("always_on_top", False)))
        self.top_toggle.toggled.connect(self._on_always_on_top)
        card.add(form_row(tr("settings.always_on_top"), self.top_toggle))

        self.autostart_toggle = ToggleSwitch(
            bool(general.get("autostart", False)) and is_autostart_enabled()
        )
        self.autostart_toggle.toggled.connect(self._on_autostart)
        card.add(form_row(tr("settings.autostart"), self.autostart_toggle))

        self.minimized_toggle = ToggleSwitch(bool(general.get("start_minimized", False)))
        self.minimized_toggle.toggled.connect(
            lambda value: self.save("general", "start_minimized", value)
        )
        card.add(form_row(tr("settings.start_minimized"), self.minimized_toggle))
        return card

    def _build_profiles_card(self) -> QWidget:
        card = Card(tr("card.profiles"), icon_name="folder")

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        card.add(form_row(tr("settings.profile.current"), self.profile_combo))

        buttons = QWidget()
        row = QHBoxLayout(buttons)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        load_button = QPushButton(tr("settings.profile.load"))
        load_button.setObjectName("GhostButton")
        load_button.clicked.connect(self._load_profile)
        delete_button = QPushButton(tr("settings.profile.delete"))
        delete_button.setObjectName("DangerButton")
        delete_button.clicked.connect(self._delete_profile)
        row.addWidget(load_button)
        row.addWidget(delete_button)
        row.addStretch(1)
        card.add(buttons)

        card.add(divider())

        self.profile_name = QLineEdit()
        self.profile_name.setObjectName("Bare")
        self.profile_name.setPlaceholderText(tr("settings.profile.name"))
        save_button = QPushButton(tr("settings.profile.save"))
        save_button.setObjectName("GhostButton")
        save_button.clicked.connect(self._save_profile)

        save_row = QWidget()
        save_layout = QHBoxLayout(save_row)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.setSpacing(8)
        save_layout.addWidget(self.profile_name, 1)
        save_layout.addWidget(save_button)
        card.add(save_row)

        reset_button = QPushButton(tr("settings.reset"))
        reset_button.setObjectName("DangerButton")
        reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_button.clicked.connect(self._reset_settings)
        card.add(reset_button)

        self._refresh_profiles()
        return card

    def _build_about_card(self) -> QWidget:
        card = Card(tr("card.about"), icon_name="info")

        head = QWidget()
        row = QHBoxLayout(head)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)

        logo = QWidget()
        logo.setFixedSize(56, 56)
        logo_layout = QVBoxLayout(logo)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        image = icon_label("sparkle", ACCENT, 1)
        image.setPixmap(icon_pixmap(52))
        image.setFixedSize(52, 52)
        logo_layout.addWidget(image)
        row.addWidget(logo)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(label("Viberium", "PageTitle"))
        texts.addWidget(label(tr("settings.version", v=APP_VERSION), "Hint"))
        row.addLayout(texts, 1)
        card.add(head)

        card.add(hint(tr("settings.about.text")))

        links = QWidget()
        link_row = QHBoxLayout(links)
        link_row.setContentsMargins(0, 0, 0, 0)
        link_row.setSpacing(8)
        github = QPushButton(tr("settings.github"))
        github.setObjectName("GhostButton")
        github.setCursor(Qt.CursorShape.PointingHandCursor)
        github.setIcon(icons.icon("globe", DIM, 15))
        github.clicked.connect(lambda: webbrowser.open(GITHUB_URL))
        link_row.addWidget(github)
        link_row.addWidget(label(tr("settings.license"), "Hint"))
        link_row.addStretch(1)
        card.add(links)
        return card

    # ---------------------------------------------------------------- handlers
    def _on_language(self, language: str) -> None:
        self.settings.data["language"] = language
        self.settings.save()
        tr.set_language(language)
        QTimer.singleShot(0, self.ctx.rebuild)

    def _on_theme(self, theme: str) -> None:
        self.settings.data["theme"] = theme
        self.settings.save()
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, theme)
        QTimer.singleShot(0, self.ctx.rebuild)

    def _on_autostart(self, enabled: bool) -> None:
        set_autostart(enabled)
        self.save("general", "autostart", enabled)

    def _on_always_on_top(self, enabled: bool) -> None:
        self.save("general", "always_on_top", enabled)
        self.ctx.apply_flags()

    # ---------------------------------------------------------------- profiles
    def _refresh_profiles(self) -> None:
        current = self.profile_combo.currentText()
        self.profile_combo.clear()
        self.profile_combo.addItem(tr("settings.profile.default"), "")
        for name in self.settings.profile_names():
            self.profile_combo.addItem(name, name)
        index = self.profile_combo.findText(current)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)

    def _save_profile(self) -> None:
        name = self.profile_name.text().strip()
        if not name:
            self.profile_name.setFocus()
            return
        self.settings.save_profile(name)
        self.profile_name.clear()
        self._refresh_profiles()
        self.ctx.toast(tr("settings.profile.saved", name=name))

    def _load_profile(self) -> None:
        name = self.profile_combo.currentData()
        if not name:
            return
        if self.settings.load_profile(name):
            tr.set_language(self.settings.get_value("language", "ru"))
            self.ctx.toast(tr("settings.profile.loaded", name=name))
            QTimer.singleShot(0, self.ctx.rebuild)

    def _delete_profile(self) -> None:
        name = self.profile_combo.currentData()
        if not name:
            return
        self.settings.delete_profile(name)
        self._refresh_profiles()
        self.ctx.toast(tr("settings.profile.deleted", name=name))

    def _reset_settings(self) -> None:
        answer = QMessageBox.question(
            self,
            tr("settings.reset"),
            tr("settings.reset_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.settings.reset()
        tr.set_language(self.settings.get_value("language", "ru"))
        set_autostart(False)
        self.ctx.hotkeys.reload()
        QTimer.singleShot(0, self.ctx.rebuild)
