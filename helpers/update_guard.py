"""Utilities for tracking the last update of Fantasy Premier League data.

Provides simple functions to check whether data should be refreshed and
to record the date of the last update.
"""

from datetime import datetime, timezone
from pathlib import Path

STAMP_FILE = Path("data/last_update.txt")


def should_update() -> bool:
    """Determine whether new history data should be fetched today.

    Returns
    -------
    bool
        True if the data should be updated (either the stamp file does not
        exist or it is not from today), False otherwise.

    """
    if not STAMP_FILE.exists():
        return True
    last_date = STAMP_FILE.read_text().strip()
    return last_date != str(datetime.now(tz=timezone.utc).date())


def mark_updated() -> None:
    """Record today's date in the stamp file after updating history data.

    Returns
    -------
    None

    """
    STAMP_FILE.write_text(str(datetime.now(tz=timezone.utc).date()))
