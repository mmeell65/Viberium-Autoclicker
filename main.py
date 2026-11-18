"""Viberium entry point."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from viberium.config import APP_NAME, Settings  # noqa: E402
from viberium.core.winapi import enable_dpi_awareness  # noqa: E402
from viberium.i18n import tr  # noqa: E402
from viberium.ui.appicon import app_icon  # noqa: E402
from viberium.ui.main_window import MainWindow  # noqa: E402
from viberium.ui.theme import apply_theme  # noqa: E402


def main() -> int:
    enable_dpi_awareness()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setWindowIcon(app_icon())
    app.setQuitOnLastWindowClosed(False)

    settings = Settings()
    tr.set_language(settings.get_value("language", "ru"))
    apply_theme(app, settings.get_value("theme", "dark"))

    window = MainWindow()

    minimized = "--minimized" in sys.argv or (
        settings["general"].get("start_minimized", False) and window._tray is not None
    )
    if minimized:
        window.hide()
    else:
        window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
