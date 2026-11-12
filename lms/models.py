"""Logic layer: records, validation rules and fine calculation.

No PyQt imports here, so everything can be unit-tested without a display.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from lms.config import GENRES, FINE_PER_DAY, MAX_LOAN_DAYS

MEMBER_ID_RE = re.compile(r"^M\d{3}$")                    # M001 ... M999
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,59}$")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
PHONE_RE = re.compile(r"^(17|77)\d{6}$")                  # Bhutan mobile: 17xxxxxx / 77xxxxxx


class ValidationError(ValueError):
    """Carries a list of (field, message) pairs so the UI can highlight each bad field."""

    def __init__(self, errors: list[tuple[str, str]]):
        self.errors = errors
        super().__init__("; ".join(msg for _, msg in errors))


# ----------------------------------------------------------------- records
@dataclass
class Book:
    isbn: str
    title: str
    author: str
    genre: str
    year: int
    copies: int


@dataclass
class Member:
    member_id: str
    name: str
    email: str
    phone: str
    joined: str            # ISO date "YYYY-MM-DD"


@dataclass
class Loan:
    loan_id: int
    isbn: str
    member_id: str
    issued: str            # ISO dates
    due: str
    returned: str | None = None
    fine_paid: int = 0
    title: str = ""        # filled in by the database join, for display
    member_name: str = ""

    @property
    def is_active(self) -> bool:
        return self.returned is None

    def days_late(self, today: date) -> int:
        end = date.fromisoformat(self.returned) if self.returned else today
        return max(0, (end - date.fromisoformat(self.due)).days)

    def is_overdue(self, today: date) -> bool:
        return self.is_active and self.days_late(today) > 0

    def fine(self, today: date) -> int:
        return fine_for(self.days_late(today))


# ----------------------------------------------------------------- rules
def fine_for(days_late: int) -> int:
    """Nu. FINE_PER_DAY for each day late; never negative."""
    return max(0, days_late) * FINE_PER_DAY


def isbn13_valid(isbn: str) -> bool:
    """ISBN-13 check digit: weights 1,3,1,3,... and the total must be a multiple of 10."""
    digits = isbn.replace("-", "")
    if not re.fullmatch(r"\d{13}", digits):
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    return total % 10 == 0


def clean_isbn(isbn: str) -> str:
    return isbn.replace("-", "").replace(" ", "").strip()


def validate_book(book: Book, this_year: int | None = None) -> None:
    this_year = this_year or date.today().year
    errors: list[tuple[str, str]] = []
    if not isbn13_valid(book.isbn):
        errors.append(("isbn", "ISBN must be 13 digits with a correct check digit, e.g. 9780134685991."))
    if not 1 <= len(book.title.strip()) <= 120:
        errors.append(("title", "Title is required (up to 120 characters)."))
    if not NAME_RE.match(book.author.strip()):
        errors.append(("author", "Author must be 2-60 letters (spaces, . ' - allowed)."))
    if book.genre not in GENRES:
        errors.append(("genre", "Choose a genre from the list."))
    if not 1450 <= book.year <= this_year:
        errors.append(("year", f"Year must be between 1450 and {this_year}."))
    if not 1 <= book.copies <= 50:
        errors.append(("copies", "Copies must be between 1 and 50."))
    if errors:
        raise ValidationError(errors)


def validate_member(member: Member, today: date | None = None) -> None:
    today = today or date.today()
    errors: list[tuple[str, str]] = []
    if not MEMBER_ID_RE.match(member.member_id):
        errors.append(("member_id", "Member ID must be M followed by 3 digits, e.g. M007."))
    if not NAME_RE.match(member.name.strip()):
        errors.append(("name", "Name must be 2-60 letters (spaces, . ' - allowed)."))
    if not EMAIL_RE.match(member.email):
        errors.append(("email", "Email is not valid, e.g. name@rub.edu.bt."))
    if not PHONE_RE.match(member.phone):
        errors.append(("phone", "Phone must be 8 digits starting with 17 or 77."))
    try:
        if date.fromisoformat(member.joined) > today:
            errors.append(("joined", "Joined date cannot be in the future."))
    except ValueError:
        errors.append(("joined", "Joined date is not a valid date."))
    if errors:
        raise ValidationError(errors)


def validate_due_date(due: date, today: date) -> None:
    if due <= today:
        raise ValidationError([("due", "Due date must be after today.")])
    if due > today + timedelta(days=MAX_LOAN_DAYS):
        raise ValidationError([("due", f"A loan can last at most {MAX_LOAN_DAYS} days.")])
