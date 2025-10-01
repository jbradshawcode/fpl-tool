from datetime import date
from pathlib import Path


STAMP_FILE = Path("last_update.txt")


def should_update() -> bool:
    """Check if we should fetch new history data today."""
    if not STAMP_FILE.exists():
        return True
    last_date = STAMP_FILE.read_text().strip()
    return last_date != str(date.today())

def mark_updated():
    """Record today's date after updating history data."""
    STAMP_FILE.write_text(str(date.today()))
