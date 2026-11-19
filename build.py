"""Сборка .exe через PyInstaller. Запуск: python build.py"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

ROOT = Path(__file__).resolve().parent
ICON = ROOT / "viberium" / "ui" / "viberium.ico"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def clean_outputs() -> None:
    """Удаляет прошлые сборки целиком.

    PyInstaller кладёт новые файлы поверх старых, и в `dist/Viberium` остаются
    библиотеки из предыдущей версии. Приложение начинает грузить смесь файлов
    разных сборок (старый `base_library.zip` рядом с новым `PySide6`) и может
    зависнуть при выходе: процесс висит в диспетчере задач со скрытыми окнами.
    """
    for folder in (BUILD, DIST):
        if folder.exists():
            print(f">>> очистка {folder}")
            shutil.rmtree(folder, ignore_errors=True)


# Генерируем иконку приложения
from PySide6.QtGui import QGuiApplication  # noqa: E402

from viberium.ui.appicon import save_ico  # noqa: E402

qt_app = QGuiApplication([])  # QPixmap requires a Qt application instance
save_ico(str(ICON))

clean_outputs()

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--name=Viberium",
    "--onedir",
    "--windowed",
    f"--icon={ICON}",
    "--hidden-import=viberium.core.winapi",
    "--hidden-import=viberium.core.hooks",
    "--hidden-import=viberium.core.engine",
    "--hidden-import=viberium.core.hotkeys",
    "--hidden-import=viberium.core.macros",
    "--clean",
    "--noconfirm",
    "--log-level=INFO",
    str(ROOT / "main.py"),
]

print(">>>", " ".join(cmd))
subprocess.run(cmd, check=True)

exe = DIST / "Viberium" / "Viberium.exe"
internal = exe.parent / "_internal"
lib = internal / "base_library.zip"
stamps = [exe.stat().st_mtime, lib.stat().st_mtime] if lib.exists() else [exe.stat().st_mtime]
age = max(stamps) - min(stamps)
if age > 60:
    raise SystemExit(
        f"Сборка неполная: файлы в {internal} из разных прогонов "
        f"(разброс {age / 60:.0f} мин). Удалите папку dist и повторите."
    )
print(f"\nDone: {exe}")
