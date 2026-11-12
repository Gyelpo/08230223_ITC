"""Members tab: a searchable member list and a form to add/edit members."""
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox, QLineEdit, QDateEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox, QLabel,
)

from lms.database import LibraryDB, LibraryError
from lms.models import Member, ValidationError
from lms.ui.helpers import show_validation, clear_invalid, scrollable


class MembersTab(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, db: LibraryDB):
        super().__init__()
        self.db = db
        self.editing_id: str | None = None

        layout = QHBoxLayout(self)
        layout.addLayout(self._build_list(), 1)
        layout.addWidget(scrollable(self._build_form()), 1)
        self.refresh()

    def _build_list(self) -> QVBoxLayout:
        col = QVBoxLayout()
        self.search_edit = QLineEdit(placeholderText="Search members by name or ID...", clearButtonEnabled=True)
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.count_label = QLabel(objectName="muted")
        col.addWidget(self.search_edit)
        col.addWidget(self.list, 1)
        col.addWidget(self.count_label)
        self.search_edit.textChanged.connect(self.refresh)
        self.list.currentItemChanged.connect(self.on_member_selected)
        return col

    def _build_form(self) -> QWidget:
        page = QWidget(objectName="page")
        outer = QVBoxLayout(page)
        box = QGroupBox("Member details")
        grid = QGridLayout(box)                       # label column | field column
        self.id_edit = QLineEdit(placeholderText="M + 3 digits, e.g. M005", maxLength=4)
        self.name_edit = QLineEdit(placeholderText="Full name")
        self.email_edit = QLineEdit(placeholderText="name@rub.edu.bt")
        self.phone_edit = QLineEdit(placeholderText="17xxxxxx or 77xxxxxx", maxLength=8)
        self.joined_edit = QDateEdit(calendarPopup=True, displayFormat="yyyy-MM-dd")
        self.joined_edit.setDate(QDate.currentDate())
        rows = [("Member ID", self.id_edit), ("Name", self.name_edit), ("Email", self.email_edit),
                ("Phone", self.phone_edit), ("Joined", self.joined_edit)]
        for r, (label, w) in enumerate(rows):
            grid.addWidget(QLabel(label), r, 0)
            grid.addWidget(w, r, 1)
        grid.setColumnStretch(1, 1)
        self.fields = {"member_id": self.id_edit, "name": self.name_edit, "email": self.email_edit,
                       "phone": self.phone_edit, "joined": self.joined_edit}

        self.loans_label = QLabel(objectName="muted")
        buttons = QHBoxLayout()
        self.add_btn = QPushButton("Add member", objectName="primary")
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
        outer.addWidget(self.loans_label)
        outer.addLayout(buttons)
        outer.addStretch(1)
        self._set_editing(None)
        return page

    # ----------------------------------------------------------- helpers
    def _form_to_member(self) -> Member:
        return Member(member_id=self.id_edit.text().strip().upper(),
                      name=" ".join(self.name_edit.text().split()),
                      email=self.email_edit.text().strip(), phone=self.phone_edit.text().strip(),
                      joined=self.joined_edit.date().toString("yyyy-MM-dd"))

    def _set_editing(self, member_id: str | None) -> None:
        self.editing_id = member_id
        self.id_edit.setReadOnly(member_id is not None)
        self.save_btn.setEnabled(member_id is not None)
        self.delete_btn.setEnabled(member_id is not None)
        self.add_btn.setEnabled(member_id is None)
        if member_id:
            self.loans_label.setText(f"Books on loan now: {self.db.active_loans_of(member_id)}")
        else:
            self.loans_label.setText("")

    def _status(self, text: str) -> None:
        self.window().statusBar().showMessage(text, 5000)

    # ------------------------------------------------------------- slots
    def refresh(self) -> None:
        self.list.blockSignals(True)                  # don't fire selection events while rebuilding
        self.list.clear()
        members = self.db.members(self.search_edit.text())
        for m in members:
            item = QListWidgetItem(f"{m.member_id}  ·  {m.name}")
            item.setData(Qt.ItemDataRole.UserRole, m.member_id)
            self.list.addItem(item)
        self.list.blockSignals(False)
        self.count_label.setText(f"{len(members)} member(s)")

    def on_member_selected(self, current: QListWidgetItem, _previous) -> None:
        if current is None:
            return
        m = self.db.get_member(current.data(Qt.ItemDataRole.UserRole))
        if m:
            clear_invalid(self.fields)
            self.id_edit.setText(m.member_id)
            self.name_edit.setText(m.name)
            self.email_edit.setText(m.email)
            self.phone_edit.setText(m.phone)
            self.joined_edit.setDate(QDate.fromString(m.joined, "yyyy-MM-dd"))
            self._set_editing(m.member_id)

    def on_add(self) -> None:
        try:
            m = self._form_to_member()
            self.db.add_member(m)
        except ValidationError as err:
            show_validation(self, err, self.fields)
            return
        self._status(f"Added member {m.name} ({m.member_id})")
        self.clear_form()
        self.refresh()
        self.data_changed.emit()

    def on_save(self) -> None:
        try:
            m = self._form_to_member()
            self.db.update_member(m)
        except ValidationError as err:
            show_validation(self, err, self.fields)
            return
        except LibraryError as err:
            QMessageBox.warning(self, "Cannot save", str(err))
            return
        self._status(f"Saved {m.name}")
        self.clear_form()
        self.refresh()
        self.data_changed.emit()

    def on_delete(self) -> None:
        m = self.db.get_member(self.editing_id) if self.editing_id else None
        if m is None:
            return
        answer = QMessageBox.question(
            self, "Delete member", f"Delete {m.name} ({m.member_id}) and their loan history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.delete_member(m.member_id)
        except LibraryError as err:
            QMessageBox.warning(self, "Cannot delete", str(err))
            return
        self._status(f"Deleted {m.name}")
        self.clear_form()
        self.refresh()
        self.data_changed.emit()

    def clear_form(self) -> None:
        self.list.clearSelection()
        self.list.setCurrentItem(None)
        for w in (self.id_edit, self.name_edit, self.email_edit, self.phone_edit):
            w.clear()
        self.joined_edit.setDate(QDate.currentDate())
        clear_invalid(self.fields)
        self._set_editing(None)
        self.id_edit.setFocus()
