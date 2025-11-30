"""Utilities for tracking the last update of Fantasy Premier League data.

Provides simple functions to check whether data should be refreshed and
to record the date of the last update.
"""

from datetime import datetime, timezone
from pathlib import Path

STAMP_FILE = Path(__file__).parent.parent / "data" / "last_update.txt"


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

    try:
        last_date = STAMP_FILE.read_text().strip()
        return last_date != str(datetime.now(tz=timezone.utc).date())
    except (OSError, IOError):
        # If we can't read the file, assume we should update
        return True


def mark_updated() -> None:
    """Record today's date in the stamp file after updating history data.

    Returns
    -------
    None

    """
    try:
        STAMP_FILE.parent.mkdir(parents=True, exist_ok=True)
        STAMP_FILE.write_text(str(datetime.now(tz=timezone.utc).date()) + "\n")
    except (OSError, IOError) as e:
        # Log or re-raise depending on application needs
        raise RuntimeError(f"Failed to update stamp file: {e}") from e
