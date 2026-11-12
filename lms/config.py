"""App-wide settings. Name and roll number appear in the window title, status bar and About box."""
import sys
from pathlib import Path

STUDENT_NAME = "Tshering Gyelpo"
ROLL_NO = "08230223"

APP_NAME = "Library Issue & Return System"
WINDOW_TITLE = f"{APP_NAME} - {STUDENT_NAME} ({ROLL_NO})"

# Paths are built relative to the project (or to the .exe when packaged) - never absolute.
IS_FROZEN = getattr(sys, "frozen", False)
if IS_FROZEN:
    PROJECT_DIR = Path(sys.executable).resolve().parent
else:
    PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_FILE = PROJECT_DIR / "data" / "library.db"
UI_DIR = Path(__file__).resolve().parent / "ui"

# Library rules
GENRES = ["Fiction", "Science", "Technology", "History", "Dzongkha", "Reference", "Children"]
LOAN_DAYS = 14          # default loan period
MAX_LOAN_DAYS = 60      # longest loan allowed
MAX_ACTIVE_LOANS = 3    # books a member may hold at once
FINE_PER_DAY = 5        # Nu. per day late
