"""Data layer: all SQLite access lives here. No PyQt imports."""
from __future__ import annotations

import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from lms.config import MAX_ACTIVE_LOANS
from lms.models import (Book, Member, Loan, ValidationError, validate_book,
                        validate_member, validate_due_date, fine_for)

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    isbn    TEXT PRIMARY KEY,
    title   TEXT NOT NULL,
    author  TEXT NOT NULL,
    genre   TEXT NOT NULL,
    year    INTEGER NOT NULL,
    copies  INTEGER NOT NULL CHECK (copies > 0)
);
CREATE TABLE IF NOT EXISTS members (
    member_id TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    email     TEXT NOT NULL,
    phone     TEXT NOT NULL,
    joined    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS loans (
    loan_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn      TEXT NOT NULL REFERENCES books(isbn),
    member_id TEXT NOT NULL REFERENCES members(member_id),
    issued    TEXT NOT NULL,
    due       TEXT NOT NULL,
    returned  TEXT,
    fine_paid INTEGER NOT NULL DEFAULT 0
);
"""


class LibraryError(Exception):
    """A rule of the library was broken (e.g. no copies left). Message is safe to show."""


class LibraryDB:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------ books
    def add_book(self, book: Book) -> None:
        validate_book(book)
        try:
            with self.conn:                       # commits, or rolls back on error
                self.conn.execute("INSERT INTO books VALUES (?,?,?,?,?,?)",
                                  (book.isbn, book.title.strip(), book.author.strip(),
                                   book.genre, book.year, book.copies))
        except sqlite3.IntegrityError:
            raise ValidationError([("isbn", f"A book with ISBN {book.isbn} already exists.")])

    def update_book(self, book: Book) -> None:
        validate_book(book)
        on_loan = self.on_loan(book.isbn)
        if book.copies < on_loan:
            raise ValidationError([("copies", f"{on_loan} copies are on loan; copies cannot be lower.")])
        with self.conn:
            cur = self.conn.execute(
                "UPDATE books SET title=?, author=?, genre=?, year=?, copies=? WHERE isbn=?",
                (book.title.strip(), book.author.strip(), book.genre, book.year, book.copies, book.isbn))
        if cur.rowcount == 0:
            raise LibraryError("That book no longer exists.")

    def delete_book(self, isbn: str) -> None:
        if self.on_loan(isbn):
            raise LibraryError("This book has copies on loan. Return them before deleting.")
        with self.conn:
            self.conn.execute("DELETE FROM loans WHERE isbn=?", (isbn,))   # history of a removed book
            self.conn.execute("DELETE FROM books WHERE isbn=?", (isbn,))

    def get_book(self, isbn: str) -> Book | None:
        r = self.conn.execute("SELECT * FROM books WHERE isbn=?", (isbn,)).fetchone()
        return Book(**dict(r)) if r else None

    def on_loan(self, isbn: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM loans WHERE isbn=? AND returned IS NULL", (isbn,)).fetchone()[0]

    def books(self, text: str = "", genre: str = "All", available_only: bool = False) -> list[tuple[Book, int]]:
        """Books matching the filters, each with its number of copies available now."""
        sql = """SELECT b.*, b.copies - COUNT(l.loan_id) AS available
                 FROM books b LEFT JOIN loans l ON l.isbn = b.isbn AND l.returned IS NULL
                 WHERE (b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?)"""
        like = f"%{text.strip()}%"
        args: list = [like, like, like]
        if genre != "All":
            sql += " AND b.genre = ?"
            args.append(genre)
        sql += " GROUP BY b.isbn"
        if available_only:
            sql += " HAVING available > 0"
        sql += " ORDER BY b.title"
        rows = self.conn.execute(sql, args).fetchall()
        return [(Book(*[r[k] for k in ("isbn", "title", "author", "genre", "year", "copies")]),
                 r["available"]) for r in rows]

    # ---------------------------------------------------------- members
    def add_member(self, m: Member) -> None:
        validate_member(m)
        try:
            with self.conn:
                self.conn.execute("INSERT INTO members VALUES (?,?,?,?,?)",
                                  (m.member_id, m.name.strip(), m.email, m.phone, m.joined))
        except sqlite3.IntegrityError:
            raise ValidationError([("member_id", f"Member {m.member_id} already exists.")])

    def update_member(self, m: Member) -> None:
        validate_member(m)
        with self.conn:
            cur = self.conn.execute("UPDATE members SET name=?, email=?, phone=?, joined=? WHERE member_id=?",
                                    (m.name.strip(), m.email, m.phone, m.joined, m.member_id))
        if cur.rowcount == 0:
            raise LibraryError("That member no longer exists.")

    def delete_member(self, member_id: str) -> None:
        if self.active_loans_of(member_id):
            raise LibraryError("This member still has books on loan.")
        with self.conn:
            self.conn.execute("DELETE FROM loans WHERE member_id=?", (member_id,))
            self.conn.execute("DELETE FROM members WHERE member_id=?", (member_id,))

    def get_member(self, member_id: str) -> Member | None:
        r = self.conn.execute("SELECT * FROM members WHERE member_id=?", (member_id,)).fetchone()
        return Member(**dict(r)) if r else None

    def members(self, text: str = "") -> list[Member]:
        like = f"%{text.strip()}%"
        rows = self.conn.execute("SELECT * FROM members WHERE name LIKE ? OR member_id LIKE ? ORDER BY member_id",
                                 (like, like)).fetchall()
        return [Member(**dict(r)) for r in rows]

    def active_loans_of(self, member_id: str) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM loans WHERE member_id=? AND returned IS NULL", (member_id,)).fetchone()[0]

    # ------------------------------------------------------------ loans
    def issue(self, isbn: str, member_id: str, due: date, today: date | None = None) -> int:
        """Lend one copy. Every library rule is checked here, not in the UI."""
        today = today or date.today()
        if self.get_book(isbn) is None or self.get_member(member_id) is None:
            raise LibraryError("Choose an existing book and member.")
        validate_due_date(due, today)
        available = self.get_book(isbn).copies - self.on_loan(isbn)
        if available <= 0:
            raise LibraryError("No copies of this book are available right now.")
        if self.active_loans_of(member_id) >= MAX_ACTIVE_LOANS:
            raise LibraryError(f"This member already has {MAX_ACTIVE_LOANS} books on loan.")
        already = self.conn.execute("SELECT 1 FROM loans WHERE isbn=? AND member_id=? AND returned IS NULL",
                                    (isbn, member_id)).fetchone()
        if already:
            raise LibraryError("This member already has a copy of this book.")
        with self.conn:
            cur = self.conn.execute("INSERT INTO loans (isbn, member_id, issued, due) VALUES (?,?,?,?)",
                                    (isbn, member_id, today.isoformat(), due.isoformat()))
        return cur.lastrowid

    def return_book(self, loan_id: int, today: date | None = None) -> int:
        """Mark a loan returned and record the fine. Returns the fine in Nu."""
        today = today or date.today()
        loan = self.get_loan(loan_id)
        if loan is None or not loan.is_active:
            raise LibraryError("That loan is not active.")
        fine = loan.fine(today)
        with self.conn:
            self.conn.execute("UPDATE loans SET returned=?, fine_paid=? WHERE loan_id=?",
                              (today.isoformat(), fine, loan_id))
        return fine

    def get_loan(self, loan_id: int) -> Loan | None:
        r = self.conn.execute(self._LOAN_SQL + " WHERE l.loan_id=?", (loan_id,)).fetchone()
        return Loan(**dict(r)) if r else None

    _LOAN_SQL = """SELECT l.*, b.title AS title, m.name AS member_name
                   FROM loans l JOIN books b ON b.isbn = l.isbn
                   JOIN members m ON m.member_id = l.member_id"""

    def loans(self, status: str = "All", today: date | None = None) -> list[Loan]:
        """status: All | Active | Overdue | Returned"""
        today = today or date.today()
        rows = self.conn.execute(self._LOAN_SQL + " ORDER BY l.loan_id DESC").fetchall()
        loans = [Loan(**dict(r)) for r in rows]
        if status == "Active":
            return [x for x in loans if x.is_active]
        if status == "Overdue":
            return [x for x in loans if x.is_overdue(today)]
        if status == "Returned":
            return [x for x in loans if not x.is_active]
        return loans

    # ------------------------------------------------------ statistics
    def stats(self, today: date | None = None) -> dict:
        today = today or date.today()
        q = lambda sql: self.conn.execute(sql).fetchone()[0] or 0
        active = self.loans("Active", today)
        return {
            "titles": q("SELECT COUNT(*) FROM books"),
            "copies": q("SELECT SUM(copies) FROM books"),
            "members": q("SELECT COUNT(*) FROM members"),
            "on_loan": len(active),
            "overdue": sum(1 for x in active if x.is_overdue(today)),
            "fines_due": sum(x.fine(today) for x in active),
            "fines_paid": q("SELECT SUM(fine_paid) FROM loans"),
        }

    def most_borrowed(self, limit: int = 5) -> list[tuple[str, int]]:
        rows = self.conn.execute("""SELECT b.title, COUNT(*) AS n FROM loans l JOIN books b ON b.isbn = l.isbn
                                    GROUP BY l.isbn ORDER BY n DESC, b.title LIMIT ?""", (limit,)).fetchall()
        return [(r["title"], r["n"]) for r in rows]

    def export_loans_csv(self, path: str, today: date | None = None) -> int:
        today = today or date.today()
        loans = self.loans("All", today)
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["loan_id", "isbn", "title", "member_id", "member", "issued", "due",
                            "returned", "days_late", "fine_nu"])
                for x in loans:
                    w.writerow([x.loan_id, x.isbn, x.title, x.member_id, x.member_name, x.issued, x.due,
                                x.returned or "", x.days_late(today),
                                x.fine_paid if x.returned else x.fine(today)])
        except OSError as exc:
            raise LibraryError(f"Could not write the CSV file: {exc.strerror}") from exc
        return len(loans)

    # ------------------------------------------------------ sample data
    def is_empty(self) -> bool:
        return self.conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0

    def seed_sample(self, today: date | None = None) -> None:
        """Fill an empty database with sample data so the app is not blank on first run."""
        today = today or date.today()
        books = [
            Book("9780134685991", "Effective Java", "Joshua Bloch", "Technology", 2018, 2),
            Book("9781593279288", "Python Crash Course", "Eric Matthes", "Technology", 2019, 3),
            Book("9780262033848", "Introduction to Algorithms", "Thomas Cormen", "Reference", 2009, 2),
            Book("9780061120084", "To Kill a Mockingbird", "Harper Lee", "Fiction", 1960, 2),
            Book("9780141439518", "Pride and Prejudice", "Jane Austen", "Fiction", 1813, 1),
            Book("9780553380163", "A Brief History of Time", "Stephen Hawking", "Science", 1998, 2),
            Book("9780307887443", "Ready Player One", "Ernest Cline", "Fiction", 2011, 1),
            Book("9780393354324", "Guns Germs and Steel", "Jared Diamond", "History", 2017, 1),
        ]
        members = [
            Member("M001", "Tashi Wangmo", "tashi.wangmo@example.edu.bt", "17123456", "2025-02-10"),
            Member("M002", "Kinley Dorji", "kinley.dorji@example.edu.bt", "77234567", "2025-03-01"),
            Member("M003", "Pema Lhamo", "pema.lhamo@example.edu.bt", "17345678", "2025-07-15"),
            Member("M004", "Sonam Tobgay", "sonam.tobgay@example.edu.bt", "77456789", "2026-01-20"),
        ]
        for b in books:
            self.add_book(b)
        for m in members:
            self.add_member(m)
        # loans: some returned, one overdue, some active
        with self.conn:
            ins = "INSERT INTO loans (isbn, member_id, issued, due, returned, fine_paid) VALUES (?,?,?,?,?,?)"
            d = lambda n: (today - timedelta(days=n)).isoformat()
            self.conn.executemany(ins, [
                ("9781593279288", "M001", d(40), d(26), d(28), 0),
                ("9780134685991", "M002", d(35), d(21), d(15), 30),
                ("9781593279288", "M003", d(20), d(6), None, 0),       # overdue by 6 days
                ("9780061120084", "M001", d(5), (today + timedelta(days=9)).isoformat(), None, 0),
                ("9780553380163", "M004", d(2), (today + timedelta(days=12)).isoformat(), None, 0),
            ])
