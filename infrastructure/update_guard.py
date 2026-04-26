"""Utilities for tracking the last update of Fantasy Premier League data.

Provides simple functions to check whether data should be refreshed and
to record the date of the last update.
"""

import os
from datetime import datetime, timezone

STAMP_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "last_update.txt")


def should_update() -> bool:
    """Determine whether new history data should be fetched today.

    Returns
    -------
    bool
        True if the data should be updated (either the stamp file does not
        exist or it is not from today), False otherwise.

    """
    if not os.path.exists(STAMP_FILE):
        return True

    try:
        with open(STAMP_FILE, "r") as f:
            last_date = f.read().strip()
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
        os.makedirs(os.path.dirname(STAMP_FILE), exist_ok=True)
        with open(STAMP_FILE, "w") as f:
            f.write(str(datetime.now(tz=timezone.utc).date()) + "\n")
    except (OSError, IOError) as e:
        # Log or re-raise depending on application needs
        raise RuntimeError(f"Failed to update stamp file: {e}") from e
