"""Light / dark Qt stylesheets."""

LIGHT_QSS = """
QMainWindow, QWidget { background-color: #f8fafc; color: #0f172a; font-size: 13px; }
QFrame#card { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; }
QListWidget { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px; }
QListWidget::item { padding: 10px 12px; border-radius: 4px; }
QListWidget::item:selected { background: #e0e7ff; color: #1e1b4b; }
QPushButton { background: #4f46e5; color: white; border: none; padding: 8px 16px; border-radius: 6px; }
QPushButton:hover { background: #4338ca; }
QPushButton:pressed { background: #3730a3; }
QPushButton#secondary { background: #e2e8f0; color: #0f172a; }
QPushButton#secondary:hover { background: #cbd5e1; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
  border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px; background: #ffffff;
}
QTabWidget::pane { border: 1px solid #e2e8f0; border-radius: 6px; background: #ffffff; }
QTabBar::tab { padding: 8px 14px; margin-right: 2px; }
QTabBar::tab:selected { background: #ffffff; border: 1px solid #e2e8f0; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QHeaderView::section { background: #f1f5f9; padding: 6px; border: 1px solid #e2e8f0; }
QTableWidget { gridline-color: #e2e8f0; background: #ffffff; }
QScrollBar:vertical { width: 10px; background: #f1f5f9; }
QScrollBar::handle:vertical { background: #cbd5e1; min-height: 24px; border-radius: 4px; }
"""

DARK_QSS = """
QMainWindow, QWidget { background-color: #0f172a; color: #e2e8f0; font-size: 13px; }
QFrame#card { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; }
QListWidget { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 4px; }
QListWidget::item { padding: 10px 12px; border-radius: 4px; }
QListWidget::item:selected { background: #312e81; color: #e0e7ff; }
QPushButton { background: #6366f1; color: white; border: none; padding: 8px 16px; border-radius: 6px; }
QPushButton:hover { background: #4f46e5; }
QPushButton:pressed { background: #4338ca; }
QPushButton#secondary { background: #334155; color: #e2e8f0; }
QPushButton#secondary:hover { background: #475569; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
  border: 1px solid #475569; border-radius: 6px; padding: 6px; background: #1e293b; color: #e2e8f0;
}
QTabWidget::pane { border: 1px solid #334155; border-radius: 6px; background: #1e293b; }
QTabBar::tab { padding: 8px 14px; margin-right: 2px; color: #94a3b8; }
QTabBar::tab:selected { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QHeaderView::section { background: #334155; padding: 6px; border: 1px solid #475569; color: #e2e8f0; }
QTableWidget { gridline-color: #334155; background: #1e293b; color: #e2e8f0; }
QScrollBar:vertical { width: 10px; background: #1e293b; }
QScrollBar::handle:vertical { background: #475569; min-height: 24px; border-radius: 4px; }
QToolTip { background: #334155; color: #f8fafc; border: 1px solid #475569; }
"""


def stylesheet_for_theme(dark: bool) -> str:
    return DARK_QSS if dark else LIGHT_QSS
