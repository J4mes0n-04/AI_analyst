#!/usr/bin/env python3
"""Entry point: AI Analyst desktop app (PyQt6)."""

import sys

from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("AI Analyst")
    app.setOrganizationName("AI Analyst")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
