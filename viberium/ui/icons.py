"""Vector icons rendered from inline SVG (no external assets needed)."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_WRAP = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
    'fill="none" stroke="{c}" stroke-width="1.7" stroke-linecap="round" '
    'stroke-linejoin="round">{body}</svg>'
)

_BODIES: dict[str, str] = {
    "cursor": '<path d="M5.2 2.8 18.8 11l-6 1.4-2.9 6.1z" fill="{c}" stroke="none"/>',
    "mouse": '<rect x="7" y="2.5" width="10" height="19" rx="5"/><path d="M12 6v3.5"/>',
    "keyboard": (
        '<rect x="2.5" y="6.5" width="19" height="11" rx="2.5"/>'
        '<path d="M6 10h.01M9.5 10h.01M13 10h.01M16.5 10h.01'
        'M6 13.5h.01M9.5 13.5h.01M13 13.5h.01M16.5 13.5h.01M8 16.5h8"/>'
    ),
    "macro": (
        '<path d="M4.2 12a7.8 7.8 0 0 1 13.3-5.5L20 9"/>'
        '<path d="M20 4.5V9h-4.5"/>'
        '<path d="M19.8 12a7.8 7.8 0 0 1-13.3 5.5L4 15"/>'
        '<path d="M4 19.5V15h4.5"/>'
    ),
    "settings": (
        '<path d="M3 7h6.5M15 7h6"/><circle cx="12.2" cy="7" r="2.3"/>'
        '<path d="M3 12h10M18.5 12H21"/><circle cx="15.7" cy="12" r="2.3"/>'
        '<path d="M3 17h3M9.5 17H21"/><circle cx="6.7" cy="17" r="2.3"/>'
    ),
    "play": '<path d="M8 5.4v13.2L19 12z" fill="{c}" stroke="none"/>',
    "stop": '<rect x="6.5" y="6.5" width="11" height="11" rx="2.4" fill="{c}" stroke="none"/>',
    "record": '<circle cx="12" cy="12" r="6" fill="{c}" stroke="none"/>',
    "trash": '<path d="M4 7h16M9.5 7V4.8h5V7M6.5 7l1 13h9l1-13M10.5 11v5M13.5 11v5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "target": (
        '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.4"/>'
        '<path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>'
    ),
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "close": '<path d="M6.2 6.2l11.6 11.6M17.8 6.2 6.2 17.8"/>',
    "minimize": '<path d="M6 12h12"/>',
    "maximize": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "restore": '<rect x="5" y="8" width="11" height="11" rx="2"/><path d="M8.5 8V5h10.5v10.5h-3"/>',
    "globe": (
        '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17"/>'
        '<path d="M12 3.5c2.4 2.3 3.7 5.3 3.7 8.5s-1.3 6.2-3.7 8.5'
        'c-2.4-2.3-3.7-5.3-3.7-8.5s1.3-6.2 3.7-8.5z"/>'
    ),
    "telegram": '<path d="M21.2 3.4 2.8 10.6l5.6 2 2 5.8 3-3.6 4.2 2.9z"/><path d="M8.4 12.6 21.2 3.4l-7.5 16.9"/>',
    "folder": (
        '<path d="M3.5 7.5a2 2 0 0 1 2-2h3.4l2 2.5h7.6a2 2 0 0 1 2 2v6.5a2 2 0 0 1-2 2'
        'h-13a2 2 0 0 1-2-2z"/>'
    ),
    "save": (
        '<path d="M5 4.5h11l3.5 3.5v11.5h-15z"/><path d="M8.5 4.5v5h7v-5M8.5 19.5v-6h7v6"/>'
    ),
    "check": '<path d="M5 12.5 9.5 17 19 7"/>',
    "chevron-up": '<path d="M7 14.5 12 9.5l5 5"/>',
    "chevron-down": '<path d="M7 9.5 12 14.5l5-5"/>',
    "bolt": '<path d="M13.2 2.5 5.6 13.6h5.2l-1 7.9 7.6-11.2h-5.2z" fill="{c}" stroke="none"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v6M12 7.6h.01"/>',
    "power": '<path d="M12 3v8"/><path d="M7.4 6.1a7 7 0 1 0 9.2 0"/>',
    "pause": '<path d="M9.5 5.5v13M14.5 5.5v13"/>',
    "sparkle": (
        '<path d="M12 3.5 13.8 9l5.5 1.8-5.5 1.8L12 18l-1.8-5.4L4.7 10.8 10.2 9z" '
        'fill="{c}" stroke="none"/>'
    ),
    "grid": (
        '<rect x="4" y="4" width="7" height="7" rx="1.6"/><rect x="13" y="4" width="7" height="7" rx="1.6"/>'
        '<rect x="4" y="13" width="7" height="7" rx="1.6"/><rect x="13" y="13" width="7" height="7" rx="1.6"/>'
    ),
    "shield": '<path d="M12 3.5 5 6v6c0 4 3 7.2 7 8.5 4-1.3 7-4.5 7-8.5V6z"/>',
}

_CACHE: dict[tuple[str, str, int], QIcon] = {}


def icon(name: str, color: str, size: int = 18) -> QIcon:
    key = (name, color, size)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    body = _BODIES.get(name, _BODIES["grid"]).replace("{c}", color)
    svg = _WRAP.format(c=color, body=body)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    dpr = 2.0
    pixmap = QPixmap(int(size * dpr), int(size * dpr))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(dpr)
    result = QIcon(pixmap)
    _CACHE[key] = result
    return result


def pixmap(name: str, color: str, size: int = 18) -> QPixmap:
    return icon(name, color, size).pixmap(QSize(size, size))
