"""Loans tab: issue books, return them, and filter loans by status."""
from datetime import date

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QRadioButton, QButtonGroup,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QLabel,
)

from lms.database import LibraryDB, LibraryError
from lms.models import ValidationError
from lms.ui.issue_dialog import IssueDialog

COLUMNS = ["#", "Book", "Member", "Issued", "Due", "Returned", "Days late", "Fine (Nu.)"]
STATUSES = ["Active", "Overdue", "Returned", "All"]


class LoansTab(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, db: LibraryDB):
        super().__init__()
        self.db = db
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.issue_btn = QPushButton("Issue book...", objectName="primary")
        self.return_btn = QPushButton("Return selected")
        self.return_btn.setEnabled(False)
        top.addWidget(self.issue_btn)
        top.addWidget(self.return_btn)
        top.addStretch(1)
        top.addWidget(QLabel("Show:"))
        self.status_group = QButtonGroup(self)
        for i, s in enumerate(STATUSES):
            rb = QRadioButton(s)
            self.status_group.addButton(rb, i)
            top.addWidget(rb)
        self.status_group.button(0).setChecked(True)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        self.info_label = QLabel(objectName="muted")
        layout.addLayout(top)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.info_label)

        self.issue_btn.clicked.connect(self.on_issue)
        self.return_btn.clicked.connect(self.on_return)
        self.status_group.idClicked.connect(lambda _id: self.refresh())
        self.table.itemSelectionChanged.connect(self.on_selection)
        self.table.cellDoubleClicked.connect(lambda _r, _c: self.on_return())
        self.refresh()

    def current_status(self) -> str:
        return STATUSES[self.status_group.checkedId()]

    def refresh(self) -> None:
        today = date.today()
        loans = self.db.loans(self.current_status(), today)
        self.table.setRowCount(len(loans))
        overdue_colour = QColor("#b42318")
        for r, x in enumerate(loans):
            fine = x.fine_paid if x.returned else x.fine(today)
            values = [x.loan_id, x.title, f"{x.member_id} · {x.member_name}", x.issued, x.due,
                      x.returned or "—", x.days_late(today), fine]
            for c, v in enumerate(values):
                item = QTableWidgetItem(str(v))
                item.setData(Qt.ItemDataRole.UserRole, x.loan_id)
                if c in (0, 6, 7):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if x.is_overdue(today):
                    item.setForeground(overdue_colour)          # overdue loans show in red
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.info_label.setText(f"{len(loans)} loan(s). Double-click an active loan to return it.")
        self.on_selection()

    def _selected_loan_id(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        return self.table.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole) if rows else None

    def on_selection(self) -> None:
        loan_id = self._selected_loan_id()
        loan = self.db.get_loan(loan_id) if loan_id else None
        self.return_btn.setEnabled(bool(loan and loan.is_active))

    def on_issue(self) -> None:
        dialog = IssueDialog(self.db, self)
        if dialog.book_combo.count() == 0 or dialog.member_combo.count() == 0:
            QMessageBox.information(self, "Nothing to issue", "You need at least one available book and one member.")
            return
        if not dialog.exec():                      # 0 = Cancel, 1 = Issue
            return
        isbn, member_id, due = dialog.values()
        try:
            self.db.issue(isbn, member_id, due)
        except (LibraryError, ValidationError) as err:
            QMessageBox.warning(self, "Cannot issue this book", str(err))
            return
        self.window().statusBar().showMessage(f"Issued to {member_id}, due {due.isoformat()}", 5000)
        self.refresh()
        self.data_changed.emit()

    def on_return(self) -> None:
        loan_id = self._selected_loan_id()
        loan = self.db.get_loan(loan_id) if loan_id else None
        if loan is None or not loan.is_active:
            return
        fine = loan.fine(date.today())
        msg = f"Return \"{loan.title}\" from {loan.member_name}?"
        if fine:
            msg += f"\n\nIt is {loan.days_late(date.today())} day(s) late. Fine to collect: Nu. {fine}."
        answer = QMessageBox.question(self, "Return book", msg,
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.Yes)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.return_book(loan_id)
        except LibraryError as err:
            QMessageBox.warning(self, "Cannot return", str(err))
            return
        self.window().statusBar().showMessage(f"Returned \"{loan.title}\"" + (f", fine Nu. {fine}" if fine else ""), 5000)
        self.refresh()
        self.data_changed.emit()
