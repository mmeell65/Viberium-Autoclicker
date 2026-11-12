"""Generate Telegram channel assets for Viberium (dev helper)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor,
    QFont,
    QFontMetricsF,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

OUT = ROOT / "telegram"
ICON_PATH = ROOT / "docs" / "screenshots" / "icon.png"
SHOTS = ROOT / "docs" / "screenshots"

ACCENT = QColor("#5B8CFF")
ACCENT_SOFT = QColor("#8FB0FF")
TEXT = QColor("#F2F5FF")
MUTED = QColor("#93A1BF")
BORDER = QColor("#2A3550")
BG_DARK = QColor("#080B12")


def font(size: int, weight: QFont.Weight = QFont.Weight.Normal, spacing: float = 0.0) -> QFont:
    value = QFont("Segoe UI")
    value.setPixelSize(size)
    value.setWeight(weight)
    if spacing:
        value.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return value


def background(width: int, height: int) -> tuple[QImage, QPainter]:
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(BG_DARK)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor("#0B1222"))
    gradient.setColorAt(0.55, QColor("#0E1526"))
    gradient.setColorAt(1.0, QColor("#111B33"))
    painter.fillRect(image.rect(), gradient)

    glow = QRadialGradient(width * 0.16, height * 0.14, max(width, height) * 0.75)
    glow.setColorAt(0.0, QColor(91, 140, 255, 70))
    glow.setColorAt(1.0, QColor(91, 140, 255, 0))
    painter.fillRect(image.rect(), glow)

    glow2 = QRadialGradient(width * 0.92, height * 0.96, max(width, height) * 0.55)
    glow2.setColorAt(0.0, QColor(38, 165, 228, 40))
    glow2.setColorAt(1.0, QColor(38, 165, 228, 0))
    painter.fillRect(image.rect(), glow2)
    return image, painter


def rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def draw_icon(painter: QPainter, rect: QRectF) -> None:
    icon = QImage(str(ICON_PATH))
    painter.drawImage(rect, icon)


def draw_screenshot(painter: QPainter, rect: QRectF, name: str, radius: float = 22) -> None:
    source = QImage(str(SHOTS / name))
    if source.isNull():
        return
    scaled = source.scaled(
        rect.size().toSize(),
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    source_rect = QRectF(
        max((scaled.width() - rect.width()) / 2, 0),
        max((scaled.height() - rect.height()) / 2, 0),
        rect.width(),
        rect.height(),
    )
    path = rounded_path(rect, radius)

    shadow = rect.adjusted(10, 14, 10, 14)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 90))
    painter.drawPath(rounded_path(shadow, radius))

    painter.save()
    painter.setClipPath(path)
    painter.drawImage(rect, scaled, source_rect)
    painter.restore()

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(BORDER, 2))
    painter.drawPath(path)


def draw_chip(painter: QPainter, x: float, y: float, text: str, size: int = 22) -> float:
    painter.setFont(font(size, QFont.Weight.DemiBold))
    width = QFontMetricsF(painter.font()).horizontalAdvance(text) + 38
    rect = QRectF(x, y, width, size + 26)
    painter.setPen(QPen(QColor(91, 140, 255, 110), 1.4))
    painter.setBrush(QColor(91, 140, 255, 26))
    painter.drawPath(rounded_path(rect, rect.height() / 2))
    painter.setPen(ACCENT_SOFT)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    return x + width + 12


def draw_brand(painter: QPainter, x: float, y: float, icon_size: float = 52) -> None:
    draw_icon(painter, QRectF(x, y, icon_size, icon_size))
    painter.setFont(font(21, QFont.Weight.Bold, 3.2))
    painter.setPen(MUTED)
    painter.drawText(
        QRectF(x + icon_size + 16, y - 2, 420, icon_size + 4),
        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        "VIBERIUM",
    )


def draw_footer(painter: QPainter, width: int, height: int) -> None:
    painter.setFont(font(21))
    painter.setPen(MUTED)
    painter.drawText(
        QRectF(64, height - 74, width - 128, 32),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        "github.com/mmeell65/Viberium-Autoclicker",
    )
    painter.setPen(ACCENT_SOFT)
    painter.drawText(
        QRectF(64, height - 74, width - 128, 32),
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        "t.me/viberium_autoclicker",
    )


def draw_bullets(painter: QPainter, x: float, y: float, lines: list[str], size: int = 30) -> float:
    painter.setFont(font(size))
    for line in lines:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ACCENT)
        painter.drawEllipse(QRectF(x, y + size * 0.42, 9, 9))
        painter.setPen(QColor("#D9E2FA"))
        painter.drawText(QRectF(x + 28, y - 4, 900, size + 16), Qt.AlignmentFlag.AlignLeft, line)
        y += size + 22
    return y


def make_avatar() -> None:
    size = 512
    image, painter = background(size, size)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(91, 140, 255, 90), 5))
    painter.drawEllipse(QRectF(26, 26, size - 52, size - 52))
    draw_icon(painter, QRectF(106, 106, 300, 300))
    painter.end()
    image.save(str(OUT / "avatar.png"))


def make_banner() -> None:
    width, height = 1280, 640
    image, painter = background(width, height)
    draw_brand(painter, 72, 62, 56)

    painter.setFont(font(88, QFont.Weight.Bold, -2))
    painter.setPen(TEXT)
    painter.drawText(QRectF(72, 156, 620, 110), Qt.AlignmentFlag.AlignLeft, "Viberium")

    painter.setFont(font(36, QFont.Weight.Medium))
    painter.setPen(QColor("#B8C6E6"))
    painter.drawText(QRectF(72, 264, 620, 52), Qt.AlignmentFlag.AlignLeft, "Автокликер для Windows")

    painter.setFont(font(24))
    painter.setPen(MUTED)
    painter.drawText(
        QRectF(72, 330, 580, 80),
        Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
        "Точные клики и нажатия, макросы, горячие клавиши и работа только в выбранном окне.",
    )

    x = 72.0
    x = draw_chip(painter, x, 438, "Мышь")
    x = draw_chip(painter, x, 438, "Клавиатура")
    x = draw_chip(painter, x, 438, "Макросы")
    draw_chip(painter, x, 438, "F8")

    draw_screenshot(painter, QRectF(690, 104, 520, 356), "keyboard-dark.png", 24)

    painter.setFont(font(21))
    painter.setPen(MUTED)
    painter.drawText(QRectF(72, 552, 600, 34), Qt.AlignmentFlag.AlignLeft, "github.com/mmeell65/Viberium-Autoclicker")
    painter.setPen(ACCENT_SOFT)
    painter.drawText(QRectF(690, 492, 520, 34), Qt.AlignmentFlag.AlignRight, "t.me/viberium_autoclicker")

    painter.end()
    image.save(str(OUT / "banner.png"))


def make_post(
    filename: str,
    title: str,
    subtitle: str,
    bullets: list[str],
    screenshot: str | None = None,
    cta: tuple[str, str] | None = None,
) -> None:
    width, height = 1080, 1080
    image, painter = background(width, height)
    draw_brand(painter, 64, 58, 48)

    painter.setFont(font(66, QFont.Weight.Bold, -1))
    painter.setPen(TEXT)
    painter.drawText(
        QRectF(64, 170, 952, 170),
        Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
        title,
    )

    painter.setFont(font(31, QFont.Weight.Medium))
    painter.setPen(QColor("#B8C6E6"))
    painter.drawText(
        QRectF(64, 340, 952, 80),
        Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
        subtitle,
    )

    y = draw_bullets(painter, 64, 440, bullets, 29)
    if screenshot:
        top = max(y + 40, 610)
        draw_screenshot(painter, QRectF(64, top, 952, height - top - 110), screenshot, 24)
    elif cta:
        rect = QRectF(64, 650, 952, 270)
        painter.setPen(QPen(QColor(91, 140, 255, 130), 1.6))
        painter.setBrush(QColor(91, 140, 255, 24))
        painter.drawPath(rounded_path(rect, 26))
        painter.setFont(font(40, QFont.Weight.Bold))
        painter.setPen(TEXT)
        painter.drawText(
            QRectF(104, 700, 700, 60),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            cta[0],
        )
        painter.setFont(font(26))
        painter.setPen(QColor("#C6D4F2"))
        painter.drawText(
            QRectF(104, 770, 700, 100),
            Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
            cta[1],
        )
        painter.setFont(font(76, QFont.Weight.Bold))
        painter.setPen(ACCENT_SOFT)
        painter.drawText(
            QRectF(rect.right() - 190, rect.top() + 60, 130, 130),
            Qt.AlignmentFlag.AlignCenter,
            "↓",
        )

    draw_footer(painter, width, height)
    painter.end()
    image.save(str(OUT / filename))


def main() -> None:
    OUT.mkdir(exist_ok=True)
    app = QGuiApplication(sys.argv)  # noqa: F841
    make_avatar()
    make_banner()
    make_post(
        "post-01.png",
        "Автокликер для Windows",
        "Viberium — точные клики и нажатия без лишних посредников.",
        [
            "Кликер мыши и клавиатуры",
            "Макросы и глобальные горячие клавиши",
            "Тёмная и светлая темы",
        ],
        "mouse-dark.png",
    )
    make_post(
        "post-02.png",
        "Кликер мыши",
        "Полный контроль над каждым кликом.",
        [
            "ЛКМ / ПКМ / СКМ",
            "Одинарный, двойной и тройной клик",
            "Интервал, разброс и зажатие",
            "Лимиты и фиксированная позиция",
        ],
        "mouse-dark.png",
    )
    make_post(
        "post-03.png",
        "Клавиатура",
        "Несколько кнопок и сочетания — одновременно или по очереди.",
        [
            "Ctrl + S, Alt + Enter и другие",
            "Захват с Shift, Ctrl, Alt, Win",
            "Перестановка кнопок и пауза",
            "Лимиты и задержка перед стартом",
        ],
        "keyboard-dark.png",
    )
    make_post(
        "post-04.png",
        "Макросы",
        "Записал — воспроизвёл.",
        [
            "Клики, движение мыши и клавиши",
            "Своя скорость и повторы",
            "Библиотека макросов",
            "Импорт и экспорт в JSON",
        ],
        "macros-dark.png",
    )
    make_post(
        "post-05.png",
        "Горячие клавиши",
        "Управление без переключения окон.",
        [
            "Старт и стоп",
            "Удержание для работы",
            "Аварийный стоп — F8",
            "Отдельные комбинации для каждого режима",
        ],
        "settings-dark.png",
    )
    make_post(
        "post-06.png",
        "Установка за 3 шага",
        "Без установщика и лишних настроек.",
        [
            "Скачайте Viberium-windows.zip",
            "Распакуйте архив целиком",
            "Запустите Viberium.exe",
        ],
        cta=(
            "Скачать последнюю версию",
            "github.com/mmeell65/Viberium-Autoclicker/releases/latest",
        ),
    )
    print("saved", OUT)


if __name__ == "__main__":
    main()
