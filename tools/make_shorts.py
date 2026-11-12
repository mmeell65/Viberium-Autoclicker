"""Render vertical short videos (TikTok / YouTube Shorts / VK Клипы) for Viberium.

No live clicking: the clips are built from clean screenshots of the app
(dark and light theme, English UI) with big captions and a call to action.

Usage:
    python tools/make_shorts.py             # render all clips
    python tools/make_shorts.py features    # render one clip
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPoint, QRect, QSize, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

FFMPEG = ROOT / "tools" / "ffmpeg" / "ffmpeg-9.0.2-essentials_build" / "bin" / "ffmpeg.exe"
OUT_DIR = ROOT / "shorts"
SRC_DIR = OUT_DIR / "src"

W, H = 1080, 1920
FPS = 20

PAGES = ["mouse", "keyboard", "macros", "settings"]


# ----------------------------------------------------------------- source shots
def render_sources() -> None:
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    appdata = Path(os.environ.get("TEMP", r"C:\Windows\Temp")) / "viberium-shots-appdata"
    (appdata / "Viberium").mkdir(parents=True, exist_ok=True)
    (appdata / "Viberium" / "config.json").write_text(
        json.dumps({"language": "en", "version": 3}), encoding="utf-8"
    )

    env = dict(os.environ)
    env["APPDATA"] = str(appdata)
    env["PYTHONPATH"] = str(ROOT)

    for theme in ("dark", "light"):
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "screenshot.py"), f"--theme={theme}"],
            cwd=str(ROOT),
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        for page in PAGES:
            src = ROOT / "shots" / f"{theme}_{page}.png"
            dst = SRC_DIR / f"{page}-{theme}.png"
            if src.exists():
                shutil.copy(src, dst)
                print("source:", dst.name, dst.stat().st_size)


def source(page: str, theme: str = "dark") -> QImage:
    path = SRC_DIR / f"{page}-{theme}.png"
    return QImage(str(path))


# -------------------------------------------------------------------- drawing
def text(p: QPainter, txt: str, rect: QRect, size: int, color: str, bold: bool = True, align=Qt.AlignmentFlag.AlignLeft) -> None:
    font = QFont("Segoe UI", size)
    font.setBold(bold)
    p.setFont(font)
    p.setPen(QColor(color))
    p.drawText(rect, int(align) | int(Qt.TextFlag.TextWordWrap), txt)


def make_card(title: str, subtitle: str) -> QImage:
    """Square title card with the app icon."""
    card = QImage(1024, 1024, QImage.Format.Format_RGB32)
    card.fill(QColor("#0b1222"))
    p = QPainter(card)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(91, 140, 255, 60))
    p.drawEllipse(QRect(-160, 180, 1344, 900))
    icon = QImage(str(ROOT / "docs" / "screenshots" / "icon.png"))
    if not icon.isNull():
        big = icon.scaled(QSize(360, 360), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        p.drawImage((1024 - big.width()) // 2, 250, big)
    font = QFont("Segoe UI", 86)
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#f4f7ff"))
    p.drawText(QRect(0, 640, 1024, 130), int(Qt.AlignmentFlag.AlignCenter), title)
    font2 = QFont("Segoe UI", 38)
    p.setFont(font2)
    p.setPen(QColor("#93a1bf"))
    p.drawText(QRect(0, 780, 1024, 80), int(Qt.AlignmentFlag.AlignCenter), subtitle)
    p.end()
    return card


def frame_from(
    img: QImage,
    caption: str,
    sub: str,
    bullets: list[str],
    progress: float,
    zoom: float,
) -> QImage:
    canvas = QImage(W, H, QImage.Format.Format_RGB32)
    canvas.fill(QColor("#05070d"))
    p = QPainter(canvas)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(91, 140, 255, 34))
    p.drawEllipse(QRect(-260, -300, W + 520, 760))

    text(p, caption, QRect(70, 100, W - 140, 330), 62, "#f4f7ff")
    if sub:
        text(p, sub, QRect(70, 440, W - 140, 110), 29, "#93a1bf", bold=False)

    box = QRect(40, 560, W - 80, 700)
    if not img.isNull():
        scaled = img.scaled(
            QSize(int(box.width() * zoom), int(box.height() * zoom)),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        px = box.x() + (box.width() - scaled.width()) // 2
        py = box.y() + (box.height() - scaled.height()) // 2
        p.setPen(QPen(QColor("#2a3550"), 3))
        p.setBrush(QColor("#0b1222"))
        p.drawRoundedRect(QRect(px - 10, py - 10, scaled.width() + 20, scaled.height() + 20), 22, 22)
        p.drawImage(px, py, scaled)

    if bullets:
        y = 1300
        for line in bullets:
            p.setPen(QColor("#3ddc97"))
            font_b = QFont("Segoe UI", 29)
            font_b.setBold(True)
            p.setFont(font_b)
            p.drawText(QRect(70, y, 60, 50), int(Qt.AlignmentFlag.AlignLeft), "•")
            text(p, line, QRect(128, y, W - 200, 80), 29, "#c9d6f5", bold=False)
            y += 86

    text(p, "Бесплатно · Windows 10/11 · open source (MIT)", QRect(40, 1650, W - 80, 60), 30, "#8fb0ff", align=Qt.AlignmentFlag.AlignCenter)
    text(p, "github.com/mmeell65/Viberium-Autoclicker", QRect(40, 1710, W - 80, 50), 26, "#93a1bf", bold=False, align=Qt.AlignmentFlag.AlignCenter)
    text(p, "@viberium_autoclicker", QRect(40, 1760, W - 80, 50), 30, "#3ddc97", align=Qt.AlignmentFlag.AlignCenter)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(91, 140, 255, 70))
    p.drawRect(0, H - 10, int(W * progress), 10)
    p.end()
    return canvas


# ----------------------------------------------------------------------- clips
CLIPS = [
    {
        "name": "features",
        "segments": [
            ("card", "Бесплатный\nавтокликер\nдля Windows", "Viberium 1.1.0 · мышь, клавиатура, макросы", [], 3.0),
            ("mouse", "Кликер мыши", "Тонкая настройка под свою задачу", ["ЛКМ / ПКМ / СКМ, двойной и тройной клик", "Интервал, разброс и лимиты по кликам"], 4.0),
            ("keyboard", "Кликер клавиатуры", "Несколько клавиш и сочетаний сразу", ["Ctrl, Shift, Alt, Win в любых комбинациях", "Режимы «одновременно» и «по очереди»"], 4.0),
            ("macros", "Макросы", "Записал один раз — повторяет сколько нужно", ["Клики, движение мыши и клавиши", "Импорт/экспорт JSON, библиотека макросов"], 4.0),
            ("settings", "Целевое окно", "Кликает только там, где нужно", ["Профили настроек, тёмная и светлая темы", "Русский и английский интерфейс"], 4.0),
            ("card", "Скачай\nбесплатно", "Без установщика · MIT · Windows 10/11", [], 3.0),
        ],
    },
    {
        "name": "keyboard",
        "segments": [
            ("card", "Кликер\nклавиатуры", "Viberium 1.1.0", [], 3.0),
            ("keyboard", "Сочетания\nи режимы", "Несколько клавиш одновременно", ["Любые комбинации с Ctrl, Shift, Alt, Win", "Пауза между нажатиями, перестановка строк"], 5.0),
            ("macros", "Макросы\nв один клик", "Запись и воспроизведение", ["Своя скорость и повторы", "Готовые паки макросов — в Telegram-канале"], 4.0),
            ("card", "Скачай\nбесплатно", "Windows 10/11 · open source", [], 3.0),
        ],
    },
    {
        "name": "free",
        "segments": [
            ("card", "Бесплатно.\nБез рекламы.\nOpen source.", "Viberium 1.1.0 · MIT · ~100 МБ", [], 4.0),
            ("mouse", "Что умеет", "Всё в одном приложении", ["Кликер мыши и клавиатуры", "Макросы, горячие клавиши, целевое окно"], 5.0),
            ("settings", "Темы и профили", "Под свою задачу", ["Тёмная и светлая тема", "Профили: «Тесты», «Работа», «Игры»"], 4.0),
            ("card", "Ссылка\nв описании", "github.com/mmeell65/Viberium-Autoclicker", [], 3.0),
        ],
    },
]

INTRO_IMG = "intro.png"


def build_intro_card() -> QImage:
    """Title card built from the app icon."""
    canvas = QImage(W, H, QImage.Format.Format_RGB32)
    canvas.fill(QColor("#05070d"))
    p = QPainter(canvas)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(91, 140, 255, 40))
    p.drawEllipse(QRect(-300, 300, W + 600, 900))
    icon = QImage(str(ROOT / "docs" / "screenshots" / "icon.png"))
    if not icon.isNull():
        big = icon.scaled(QSize(360, 360), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        p.drawImage((W - big.width()) // 2, 620, big)
    font = QFont("Segoe UI", 84)
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#f4f7ff"))
    p.drawText(QRect(0, 1060, W, 120), int(Qt.AlignmentFlag.AlignCenter), "Viberium")
    font2 = QFont("Segoe UI", 36)
    p.setFont(font2)
    p.setPen(QColor("#93a1bf"))
    p.drawText(QRect(0, 1180, W, 70), int(Qt.AlignmentFlag.AlignCenter), "Auto clicker for Windows")
    p.end()
    return canvas


def render_clip(clip: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"viberium-{clip['name']}.mp4"
    total_time = sum(seg[4] for seg in clip["segments"])
    cmd = [
        str(FFMPEG), "-y",
        "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{W}x{H}", "-framerate", str(FPS),
        "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    intro = make_card("Viberium", "Auto clicker for Windows")
    elapsed = 0.0
    try:
        for kind, caption, sub, bullets, dur in clip["segments"]:
            if kind == "card":
                img = intro
            else:
                img = source(kind, "dark")
            frames = int(dur * FPS)
            for i in range(frames):
                t = elapsed + i / FPS
                zoom = 1.0 + 0.035 * (i / max(frames - 1, 1))
                frame = frame_from(img, caption, sub, bullets, t / total_time, zoom)
                rgb = frame.convertToFormat(QImage.Format.Format_RGB888)
                proc.stdin.write(rgb.constBits().tobytes())
            elapsed += dur
    finally:
        proc.stdin.close()
        proc.wait()
    print("saved", out, out.stat().st_size if out.exists() else 0)
    return out


def make_thumb(clip: dict) -> None:
    img = source("mouse", "dark")
    canvas = QImage(W, H, QImage.Format.Format_RGB32)
    canvas.fill(QColor("#05070d"))
    p = QPainter(canvas)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(91, 140, 255, 40))
    p.drawEllipse(QRect(-260, -200, W + 520, 700))
    text(p, clip["segments"][1][1] if len(clip["segments"]) > 1 else "Viberium", QRect(70, 100, W - 140, 330), 62, "#f4f7ff")
    if not img.isNull():
        scaled = img.scaled(QSize(1000, 1000), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        p.drawImage((W - scaled.width()) // 2, 560, scaled)
    text(p, "Бесплатно · Windows 10/11", QRect(40, 1700, W - 80, 60), 30, "#8fb0ff", align=Qt.AlignmentFlag.AlignCenter)
    p.end()
    path = OUT_DIR / f"viberium-{clip['name']}-thumb.jpg"
    canvas.save(str(path), "JPG", 92)
    print("thumb", path)


def main() -> None:
    if not FFMPEG.exists():
        print("ffmpeg not found:", FFMPEG)
        raise SystemExit(1)

    app = QApplication(sys.argv)
    render_sources()

    wanted = sys.argv[1:] or None
    for clip in CLIPS:
        if wanted and clip["name"] not in wanted:
            continue
        print("rendering", clip["name"])
        render_clip(clip)
        make_thumb(clip)


if __name__ == "__main__":
    main()
