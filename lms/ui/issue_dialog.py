"""A custom QDialog for lending a book to a member."""
from datetime import date

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QDialog, QFormLayout, QComboBox, QDateEdit, QDialogButtonBox, QLabel

from lms import config
from lms.database import LibraryDB


class IssueDialog(QDialog):
    def __init__(self, db: LibraryDB, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Issue a book")
        self.setMinimumWidth(420)

        form = QFormLayout(self)
        self.book_combo = QComboBox()
        for book, available in db.books(available_only=True):
            self.book_combo.addItem(f"{book.title}  ({available} available)", book.isbn)
        self.member_combo = QComboBox()
        for m in db.members():
            self.member_combo.addItem(f"{m.member_id} · {m.name}", m.member_id)
        self.due_edit = QDateEdit(calendarPopup=True, displayFormat="yyyy-MM-dd")
        self.due_edit.setDate(QDate.currentDate().addDays(config.LOAN_DAYS))
        self.due_edit.setMinimumDate(QDate.currentDate().addDays(1))

        form.addRow("Book", self.book_combo)
        form.addRow("Member", self.member_combo)
        form.addRow("Due date", self.due_edit)
        form.addRow(QLabel(f"Late returns are fined Nu. {config.FINE_PER_DAY} per day.", objectName="muted"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Issue")
        buttons.accepted.connect(self.accept)       # closes the dialog with result Accepted
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> tuple[str, str, date]:
        due = self.due_edit.date()
        return (self.book_combo.currentData(), self.member_combo.currentData(),
                date(due.year(), due.month(), due.day()))
