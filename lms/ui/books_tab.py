"""Books tab: a form to add/edit books and a filterable catalogue table."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QGroupBox, QLineEdit, QComboBox,
    QSpinBox, QPushButton, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QLabel,
)

from lms import config
from lms.database import LibraryDB, LibraryError
from lms.models import Book, ValidationError, clean_isbn
from lms.ui.helpers import show_validation, clear_invalid, scrollable

COLUMNS = ["ISBN", "Title", "Author", "Genre", "Year", "Copies", "Available"]


class BooksTab(QWidget):
    data_changed = pyqtSignal()          # custom signal: tells the other tabs to refresh

    def __init__(self, db: LibraryDB):
        super().__init__()
        self.db = db
        self.editing_isbn: str | None = None

        layout = QHBoxLayout(self)
        layout.addWidget(scrollable(self._build_form()), 0)
        layout.addLayout(self._build_catalogue(), 1)      # stretch 1: the table takes extra space
        self.refresh()

    # ------------------------------------------------------------- build
    def _build_form(self) -> QWidget:
        page = QWidget(objectName="page")
        outer = QVBoxLayout(page)
        box = QGroupBox("Book details")
        form = QFormLayout(box)
        self.isbn_edit = QLineEdit(placeholderText="13 digits, e.g. 9780134685991")
        self.title_edit = QLineEdit(placeholderText="Book title")
        self.author_edit = QLineEdit(placeholderText="Author name")
        self.genre_combo = QComboBox()
        self.genre_combo.addItems(config.GENRES)
        self.year_spin = QSpinBox(minimum=1450, maximum=2100, value=2020)
        self.copies_spin = QSpinBox(minimum=1, maximum=50, value=1)
        form.addRow("ISBN", self.isbn_edit)
        form.addRow("Title", self.title_edit)
        form.addRow("Author", self.author_edit)
        form.addRow("Genre", self.genre_combo)
        form.addRow("Year", self.year_spin)
        form.addRow("Copies", self.copies_spin)
        self.fields = {"isbn": self.isbn_edit, "title": self.title_edit, "author": self.author_edit,
                       "genre": self.genre_combo, "year": self.year_spin, "copies": self.copies_spin}

        buttons = QHBoxLayout()
        self.add_btn = QPushButton("Add book", objectName="primary")
        self.save_btn = QPushButton("Save changes")
        self.delete_btn = QPushButton("Delete", objectName="danger")
        self.clear_btn = QPushButton("Clear")
        for b in (self.add_btn, self.save_btn, self.delete_btn, self.clear_btn):
            buttons.addWidget(b)
        self.add_btn.clicked.connect(self.on_add)
        self.save_btn.clicked.connect(self.on_save)
        self.delete_btn.clicked.connect(self.on_delete)
        self.clear_btn.clicked.connect(self.clear_form)

        outer.addWidget(box)
        outer.addLayout(buttons)
        outer.addStretch(1)
        self._set_editing(None)
        return page

    def _build_catalogue(self) -> QVBoxLayout:
        col = QVBoxLayout()
        filters = QHBoxLayout()
        self.search_edit = QLineEdit(placeholderText="Search title, author or ISBN...", clearButtonEnabled=True)
        self.genre_filter = QComboBox()
        self.genre_filter.addItems(["All", *config.GENRES])
        self.available_check = QCheckBox("Available only")
        filters.addWidget(self.search_edit, 1)
        filters.addWidget(self.genre_filter)
        filters.addWidget(self.available_check)
        self.search_edit.textChanged.connect(self.refresh)
        self.genre_filter.currentIndexChanged.connect(self.refresh)
        self.available_check.toggled.connect(self.refresh)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.on_row_selected)

        self.count_label = QLabel(objectName="muted")
        col.addLayout(filters)
        col.addWidget(self.table, 1)
        col.addWidget(self.count_label)
        return col

    # ----------------------------------------------------------- helpers
    def _form_to_book(self) -> Book:
        return Book(isbn=clean_isbn(self.isbn_edit.text()), title=self.title_edit.text(),
                    author=" ".join(self.author_edit.text().split()), genre=self.genre_combo.currentText(),
                    year=self.year_spin.value(), copies=self.copies_spin.value())

    def _set_editing(self, isbn: str | None) -> None:
        self.editing_isbn = isbn
        self.isbn_edit.setReadOnly(isbn is not None)     # the ISBN is the key, so it can't change
        self.save_btn.setEnabled(isbn is not None)
        self.delete_btn.setEnabled(isbn is not None)
        self.add_btn.setEnabled(isbn is None)

    def _status(self, text: str) -> None:
        self.window().statusBar().showMessage(text, 5000)

    # ------------------------------------------------------------- slots
    def refresh(self) -> None:
        rows = self.db.books(self.search_edit.text(), self.genre_filter.currentText(),
                             self.available_check.isChecked())
        self.table.setSortingEnabled(False)               # avoid re-sorting while filling
        self.table.setRowCount(len(rows))
        for r, (b, available) in enumerate(rows):
            for c, v in enumerate([b.isbn, b.title, b.author, b.genre, b.year, b.copies, available]):
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, v)     # numbers sort as numbers
                if c >= 4:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, item)
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.count_label.setText(f"{len(rows)} title(s) shown")

    def on_row_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        book = self.db.get_book(self.table.item(rows[0].row(), 0).text())
        if book:
            clear_invalid(self.fields)
            self.isbn_edit.setText(book.isbn)
            self.title_edit.setText(book.title)
            self.author_edit.setText(book.author)
            self.genre_combo.setCurrentText(book.genre)
            self.year_spin.setValue(book.year)
            self.copies_spin.setValue(book.copies)
            self._set_editing(book.isbn)

    def on_add(self) -> None:
        try:
            book = self._form_to_book()
            self.db.add_book(book)
        except ValidationError as err:
            show_validation(self, err, self.fields)
            return
        self._status(f"Added \"{book.title}\"")
        self.clear_form()
        self.refresh()
        self.data_changed.emit()

    def on_save(self) -> None:
        try:
            book = self._form_to_book()
            self.db.update_book(book)
        except ValidationError as err:
            show_validation(self, err, self.fields)
            return
        except LibraryError as err:
            QMessageBox.warning(self, "Cannot save", str(err))
            return
        self._status(f"Saved \"{book.title}\"")
        self.clear_form()
        self.refresh()
        self.data_changed.emit()

    def on_delete(self) -> None:
        book = self.db.get_book(self.editing_isbn) if self.editing_isbn else None
        if book is None:
            return
        answer = QMessageBox.question(
            self, "Delete book", f"Delete \"{book.title}\" and its loan history?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_book(book.isbn)
        except LibraryError as err:
            QMessageBox.warning(self, "Cannot delete", str(err))
            return
        self._status(f"Deleted \"{book.title}\"")
        self.clear_form()
        self.refresh()
        self.data_changed.emit()

    def clear_form(self) -> None:
        self.table.clearSelection()
        for w in (self.isbn_edit, self.title_edit, self.author_edit):
            w.clear()
        self.genre_combo.setCurrentIndex(0)
        self.year_spin.setValue(2020)
        self.copies_spin.setValue(1)
        clear_invalid(self.fields)
        self._set_editing(None)
        self.isbn_edit.setFocus()
