"""The main window: menu bar, four tabs and a status bar. Tabs talk to each other through signals."""
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QLabel, QFileDialog, QMessageBox

from lms import config
from lms.database import LibraryDB, LibraryError
from lms.ui.books_tab import BooksTab
from lms.ui.members_tab import MembersTab
from lms.ui.loans_tab import LoansTab
from lms.ui.summary_tab import SummaryTab


class MainWindow(QMainWindow):
    def __init__(self, db: LibraryDB):
        super().__init__()
        self.db = db
        self.setWindowTitle(config.WINDOW_TITLE)
        self.resize(1150, 700)
        self.setMinimumSize(880, 540)

        self.books = BooksTab(db)
        self.members = MembersTab(db)
        self.loans = LoansTab(db)
        self.summary = SummaryTab(db)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.books, "Books")
        self.tabs.addTab(self.members, "Members")
        self.tabs.addTab(self.loans, "Loans")
        self.tabs.addTab(self.summary, "Summary")
        self.setCentralWidget(self.tabs)

        # When one tab changes the data, the others reload what they show.
        self.books.data_changed.connect(self.refresh_all)
        self.members.data_changed.connect(self.refresh_all)
        self.loans.data_changed.connect(self.refresh_all)
        self.tabs.currentChanged.connect(self.refresh_all)

        self._build_menu()
        self.statusBar().showMessage(f"Database: {config.DB_FILE.name}")
        self.statusBar().addPermanentWidget(QLabel(f"{config.STUDENT_NAME}  |  {config.ROLL_NO}  "))

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        export = QAction("&Export loans to CSV...", self, shortcut=QKeySequence("Ctrl+E"))
        export.triggered.connect(self.on_export)
        quit_ = QAction("E&xit", self, shortcut=QKeySequence("Ctrl+Q"))
        quit_.triggered.connect(self.close)
        file_menu.addActions([export, quit_])

        loans_menu = self.menuBar().addMenu("&Loans")
        issue = QAction("&Issue a book...", self, shortcut=QKeySequence("Ctrl+I"))
        issue.triggered.connect(self.on_issue)
        loans_menu.addAction(issue)

        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("&About", self)
        about.triggered.connect(self.on_about)
        help_menu.addAction(about)

    # ------------------------------------------------------------- slots
    def refresh_all(self, *_) -> None:
        self.books.refresh()
        self.members.refresh()
        self.loans.refresh()
        self.summary.refresh()

    def on_issue(self) -> None:
        self.tabs.setCurrentWidget(self.loans)
        self.loans.on_issue()

    def on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export loans", "loans.csv", "CSV files (*.csv)")
        if not path:
            return
        try:
            n = self.db.export_loans_csv(path)
        except LibraryError as err:
            QMessageBox.critical(self, "Export failed", str(err))
            return
        self.statusBar().showMessage(f"Exported {n} loans to {path}", 5000)

    def on_about(self) -> None:
        QMessageBox.about(self, "About", f"<b>{config.APP_NAME}</b><br>Unit V assignment - PyQt6<br><br>"
                                         f"Name: {config.STUDENT_NAME}<br>Roll no: {config.ROLL_NO}")

    def closeEvent(self, event):
        self.db.close()                  # SQLite has already saved every change; just close cleanly
        event.accept()
