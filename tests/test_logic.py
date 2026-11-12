"""Unit tests for the logic and data layers (no GUI needed): python -m unittest -v"""
import unittest
from datetime import date, timedelta

from lms.database import LibraryDB, LibraryError
from lms.models import (Book, Member, ValidationError, isbn13_valid, fine_for,
                        validate_book, validate_member, validate_due_date)

TODAY = date(2026, 11, 13)


def book(**kw):
    d = dict(isbn="9780134685991", title="Effective Java", author="Joshua Bloch",
             genre="Technology", year=2018, copies=1)
    d.update(kw)
    return Book(**d)


def member(**kw):
    d = dict(member_id="M010", name="Dorji Wangdi", email="dorji@example.edu.bt",
             phone="17112233", joined="2025-01-01")
    d.update(kw)
    return Member(**d)


class TestRules(unittest.TestCase):
    def test_isbn_check_digit(self):
        self.assertTrue(isbn13_valid("9780134685991"))
        self.assertTrue(isbn13_valid("978-0-13-468599-1"))
        self.assertFalse(isbn13_valid("9780134685992"))     # wrong check digit
        self.assertFalse(isbn13_valid("12345"))

    def test_fine(self):
        self.assertEqual(fine_for(0), 0)
        self.assertEqual(fine_for(6), 30)
        self.assertEqual(fine_for(-3), 0)

    def test_bad_book_reports_every_field(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_book(book(isbn="111", title="", year=3000, copies=0), this_year=2026)
        self.assertEqual({f for f, _ in ctx.exception.errors}, {"isbn", "title", "year", "copies"})

    def test_bad_member(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_member(member(member_id="7", phone="12345678", email="x@"), today=TODAY)
        self.assertEqual({f for f, _ in ctx.exception.errors}, {"member_id", "phone", "email"})

    def test_due_date_rules(self):
        validate_due_date(TODAY + timedelta(days=14), TODAY)
        with self.assertRaises(ValidationError):
            validate_due_date(TODAY, TODAY)
        with self.assertRaises(ValidationError):
            validate_due_date(TODAY + timedelta(days=90), TODAY)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = LibraryDB(":memory:")
        self.db.add_book(book(copies=1))
        self.db.add_member(member())
        self.db.add_member(member(member_id="M011", phone="77112233"))

    def tearDown(self):
        self.db.close()

    def test_duplicate_isbn_rejected(self):
        with self.assertRaises(ValidationError):
            self.db.add_book(book())

    def test_issue_and_return_with_fine(self):
        loan_id = self.db.issue("9780134685991", "M010", TODAY + timedelta(days=14), today=TODAY)
        fine = self.db.return_book(loan_id, today=TODAY + timedelta(days=20))   # 6 days late
        self.assertEqual(fine, 30)
        self.assertEqual(self.db.get_loan(loan_id).fine_paid, 30)

    def test_no_copies_left(self):
        self.db.issue("9780134685991", "M010", TODAY + timedelta(days=14), today=TODAY)
        with self.assertRaises(LibraryError):
            self.db.issue("9780134685991", "M011", TODAY + timedelta(days=14), today=TODAY)

    def test_member_loan_limit(self):
        for i, isbn in enumerate(["9781593279288", "9780262033848", "9780061120084", "9780141439518"]):
            self.db.add_book(book(isbn=isbn, title=f"Book {i}"))
        for isbn in ["9781593279288", "9780262033848", "9780061120084"]:
            self.db.issue(isbn, "M010", TODAY + timedelta(days=7), today=TODAY)
        with self.assertRaises(LibraryError):
            self.db.issue("9780141439518", "M010", TODAY + timedelta(days=7), today=TODAY)

    def test_cannot_delete_book_on_loan(self):
        self.db.issue("9780134685991", "M010", TODAY + timedelta(days=14), today=TODAY)
        with self.assertRaises(LibraryError):
            self.db.delete_book("9780134685991")

    def test_overdue_filter_and_stats(self):
        self.db.issue("9780134685991", "M010", TODAY + timedelta(days=3), today=TODAY)
        later = TODAY + timedelta(days=10)                                       # 7 days overdue
        self.assertEqual(len(self.db.loans("Overdue", later)), 1)
        self.assertEqual(self.db.stats(later)["fines_due"], 35)

    def test_search_and_available_filter(self):
        self.assertEqual(len(self.db.books("java")), 1)
        self.db.issue("9780134685991", "M010", TODAY + timedelta(days=14), today=TODAY)
        self.assertEqual(len(self.db.books(available_only=True)), 0)

    def test_data_persists_in_file(self):
        import tempfile, os
        path = os.path.join(tempfile.mkdtemp(), "lib.db")
        db = LibraryDB(path)
        db.add_book(book())
        db.close()
        again = LibraryDB(path)
        self.assertIsNotNone(again.get_book("9780134685991"))
        again.close()


if __name__ == "__main__":
    unittest.main()
