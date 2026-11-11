"""Theming: dark and light palettes, fonts and the global stylesheet."""

from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget

# ------------------------------------------------------------------ tokens
TOKENS = (
    "BG", "SIDEBAR_BG", "CARD", "CARD_HOVER", "FIELD", "FIELD_HOVER",
    "BORDER", "BORDER_SOFT", "BORDER_HOVER", "TEXT", "DIM", "MUTED",
    "ACCENT", "ACCENT_HOVER", "ACCENT_PRESSED", "ACCENT_SOFT", "ACCENT_SOFT_HOVER",
    "GREEN", "GREEN_SOFT", "RED", "RED_SOFT", "AMBER",
    "SCROLL", "SCROLL_HOVER",
    "HERO_0", "HERO_1", "HERO_2", "HERO_BORDER",
    "STAT_TILE", "BTN_PRESSED", "BTN_DISABLED",
    "SEG_BG", "SEG_CHECKED",
    "SLIDER_GROOVE", "SLIDER_HANDLE", "SLIDER_HANDLE_HOVER",
    "CHECK_BORDER", "CHECK_BG",
    "TOAST_BG", "TOAST_BORDER", "CHIP_TEXT",
    "HOVER_OVERLAY", "WINBTN_HOVER", "PILL_BG", "CHIP_BG",
    "KEYTILE_BG", "SIDEBAR_CARD_BG", "KEYCAP_BG", "KEYCAP_TEXT",
)

DARK: dict[str, str] = {
    "BG": "#14161a",
    "SIDEBAR_BG": "#101216",
    "CARD": "#1a1d23",
    "CARD_HOVER": "#1f232b",
    "FIELD": "#22262e",
    "FIELD_HOVER": "#272c35",
    "BORDER": "#2a2f39",
    "BORDER_SOFT": "#23272f",
    "BORDER_HOVER": "#343b47",
    "TEXT": "#e9ebf1",
    "DIM": "#98a0af",
    "MUTED": "#6d7584",
    "ACCENT": "#5b8cff",
    "ACCENT_HOVER": "#7ba3ff",
    "ACCENT_PRESSED": "#4a79ea",
    "ACCENT_SOFT": "rgba(91, 140, 255, 0.14)",
    "ACCENT_SOFT_HOVER": "rgba(91, 140, 255, 0.22)",
    "GREEN": "#3ddc97",
    "GREEN_SOFT": "rgba(61, 220, 151, 0.14)",
    "RED": "#ff5f6d",
    "RED_SOFT": "rgba(255, 95, 109, 0.14)",
    "AMBER": "#ffb454",
    "SCROLL": "#343a45",
    "SCROLL_HOVER": "#414855",
    "HERO_0": "#1c2130",
    "HERO_1": "#1a1e27",
    "HERO_2": "#191c22",
    "HERO_BORDER": "#2b3242",
    "STAT_TILE": "rgba(255, 255, 255, 0.03)",
    "BTN_PRESSED": "#1d2129",
    "BTN_DISABLED": "#1b1e24",
    "SEG_BG": "#191c22",
    "SEG_CHECKED": "#2b3345",
    "SLIDER_GROOVE": "#2b303a",
    "SLIDER_HANDLE": "#f0f3fa",
    "SLIDER_HANDLE_HOVER": "#ffffff",
    "CHECK_BORDER": "#3a414e",
    "CHECK_BG": "#1d2128",
    "TOAST_BG": "#242b39",
    "TOAST_BORDER": "#3a4560",
    "CHIP_TEXT": "#8fb0ff",
    "HOVER_OVERLAY": "rgba(255, 255, 255, 0.04)",
    "WINBTN_HOVER": "rgba(255, 255, 255, 0.07)",
    "PILL_BG": "rgba(255, 255, 255, 0.05)",
    "CHIP_BG": "rgba(255, 255, 255, 0.04)",
    "KEYTILE_BG": "rgba(255, 255, 255, 0.035)",
    "SIDEBAR_CARD_BG": "rgba(255, 255, 255, 0.035)",
    "KEYCAP_BG": "rgba(255, 255, 255, 0.07)",
    "KEYCAP_TEXT": "#cfd6e4",
}

LIGHT: dict[str, str] = {
    "BG": "#f3f5f8",
    "SIDEBAR_BG": "#e9edf3",
    "CARD": "#ffffff",
    "CARD_HOVER": "#f6f8fb",
    "FIELD": "#eef1f5",
    "FIELD_HOVER": "#e5eaf1",
    "BORDER": "#d8dde5",
    "BORDER_SOFT": "#e2e6ed",
    "BORDER_HOVER": "#c5cdd9",
    "TEXT": "#1b1f27",
    "DIM": "#4d5665",
    "MUTED": "#7d8798",
    "ACCENT": "#3d74f5",
    "ACCENT_HOVER": "#5b8cff",
    "ACCENT_PRESSED": "#2f63d8",
    "ACCENT_SOFT": "rgba(61, 116, 245, 0.12)",
    "ACCENT_SOFT_HOVER": "rgba(61, 116, 245, 0.20)",
    "GREEN": "#18a05f",
    "GREEN_SOFT": "rgba(24, 160, 95, 0.12)",
    "RED": "#e0424d",
    "RED_SOFT": "rgba(224, 66, 77, 0.12)",
    "AMBER": "#d08420",
    "SCROLL": "#c3cad6",
    "SCROLL_HOVER": "#aab3c2",
    "HERO_0": "#ffffff",
    "HERO_1": "#f8f9fc",
    "HERO_2": "#f3f5f9",
    "HERO_BORDER": "#e0e5ee",
    "STAT_TILE": "rgba(0, 0, 0, 0.03)",
    "BTN_PRESSED": "#e3e7ee",
    "BTN_DISABLED": "#eef0f4",
    "SEG_BG": "#e8ebf1",
    "SEG_CHECKED": "#d8dfeb",
    "SLIDER_GROOVE": "#d5dae3",
    "SLIDER_HANDLE": "#4b5462",
    "SLIDER_HANDLE_HOVER": "#39414e",
    "CHECK_BORDER": "#b6bec9",
    "CHECK_BG": "#f2f4f8",
    "TOAST_BG": "#ffffff",
    "TOAST_BORDER": "#d8dde5",
    "CHIP_TEXT": "#2f63d8",
    "HOVER_OVERLAY": "rgba(0, 0, 0, 0.04)",
    "WINBTN_HOVER": "rgba(0, 0, 0, 0.06)",
    "PILL_BG": "rgba(0, 0, 0, 0.04)",
    "CHIP_BG": "rgba(0, 0, 0, 0.04)",
    "KEYTILE_BG": "rgba(0, 0, 0, 0.03)",
    "SIDEBAR_CARD_BG": "rgba(255, 255, 255, 0.65)",
    "KEYCAP_BG": "rgba(0, 0, 0, 0.06)",
    "KEYCAP_TEXT": "#3a4150",
}

THEMES: dict[str, dict[str, str]] = {"dark": DARK, "light": LIGHT}

# Names below are kept as module-level constants and refreshed on theme change
# so that `from .theme import ACCENT` style imports keep working.
for _name in TOKENS:
    globals()[_name] = DARK[_name]

current_theme: str = "dark"


def _sync_modules() -> None:
    """Refresh token constants in every viberium module that imported them."""
    snapshot = {name: globals()[name] for name in TOKENS}
    for module in list(sys.modules.values()):
        if module is None or not getattr(module, "__name__", "").startswith("viberium"):
            continue
        for name, value in snapshot.items():
            if name in module.__dict__:
                setattr(module, name, value)


def pick_font(candidates: list[str]) -> str:
    available = set(QFontDatabase.families())
    for name in candidates:
        if name in available:
            return name
    return QApplication.font().family()


def apply_theme(app: QApplication, name: str = "dark") -> None:
    global current_theme
    theme = THEMES.get(name, DARK)
    current_theme = "light" if theme is LIGHT else "dark"
    for token in TOKENS:
        globals()[token] = theme[token]

    family = pick_font(["Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans"])
    font = QFont(family, 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(theme["BG"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme["TEXT"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme["FIELD"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme["CARD"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(theme["TEXT"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(theme["FIELD"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme["TEXT"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme["ACCENT"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme["CARD"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme["TEXT"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(theme["MUTED"]))
    app.setPalette(palette)
    app.setStyleSheet(build_stylesheet(theme))
    _sync_modules()


def add_shadow(widget: QWidget, blur: int = 34, alpha: int = 90, dy: int = 6) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setColor(QColor(0, 0, 0, alpha))
    effect.setOffset(0, dy)
    widget.setGraphicsEffect(effect)


def remove_shadow(widget: QWidget) -> None:
    widget.setGraphicsEffect(None)


def build_stylesheet(t: dict[str, str]) -> str:
    return f"""
* {{
    outline: none;
}}

QWidget {{
    color: {t['TEXT']};
    background: transparent;
    font-size: 10pt;
}}

QToolTip {{
    background: {t['CARD']};
    color: {t['TEXT']};
    border: 1px solid {t['BORDER']};
    border-radius: 6px;
    padding: 6px 9px;
}}

/* ------------------------------------------------------------- containers */
QFrame#Root {{
    background: {t['BG']};
    border: 1px solid {t['BORDER']};
    border-radius: 14px;
}}
QFrame#Root[maximized="true"] {{
    border-radius: 0px;
    border: none;
}}

QWidget#Sidebar {{
    background: {t['SIDEBAR_BG']};
    border-top-left-radius: 14px;
    border-bottom-left-radius: 14px;
    border-right: 1px solid {t['BORDER_SOFT']};
}}

QWidget#TitleBar {{
    background: transparent;
}}

QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
    background: {t['SCROLL']};
    border-radius: 3px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t['SCROLL_HOVER']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0;
    background: transparent;
}}
QScrollBar:horizontal {{ height: 0; }}

/* ------------------------------------------------------------------ cards */
QFrame#Card {{
    background: {t['CARD']};
    border: 1px solid {t['BORDER_SOFT']};
    border-radius: 12px;
}}
QFrame#HeroCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {t['HERO_0']}, stop:0.55 {t['HERO_1']}, stop:1 {t['HERO_2']});
    border: 1px solid {t['HERO_BORDER']};
    border-radius: 14px;
}}
QFrame#StatTile {{
    background: {t['STAT_TILE']};
    border: 1px solid {t['BORDER_SOFT']};
    border-radius: 10px;
}}
QFrame#Divider {{
    background: {t['BORDER_SOFT']};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

/* ----------------------------------------------------------------- labels */
QLabel#CardTitle {{
    font-size: 10.5pt;
    font-weight: 600;
    color: {t['TEXT']};
}}
QLabel#CardSubtitle, QLabel#Hint {{
    font-size: 8.5pt;
    color: {t['MUTED']};
}}
QLabel#LinkLabel {{
    font-size: 8.5pt;
}}
QLabel#FieldLabel {{
    font-size: 9.5pt;
    color: {t['DIM']};
}}
QLabel#PageTitle {{
    font-size: 17pt;
    font-weight: 600;
    color: {t['TEXT']};
}}
QLabel#PageSubtitle {{
    font-size: 9.5pt;
    color: {t['MUTED']};
}}
QLabel#StatValue {{
    font-size: 17pt;
    font-weight: 600;
    color: {t['TEXT']};
}}
QLabel#StatLabel {{
    font-size: 8pt;
    color: {t['MUTED']};
    text-transform: uppercase;
}}
QLabel#HeroTitle {{
    font-size: 15pt;
    font-weight: 600;
}}
QLabel#HeroSubtitle {{
    font-size: 9pt;
    color: {t['DIM']};
}}
QLabel#Brand {{
    font-size: 12pt;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QLabel#BrandSub {{
    font-size: 7.5pt;
    color: {t['MUTED']};
    letter-spacing: 1.6px;
}}
QLabel#Version {{
    font-size: 8pt;
    color: {t['MUTED']};
}}
QLabel#Mono {{
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 9pt;
    color: {t['DIM']};
}}

/* ---------------------------------------------------------------- buttons */
QPushButton {{
    background: {t['FIELD']};
    border: 1px solid {t['BORDER']};
    border-radius: 8px;
    padding: 7px 14px;
    color: {t['TEXT']};
    font-size: 9.5pt;
}}
QPushButton:hover {{
    background: {t['FIELD_HOVER']};
    border-color: {t['BORDER_HOVER']};
}}
QPushButton:pressed {{
    background: {t['BTN_PRESSED']};
}}
QPushButton:disabled {{
    color: {t['MUTED']};
    background: {t['BTN_DISABLED']};
    border-color: {t['BORDER_SOFT']};
}}

QPushButton#PrimaryButton {{
    background: {t['ACCENT']};
    border: 1px solid {t['ACCENT']};
    color: #ffffff;
    font-size: 10.5pt;
    font-weight: 600;
    border-radius: 10px;
    padding: 12px 22px;
}}
QPushButton#PrimaryButton:hover {{
    background: {t['ACCENT_HOVER']};
    border-color: {t['ACCENT_HOVER']};
}}
QPushButton#PrimaryButton:pressed {{
    background: {t['ACCENT_PRESSED']};
}}
QPushButton#PrimaryButton[running="true"] {{
    background: {t['RED_SOFT']};
    border: 1px solid {t['RED']};
    color: {t['RED']};
}}
QPushButton#PrimaryButton[running="true"]:hover {{
    background: {t['RED_SOFT']};
}}

QPushButton#GhostButton {{
    background: transparent;
    border: 1px solid {t['BORDER']};
    color: {t['DIM']};
}}
QPushButton#GhostButton:hover {{
    background: {t['CARD_HOVER']};
    color: {t['TEXT']};
}}
QPushButton#DangerButton {{
    background: transparent;
    border: 1px solid {t['RED']};
    color: {t['RED']};
}}
QPushButton#DangerButton:hover {{
    background: {t['RED_SOFT']};
}}

QPushButton#NavButton {{
    background: transparent;
    border: none;
    border-radius: 9px;
    padding: 9px 12px;
    text-align: left;
    color: {t['DIM']};
    font-size: 10pt;
}}
QPushButton#NavButton:hover {{
    background: {t['HOVER_OVERLAY']};
    color: {t['TEXT']};
}}
QPushButton#NavButton:checked {{
    background: {t['ACCENT_SOFT']};
    color: {t['TEXT']};
    font-weight: 600;
}}

QPushButton#WinButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 0;
}}
QPushButton#WinButton:hover {{
    background: {t['WINBTN_HOVER']};
}}
QPushButton#WinClose:hover {{
    background: #e81123;
}}

QPushButton#Chip {{
    background: {t['CHIP_BG']};
    border: 1px solid {t['BORDER_SOFT']};
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 8.5pt;
    color: {t['DIM']};
}}
QPushButton#Chip:hover {{
    background: {t['ACCENT_SOFT']};
    border-color: {t['ACCENT']};
    color: {t['TEXT']};
}}

/* ------------------------------------------------------------- segmented */
QWidget#Segmented {{
    background: {t['SEG_BG']};
    border: 1px solid {t['BORDER_SOFT']};
    border-radius: 9px;
}}
QWidget#Segmented QPushButton {{
    background: transparent;
    border: none;
    border-radius: 7px;
    padding: 6px 12px;
    color: {t['DIM']};
    font-size: 9pt;
}}
QWidget#Segmented QPushButton:hover {{
    color: {t['TEXT']};
    background: {t['HOVER_OVERLAY']};
}}
QWidget#Segmented QPushButton:checked {{
    background: {t['SEG_CHECKED']};
    color: {t['TEXT']};
    font-weight: 600;
}}

/* ----------------------------------------------------------------- fields */
QFrame#Field {{
    background: {t['FIELD']};
    border: 1px solid {t['BORDER']};
    border-radius: 8px;
}}
QFrame#Field:hover {{
    border-color: {t['BORDER_HOVER']};
}}
QFrame#Field[focused="true"] {{
    border-color: {t['ACCENT']};
}}
QLineEdit {{
    background: transparent;
    border: none;
    color: {t['TEXT']};
    padding: 7px 10px;
    selection-background-color: {t['ACCENT']};
    selection-color: #ffffff;
}}
QLineEdit#Bare {{
    background: {t['FIELD']};
    border: 1px solid {t['BORDER']};
    border-radius: 8px;
}}
QLineEdit#Bare:focus {{
    border-color: {t['ACCENT']};
}}
QLineEdit#NumberField {{
    padding: 7px 4px 7px 10px;
    font-size: 10pt;
    font-weight: 600;
}}
QLineEdit#NumberField:disabled {{
    color: {t['MUTED']};
}}

QComboBox {{
    background: {t['FIELD']};
    border: 1px solid {t['BORDER']};
    border-radius: 8px;
    padding: 7px 12px;
    color: {t['TEXT']};
    min-height: 18px;
}}
QComboBox:hover {{
    border-color: {t['BORDER_HOVER']};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background: {t['CARD']};
    border: 1px solid {t['BORDER']};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {t['ACCENT_SOFT']};
    color: {t['TEXT']};
    outline: none;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {t['SLIDER_GROOVE']};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {t['ACCENT']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {t['SLIDER_HANDLE']};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {t['SLIDER_HANDLE_HOVER']};
}}

QCheckBox {{
    spacing: 10px;
    color: {t['DIM']};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {t['CHECK_BORDER']};
    background: {t['CHECK_BG']};
}}
QCheckBox::indicator:hover {{
    border-color: {t['ACCENT']};
}}
QCheckBox::indicator:checked {{
    background: {t['ACCENT']};
    border-color: {t['ACCENT']};
}}

/* ------------------------------------------------------------------- list */
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    background: transparent;
    border: none;
    padding: 0;
    margin: 0;
}}
QListWidget::item:selected {{
    background: transparent;
}}

/* ------------------------------------------------------------------ pills */
QFrame#StatusPill {{
    background: {t['PILL_BG']};
    border: 1px solid {t['BORDER']};
    border-radius: 13px;
}}
QFrame#StatusPill[running="true"] {{
    background: {t['GREEN_SOFT']};
    border: 1px solid {t['GREEN']};
}}
QLabel#StatusText {{
    font-size: 8.5pt;
    color: {t['DIM']};
}}
QFrame#StatusPill[running="true"] QLabel#StatusText {{
    color: {t['GREEN']};
}}

/* ------------------------------------------------------------------ menus */
QMenu {{
    background: {t['CARD']};
    border: 1px solid {t['BORDER']};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 22px 7px 14px;
    border-radius: 6px;
    color: {t['TEXT']};
}}
QMenu::item:selected {{
    background: {t['ACCENT_SOFT']};
}}
QMenu::separator {{
    height: 1px;
    background: {t['BORDER_SOFT']};
    margin: 5px 8px;
}}

QMessageBox {{
    background: {t['BG']};
}}
QMessageBox QLabel {{
    color: {t['TEXT']};
}}

QDialog {{
    background: {t['BG']};
}}

/* ------------------------------------------------------------ extra parts */
QPushButton#HotkeyButton {{
    background: {t['FIELD']};
    border: 1px solid {t['BORDER']};
    border-radius: 8px;
    padding: 7px 12px;
    color: {t['TEXT']};
    font-weight: 600;
    font-size: 9.5pt;
}}
QPushButton#HotkeyButton:hover {{
    background: {t['FIELD_HOVER']};
    border-color: {t['BORDER_HOVER']};
}}
QPushButton#HotkeyButton[capturing="true"] {{
    background: {t['ACCENT_SOFT']};
    border-color: {t['ACCENT']};
    color: {t['ACCENT_HOVER']};
}}

QLabel#ValueChip {{
    background: {t['ACCENT_SOFT']};
    color: {t['CHIP_TEXT']};
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 8.5pt;
    font-weight: 600;
}}

QFrame#Toast {{
    background: {t['TOAST_BG']};
    border: 1px solid {t['TOAST_BORDER']};
    border-radius: 10px;
}}
QFrame#Toast QLabel {{
    color: {t['TEXT']};
    font-size: 9.5pt;
}}

QPushButton#KeyTile {{
    background: {t['KEYTILE_BG']};
    border: 1px solid {t['BORDER_SOFT']};
    border-radius: 10px;
    padding: 10px 18px;
    font-size: 11pt;
    font-weight: 600;
    color: {t['TEXT']};
}}
QPushButton#KeyTile:hover {{
    background: {t['ACCENT_SOFT']};
    border-color: {t['ACCENT']};
}}
QPushButton#KeyTile[capturing="true"] {{
    background: {t['ACCENT_SOFT']};
    border-color: {t['ACCENT']};
    color: {t['ACCENT_HOVER']};
}}

QFrame#SidebarCard {{
    background: {t['SIDEBAR_CARD_BG']};
    border: 1px solid {t['BORDER_SOFT']};
    border-radius: 10px;
}}
QLabel#KeyCap {{
    background: {t['KEYCAP_BG']};
    border-radius: 5px;
    padding: 2px 7px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 8pt;
    color: {t['KEYCAP_TEXT']};
}}

QPushButton#HotkeyReset {{
    background: transparent;
    border: none;
    border-radius: 11px;
    color: {t['DIM']};
    font-size: 15pt;
    font-weight: 600;
    line-height: 1;
    padding: 0;
}}
QPushButton#HotkeyReset:hover {{
    background: {t['HOVER_OVERLAY']};
    color: {t['RED']};
}}
QPushButton#HotkeyReset:pressed {{
    background: {t['BTN_PRESSED']};
}}

QLabel#ProcessBubble {{
    background: {t['FIELD']};
    border: 1px solid {t['BORDER']};
    border-radius: 10px;
    padding: 2px 10px;
    color: {t['TEXT']};
    font-size: 8.5pt;
}}
QLabel#ProcessBubble[active="true"] {{
    background: {t['GREEN_SOFT']};
    border-color: {t['GREEN']};
    color: {t['GREEN']};
}}
QLabel#ProcessBubble[active="false"] {{
    background: {t['FIELD']};
    border-color: {t['BORDER']};
    color: {t['TEXT']};
}}

QMenu#TargetMenu {{
    background: {t['CARD']};
    border: 1px solid {t['BORDER']};
    border-radius: 8px;
    padding: 4px;
    color: {t['TEXT']};
}}
QMenu#TargetMenu::item {{
    padding: 6px 16px;
    border-radius: 4px;
    color: {t['TEXT']};
}}
QMenu#TargetMenu::item:selected {{
    background: {t['ACCENT_SOFT']};
    color: {t['TEXT']};
}}
"""
