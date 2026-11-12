"""Summary tab: library statistics, how much of the stock is on loan, and most-borrowed books."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QFrame, QLabel, QProgressBar, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)

from lms.database import LibraryDB

CARDS = [("titles", "Book titles"), ("copies", "Copies in stock"), ("members", "Members"),
         ("on_loan", "On loan now"), ("overdue", "Overdue"), ("fines_due", "Fines due (Nu.)")]


class SummaryTab(QWidget):
    def __init__(self, db: LibraryDB):
        super().__init__()
        self.db = db
        layout = QVBoxLayout(self)

        grid = QGridLayout()                       # 2 rows x 3 cards
        self.values: dict[str, QLabel] = {}
        for i, (key, caption) in enumerate(CARDS):
            card = QFrame(objectName="card")
            v = QVBoxLayout(card)
            value = QLabel("0", objectName="cardValue")
            v.addWidget(value)
            v.addWidget(QLabel(caption, objectName="cardCaption"))
            self.values[key] = value
            grid.addWidget(card, i // 3, i % 3)

        self.usage_bar = QProgressBar(maximum=100)
        self.fines_label = QLabel(objectName="muted")

        top_box = QGroupBox("Most borrowed books")
        self.top_table = QTableWidget(0, 2)
        self.top_table.setHorizontalHeaderLabels(["Title", "Times borrowed"])
        self.top_table.verticalHeader().setVisible(False)
        self.top_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.top_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        QVBoxLayout(top_box).addWidget(self.top_table)

        layout.addLayout(grid)
        layout.addWidget(self.usage_bar)
        layout.addWidget(self.fines_label)
        layout.addWidget(top_box, 1)
        self.refresh()

    def refresh(self) -> None:
        s = self.db.stats()
        for key, label in self.values.items():
            label.setText(str(s[key]))
        self.values["overdue"].setProperty("alert", s["overdue"] > 0)      # red when anything is overdue
        self.values["overdue"].style().unpolish(self.values["overdue"])
        self.values["overdue"].style().polish(self.values["overdue"])
        pct = round(100 * s["on_loan"] / s["copies"]) if s["copies"] else 0
        self.usage_bar.setValue(pct)
        self.usage_bar.setFormat(f"{s['on_loan']} of {s['copies']} copies on loan (%p%)")
        self.fines_label.setText(f"Fines already collected: Nu. {s['fines_paid']}")

        top = self.db.most_borrowed()
        self.top_table.setRowCount(len(top))
        for r, (title, n) in enumerate(top):
            self.top_table.setItem(r, 0, QTableWidgetItem(title))
            self.top_table.setItem(r, 1, QTableWidgetItem(str(n)))
