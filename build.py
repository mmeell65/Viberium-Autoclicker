"""Сборка .exe через PyInstaller. Запуск: python build.py"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent
ICON = ROOT / "viberium" / "ui" / "viberium.ico"

# Генерируем иконку приложения
from PySide6.QtGui import QGuiApplication  # noqa: E402

from viberium.ui.appicon import save_ico  # noqa: E402

qt_app = QGuiApplication([])  # QPixmap requires a Qt application instance
save_ico(str(ICON))

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--name=Viberium",
    "--onedir",
    "--windowed",
    f"--icon={ICON}",
    "--add-data",
    "viberium/ui;viberium/ui",
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
print(f"\nГотово: {ROOT / 'dist' / 'Viberium' / 'Viberium.exe'}")
