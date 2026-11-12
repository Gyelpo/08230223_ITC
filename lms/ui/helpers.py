"""Small UI helpers shared by the tabs."""
from PyQt6.QtWidgets import QWidget, QMessageBox, QScrollArea, QFrame
from PyQt6.QtCore import Qt

from lms.models import ValidationError


def set_invalid(widget: QWidget, invalid: bool) -> None:
    """Turn the red-border rule *[invalid="true"] in style.qss on or off for one widget."""
    widget.setProperty("invalid", invalid)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def show_validation(parent: QWidget, err: ValidationError, fields: dict[str, QWidget]) -> None:
    """Highlight every field that failed and list all the messages in one dialog."""
    for w in fields.values():
        set_invalid(w, False)
    for field, _ in err.errors:
        if field in fields:
            set_invalid(fields[field], True)
    QMessageBox.warning(parent, "Please check the form", "\n".join(f"• {m}" for _, m in err.errors))


def clear_invalid(fields: dict[str, QWidget]) -> None:
    for w in fields.values():
        set_invalid(w, False)


def scrollable(inner: QWidget) -> QScrollArea:
    """Wrap a form so a small window shows a scroll bar instead of squashing the fields."""
    area = QScrollArea()
    area.setWidget(inner)
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setMinimumWidth(360)
    return area
