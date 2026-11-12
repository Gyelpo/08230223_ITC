# Library Issue & Return System (Unit V – PyQt6)

**Tshering Gyelpo · 08230223 · PRG304**

A desktop app for a small library: manage books and members, issue and return books,
see overdue loans and fines (Nu. 5 per day late), and view library statistics.
Data is stored in an SQLite database, `data/library.db`, created automatically on first run
with sample books, members and loans.

## Requirements
- Python **3.10 or newer**
- Windows, macOS or Linux

## Install and run
```bash
# 1. create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux

# 2. install the pinned packages
pip install -r requirements.txt

# 3. run the app
python main.py
```

To start again with fresh sample data, close the app and delete `data/library.db`.

## Run the tests
```bash
python -m unittest -v           # 13 tests of the logic and data layers, no GUI needed
```

## Part A hello-world programs
```bash
python partA/hello_pyqt.py
python partA/hello_kivy.py
python partA/hello_tkinter.py
```

## Build a stand-alone executable (optional)
```bash
pyinstaller --noconfirm --onefile --windowed --name LibrarySystem --add-data "lms/ui/style.qss;lms/ui" main.py
```
(On macOS/Linux use `:` instead of `;` inside `--add-data`.) The database is created in a `data/` folder next to the executable.

## Features
| Tab | What it does |
|---|---|
| Books | Add, edit and delete books (ISBN-13 checked); search; filter by genre; "available only" |
| Members | Add, edit and delete members (ID `M###`, Bhutan phone `17/77xxxxxx`); search list |
| Loans | Issue a book through a dialog; return a book (fine shown); filter Active / Overdue / Returned / All; overdue rows in red |
| Summary | Six stat cards, a bar showing how much stock is on loan, and the most borrowed books |

Menu: **File → Export loans to CSV** (Ctrl+E), **Loans → Issue a book** (Ctrl+I), **Help → About**.

## Library rules (in `lms/config.py`)
- A loan lasts 14 days by default, at most 60 days
- A member may hold at most 3 books at once, and only one copy of the same book
- Late returns are fined Nu. 5 per day
- A book or member with books still on loan cannot be deleted

## Project layout
```
main.py                   entry point: QApplication, stylesheet, database, event loop
lms/config.py             name/roll no, paths, library rules
lms/models.py             logic layer: Book, Member, Loan, validation, ISBN check, fines   (no PyQt)
lms/database.py           data layer: LibraryDB (SQLite), issue/return rules, stats, CSV (no PyQt)
lms/ui/main_window.py     QMainWindow: menu bar, tabs, status bar, connects tab signals
lms/ui/books_tab.py       Books tab
lms/ui/members_tab.py     Members tab
lms/ui/loans_tab.py       Loans tab
lms/ui/issue_dialog.py    custom QDialog for issuing a book
lms/ui/summary_tab.py     Summary tab
lms/ui/helpers.py         red-highlight validation helper, scroll-area helper
lms/ui/style.qss          Qt stylesheet (theme)
tests/test_logic.py       unit tests
partA/                    hello-world programs for Part A
```
