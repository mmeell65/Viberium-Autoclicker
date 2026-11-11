"""Reusable UI building blocks (cards, toggles, fields, title bar...)."""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QFont, QIntValidator, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..core.winapi import combo_label
from ..i18n import tr
from . import icons
from .theme import (
    ACCENT,
    ACCENT_SOFT,
    BORDER,
    CARD,
    DIM,
    FIELD,
    GREEN,
    MUTED,
    RED,
    TEXT,
)


def repolish(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def label(text: str = "", kind: str | None = None, wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    if kind:
        widget.setObjectName(kind)
    widget.setWordWrap(wrap)
    return widget


def hint(text: str) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName("Hint")
    widget.setWordWrap(True)
    return widget


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("Divider")
    line.setFixedHeight(1)
    return line


def icon_label(name: str, color: str = ACCENT, size: int = 18) -> QLabel:
    widget = QLabel()
    widget.setPixmap(icons.pixmap(name, color, size))
    widget.setFixedSize(size, size)
    widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return widget


# --------------------------------------------------------------------- cards
class Card(QFrame):
    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        icon_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(13)

        if title:
            head = QHBoxLayout()
            head.setSpacing(10)
            if icon_name:
                head.addWidget(icon_label(icon_name, ACCENT, 17), 0, Qt.AlignmentFlag.AlignTop)
            texts = QVBoxLayout()
            texts.setSpacing(2)
            texts.addWidget(label(title, "CardTitle"))
            if subtitle:
                texts.addWidget(label(subtitle, "CardSubtitle", wrap=True))
            head.addLayout(texts, 1)
            outer.addLayout(head)

        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        self.body.setContentsMargins(0, 0, 0, 0)
        outer.addLayout(self.body)
        outer.addStretch(1)

    def add(self, widget: QWidget) -> QWidget:
        self.body.addWidget(widget)
        return widget


class StatTile(QFrame):
    def __init__(self, caption: str, value: str = "0", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(1)
        self.value_label = label(value, "StatValue")
        self.caption_label = label(caption, "StatLabel")
        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, text: str) -> None:
        self.value_label.setText(text)


class _Dot(QWidget):
    def __init__(self, color: str = MUTED, size: int = 8, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self._size = size
        self.setFixedSize(size, size)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(0, 0, self._size, self._size)


class StatusPill(QFrame):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusPill")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 14, 5)
        layout.setSpacing(8)
        self.dot = _Dot(MUTED, 8)
        self.text_label = label(text, "StatusText")
        layout.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.text_label)
        self._running = False

    def set_state(self, running: bool, text: str) -> None:
        self._running = running
        self.text_label.setText(text)
        self.dot.set_color(GREEN if running else MUTED)
        self.setProperty("running", "true" if running else "false")
        repolish(self)


# ------------------------------------------------------------------- toggles
class ToggleSwitch(QAbstractButton):
    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(42, 24)
        self._offset = 1.0 if checked else 0.0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(160)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _animate(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        off_color = QColor("#2c323c")
        on_color = QColor(ACCENT)
        t = self._offset
        track = QColor(
            int(off_color.red() + (on_color.red() - off_color.red()) * t),
            int(off_color.green() + (on_color.green() - off_color.green()) * t),
            int(off_color.blue() + (on_color.blue() - off_color.blue()) * t),
        )
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 12, 12)
        knob_x = 3 + t * (self.width() - 24)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#f4f6fb"))
        painter.drawEllipse(QRectF(knob_x, 3, 18, 18))


class SegmentedControl(QWidget):
    changed = Signal(str)

    def __init__(
        self,
        options: list[tuple[str, str]],
        value: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Segmented")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for key, text in options:
            button = QPushButton(text)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda _checked=False, k=key: self._on_click(k))
            self._group.addButton(button)
            layout.addWidget(button)
            self._buttons[key] = button
        self._value = value or (options[0][0] if options else "")
        if self._value in self._buttons:
            self._buttons[self._value].setChecked(True)

    def _on_click(self, key: str) -> None:
        if key == self._value:
            return
        self._value = key
        self.changed.emit(key)

    def value(self) -> str:
        return self._value

    def set_value(self, key: str, emit: bool = False) -> None:
        if key not in self._buttons:
            return
        self._value = key
        self._buttons[key].setChecked(True)
        if emit:
            self.changed.emit(key)


# -------------------------------------------------------------------- fields
class NumberInput(QWidget):
    valueChanged = Signal(int)

    def __init__(
        self,
        value: int = 0,
        minimum: int = 0,
        maximum: int = 1_000_000,
        step: int = 1,
        suffix: str = "",
        width: int = 148,
        prefix: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._min = minimum
        self._max = maximum
        self._step = step
        self._value = int(value)
        self.setFixedWidth(width)

        self.frame = QFrame()
        self.frame.setObjectName("Field")
        inner = QHBoxLayout(self.frame)
        inner.setContentsMargins(0, 0, 4, 0)
        inner.setSpacing(2)

        if prefix:
            prefix_label = QLabel(prefix)
            prefix_label.setObjectName("Hint")
            inner.addSpacing(6)
            inner.addWidget(prefix_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.edit = QLineEdit()
        self.edit.setObjectName("NumberField")
        self.edit.setValidator(QIntValidator(minimum, maximum, self))
        self.edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.edit.setText(str(value))
        self.edit.editingFinished.connect(self._commit)
        self.edit.installEventFilter(self)
        inner.addWidget(self.edit, 1)

        if suffix:
            suffix_label = QLabel(suffix)
            suffix_label.setObjectName("Hint")
            inner.addWidget(suffix_label, 0, Qt.AlignmentFlag.AlignVCenter)

        steppers = QVBoxLayout()
        steppers.setContentsMargins(0, 2, 0, 2)
        steppers.setSpacing(0)
        self._up = self._stepper("chevron-up")
        self._down = self._stepper("chevron-down")
        self._up.clicked.connect(lambda: self.step_by(1))
        self._down.clicked.connect(lambda: self.step_by(-1))
        steppers.addWidget(self._up)
        steppers.addWidget(self._down)
        inner.addLayout(steppers)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.frame)

    def _stepper(self, icon_name: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName("WinButton")
        button.setIcon(icons.icon(icon_name, MUTED, 11))
        button.setIconSize(QSize(11, 11))
        button.setFixedSize(20, 13)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def value(self) -> int:
        return self._value

    def set_value(self, value: int, emit: bool = False) -> None:
        value = max(self._min, min(self._max, int(value)))
        changed = value != self._value
        self._value = value
        self.edit.setText(str(value))
        if emit and changed:
            self.valueChanged.emit(value)

    def step_by(self, direction: int) -> None:
        self.set_value(self._value + direction * self._step, emit=True)

    def _commit(self) -> None:
        try:
            parsed = int(self.edit.text() or 0)
        except ValueError:
            parsed = self._value
        parsed = max(self._min, min(self._max, parsed))
        changed = parsed != self._value
        self._value = parsed
        self.edit.setText(str(parsed))
        if changed:
            self.valueChanged.emit(parsed)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.edit:
            if event.type() == QEvent.Type.FocusIn:
                self.frame.setProperty("focused", "true")
                repolish(self.frame)
            elif event.type() == QEvent.Type.FocusOut:
                self.frame.setProperty("focused", "false")
                repolish(self.frame)
        return super().eventFilter(watched, event)

    def wheelEvent(self, event) -> None:
        if self.edit.hasFocus():
            self.step_by(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)


class SliderRow(QWidget):
    valueChanged = Signal(int)

    def __init__(
        self,
        title: str,
        minimum: int,
        maximum: int,
        value: int,
        suffix: str = "%",
        hint_text: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._suffix = suffix
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(label(title, "FieldLabel"), 1)
        self._value_label = QLabel(f"{value}{suffix}")
        self._value_label.setObjectName("ValueChip")
        head.addWidget(self._value_label, 0, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(head)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider.valueChanged.connect(self._on_change)
        layout.addWidget(self.slider)

        if hint_text:
            layout.addWidget(hint(hint_text))

    def _on_change(self, value: int) -> None:
        self._value_label.setText(f"{value}{self._suffix}")
        self.valueChanged.emit(value)

    def value(self) -> int:
        return self.slider.value()

    def set_value(self, value: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self._value_label.setText(f"{value}{self._suffix}")
        self.slider.blockSignals(False)


class HotkeyButton(QPushButton):
    changed = Signal(list)
    reset_requested = Signal()
    capture_cancelled = Signal()
    capture_finished = Signal()

    def __init__(self, manager, binding=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._binding: list[int] = list(binding or [])
        self._waiting = False
        self.setObjectName("HotkeyButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(150)
        self.setMinimumHeight(34)
        self.clicked.connect(self._begin)
        self.manager.captured.connect(self._on_captured)
        self.capture_cancelled.connect(self._on_capture_cancelled)

        # Reset button: appears when a binding is assigned; clears it
        self._reset_button = QPushButton("×", self)
        self._reset_button.setObjectName("HotkeyReset")
        self._reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_button.setFixedSize(24, 24)
        self._reset_button.setVisible(False)
        self._reset_button.clicked.connect(self._reset)

        self._refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._reset_button is not None:
            self._reset_button.move(self.width() - 28, (self.height() - 24) // 2)

    def _on_capture_cancelled(self) -> None:
        """Another widget took over capture; reset our state."""
        if self._waiting:
            self._waiting = False
            self.setProperty("capturing", "false")
            repolish(self)
            self._refresh()

    def _reset(self) -> None:
        if self._waiting:
            self.manager.cancel_capture()
            self._waiting = False
            repolish(self)
        self._binding = []
        self._refresh()
        self.reset_requested.emit()
        self.changed.emit([])

    def _begin(self) -> None:
        if self._waiting:
            # повторный клик во время ожидания — отменяем и сбрасываем привязку
            self._reset()
            return
        self._waiting = True
        self.setProperty("capturing", "true")
        repolish(self)
        self.setText(tr("hotkey.press"))
        self.manager.begin_capture(self)

    def _on_captured(self, keys) -> None:
        if not self._waiting:
            return
        self._waiting = False
        self.setProperty("capturing", "false")
        repolish(self)
        if keys is None:
            self._refresh()
            return
        self._binding = list(keys)
        self._refresh()
        self.changed.emit(self._binding)

    def _refresh(self) -> None:
        self.setProperty("capturing", "false")
        repolish(self)
        text = combo_label(self._binding) or tr("hotkey.empty")
        self.setText(text)
        self._reset_button.setVisible(bool(self._binding) and not self._waiting)
        if self._reset_button.isVisible():
            self._reset_button.move(self.width() - 28, (self.height() - 24) // 2)

    def binding(self) -> list[int]:
        return list(self._binding)

    def set_binding(self, binding: list[int]) -> None:
        self._binding = list(binding or [])
        self._refresh()


# ------------------------------------------------------------------ navigation
class NavButton(QPushButton):
    def __init__(self, icon_name: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(18, 18))
        self._icon_name = icon_name
        self.toggled.connect(self._sync_icon)
        self._sync_icon(False)

    def _sync_icon(self, checked: bool) -> None:
        self.setIcon(icons.icon(self._icon_name, ACCENT if checked else DIM, 18))


class TitleBar(QWidget):
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(50)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 12, 8)
        layout.setSpacing(8)

        # Process status bubble — hugs its text, sits on the left of the content area
        self.process_label = QLabel()
        self.process_label.setObjectName("ProcessBubble")
        self.process_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.process_label.setFixedHeight(30)
        self.process_label.setMinimumWidth(0)
        self.process_label.setMaximumWidth(280)
        self.process_label.setWordWrap(False)
        self.process_label.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.process_label)

        # Flexible gap pushes the window control buttons into the corner
        layout.addStretch(1)

        self._buttons: list[QPushButton] = []
        for icon_name, slot, object_name in (
            ("minimize", self.minimize_clicked, "WinButton"),
            ("maximize", self.maximize_clicked, "WinButton"),
            ("close", self.close_clicked, "WinClose"),
        ):
            button = QPushButton()
            button.setObjectName(object_name)
            button.setFixedSize(34, 30)
            button.setIcon(icons.icon(icon_name, DIM, 15))
            button.setIconSize(QSize(15, 15))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(slot.emit)
            layout.addWidget(button)
            self._buttons.append(button)

    def add_process_control(self, widget: QWidget) -> None:
        """Добавляет кнопку управления процессом в конец строки заголовка."""
        self.layout().addWidget(widget)
        self.layout().removeWidget(widget)
        self.layout().insertWidget(self.layout().count() - len(self._buttons), widget)

    def set_maximized(self, maximized: bool) -> None:
        name = "restore" if maximized else "maximize"
        self._buttons[1].setIcon(icons.icon(name, DIM, 15))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            handle = window.windowHandle()
            if handle is not None:
                handle.startSystemMove()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class Toast(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 18, 10)
        layout.setSpacing(10)
        self._icon = icon_label("check", GREEN, 16)
        self._text = QLabel()
        layout.addWidget(self._icon)
        layout.addWidget(self._text)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._animation = QPropertyAnimation(self._effect, b"opacity", self)
        self._animation.setDuration(180)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.hide()

    def show_message(self, text: str, kind: str = "success") -> None:
        self._text.setText(text)
        self._icon.setPixmap(
            icons.pixmap("check" if kind == "success" else "info", GREEN if kind == "success" else ACCENT, 16)
        )
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._animation.stop()
        self._animation.setStartValue(self._effect.opacity())
        self._animation.setEndValue(1.0)
        self._animation.start()
        self._timer.start(2600)

    def _fade_out(self) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._effect.opacity())
        self._animation.setEndValue(0.0)
        self._animation.finished.connect(self._hide_once)
        self._animation.start()

    def _hide_once(self) -> None:
        try:
            self._animation.finished.disconnect(self._hide_once)
        except (RuntimeError, TypeError):
            pass
        if self._effect.opacity() <= 0.01:
            self.hide()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.move(
            (parent.width() - self.width()) // 2,
            parent.height() - self.height() - 22,
        )


def form_row(text: str, widget: QWidget, hint_text: str = "") -> QWidget:
    row = QWidget()
    layout = QVBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(3)
    line = QHBoxLayout()
    line.setSpacing(12)
    line.addWidget(label(text, "FieldLabel"), 1)
    line.addWidget(widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout.addLayout(line)
    if hint_text:
        layout.addWidget(hint(hint_text))
    return row


def chip(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("Chip")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def page_header(title: str, subtitle: str) -> QWidget:
    wrapper = QWidget()
    layout = QVBoxLayout(wrapper)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    layout.addWidget(label(title, "PageTitle"))
    layout.addWidget(label(subtitle, "PageSubtitle"))
    return wrapper


class HeroCard(QFrame):
    start_clicked = Signal()

    def __init__(
        self,
        stat_labels: list[str],
        hotkey_hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("HeroCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(12)
        self.pill = StatusPill(tr("status.idle"))
        top.addWidget(self.pill, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addStretch(1)
        if hotkey_hint:
            self.hint_label = label(hotkey_hint, "Hint")
            top.addWidget(self.hint_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        self.button = QPushButton(tr("btn.start"))
        self.button.setObjectName("PrimaryButton")
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setMinimumWidth(158)
        self.button.setFixedHeight(56)
        self.button.setIcon(icons.icon("play", "#ffffff", 17))
        self.button.setIconSize(QSize(17, 17))
        self.button.clicked.connect(self.start_clicked.emit)
        bottom.addWidget(self.button)

        self.tiles: list[StatTile] = []
        for caption in stat_labels:
            tile = StatTile(caption, "0")
            self.tiles.append(tile)
            bottom.addWidget(tile, 1)
        layout.addLayout(bottom)
        self._running = False

    def set_running(self, running: bool, status_text: str | None = None) -> None:
        self._running = running
        self.pill.set_state(running, status_text or (tr("status.running") if running else tr("status.idle")))
        self.button.setProperty("running", "true" if running else "false")
        self.button.setText(tr("btn.stop") if running else tr("btn.start"))
        self.button.setIcon(icons.icon("stop" if running else "play", RED if running else "#ffffff", 17))
        repolish(self.button)

    def set_stats(self, values: list[str]) -> None:
        for tile, value in zip(self.tiles, values):
            tile.set_value(value)
