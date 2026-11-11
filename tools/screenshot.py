"""Render the UI to PNG files without opening a visible window (dev helper)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QEventLoop, QTimer, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from viberium.core.winapi import enable_dpi_awareness  # noqa: E402
from viberium.ui.main_window import MainWindow  # noqa: E402
from viberium.ui.theme import apply_theme  # noqa: E402


def settle(ms: int = 350) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def main() -> None:
    enable_dpi_awareness()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    theme = "dark"
    for arg in sys.argv[1:]:
        if arg.startswith("--theme="):
            theme = arg.split("=", 1)[1]
    apply_theme(app, theme)

    window = MainWindow()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    settle(600)

    out = ROOT / "shots"
    out.mkdir(exist_ok=True)
    pages = ["mouse", "keyboard", "macros", "settings"]
    for index, name in enumerate(pages):
        window._switch(index)
        settle(250)
        window.grab().save(str(out / f"{theme}_{name}.png"))
    print("saved", out)
    window.shutdown()


if __name__ == "__main__":
    main()
