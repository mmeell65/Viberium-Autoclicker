"""Application icon drawn with QPainter (no binary assets required)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)


def _draw(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Dark graphite body
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#252a34"))
    gradient.setColorAt(0.55, QColor("#1b1f27"))
    gradient.setColorAt(1.0, QColor("#12151b"))

    radius = size * 0.24
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    # subtle top highlight
    glow = QLinearGradient(0, 0, size * 0.6, size * 0.6)
    glow.setColorAt(0.0, QColor(255, 255, 255, 26))
    glow.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setBrush(glow)
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    # accent ring around the edge
    painter.setBrush(Qt.BrushStyle.NoBrush)
    pen = QPen(QColor(91, 140, 255, 190))
    pen.setWidth(max(1.0, size * 0.035))
    painter.setPen(pen)
    inset = pen.width() / 2
    painter.drawRoundedRect(
        QRectF(inset, inset, size - pen.width(), size - pen.width()),
        radius - inset,
        radius - inset,
    )
    painter.setPen(Qt.PenStyle.NoPen)

    scale = size / 24.0
    cursor = QPolygonF(
        [
            QPointF(7.2, 4.2),
            QPointF(18.6, 12.2),
            QPointF(12.9, 13.3),
            QPointF(10.4, 19.2),
        ]
    )
    scaled = QPolygonF([QPointF(point.x() * scale, point.y() * scale) for point in cursor])

    shadow = QPainterPath()
    shadow.addPolygon(scaled)
    painter.setBrush(QColor(0, 0, 0, 110))
    painter.drawPath(shadow.translated(size * 0.014, size * 0.02))

    # cursor body with a blue-to-violet gradient
    cursor_gradient = QLinearGradient(
        size * 0.2, size * 0.1, size * 0.8, size * 0.85
    )
    cursor_gradient.setColorAt(0.0, QColor("#8fb0ff"))
    cursor_gradient.setColorAt(1.0, QColor("#5b8cff"))
    painter.setBrush(cursor_gradient)
    painter.drawPolygon(scaled)
    painter.end()
    return pixmap


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_draw(size))
    return icon


def icon_pixmap(size: int = 64) -> QPixmap:
    return _draw(size)


def save_ico(path: str) -> bool:
    """Write a multi-size .ico file (used by the build script)."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice

    images = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        _draw(size).save(buffer, "PNG")
        images.append((size, bytes(buffer.data())))
        buffer.close()

    header = bytearray()
    header += (0).to_bytes(2, "little")   # reserved
    header += (1).to_bytes(2, "little")   # type: icon
    header += len(images).to_bytes(2, "little")

    offset = 6 + 16 * len(images)
    entries = bytearray()
    payload = bytearray()
    for size, data in images:
        entries += bytes([0 if size >= 256 else size, 0 if size >= 256 else size])
        entries += bytes([0, 0])
        entries += (1).to_bytes(2, "little")   # planes
        entries += (32).to_bytes(2, "little")  # bpp
        entries += len(data).to_bytes(4, "little")
        entries += offset.to_bytes(4, "little")
        payload += data
        offset += len(data)

    with open(path, "wb") as handle:
        handle.write(header + entries + payload)
    return True
