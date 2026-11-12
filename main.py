"""Entry point: python main.py"""
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from lms import config
from lms.database import LibraryDB
from lms.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setStyleSheet((config.UI_DIR / "style.qss").read_text(encoding="utf-8"))

    try:
        db = LibraryDB(config.DB_FILE)
    except Exception as exc:                       # e.g. the data folder is read-only
        QMessageBox.critical(None, "Cannot open database", f"{config.DB_FILE}\n\n{exc}")
        return 1
    if db.is_empty():
        db.seed_sample()                          # first run: add sample books, members and loans

    window = MainWindow(db)
    window.show()
    return app.exec()                             # start the Qt event loop


if __name__ == "__main__":
    sys.exit(main())
