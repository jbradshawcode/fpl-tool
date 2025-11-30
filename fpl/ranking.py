"""Utilities for ranking Fantasy Premier League players based on performance metrics.

This module provides functions to filter players by minimum minutes played
and rank them by a chosen metric with optional tie-breaking by price.
"""

import pandas as pd


def rank_players(
    df: pd.DataFrame,
    metric: str,
    mins_threshold: int,
    *,
    ascending: bool = False,
) -> pd.DataFrame:
    """Filter and rank players by a given metric, with optional tie-breaking by price.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing player statistics, including the metric column
        and a 'minutes' and 'now_cost' column.
    metric : str
        Name of the column to rank players by (e.g., 'expected_points_per_90').
    mins_threshold : int
        Minimum number of minutes played for a player to be included.
    ascending : bool, optional
        Whether to sort the metric in ascending order. Default is False
        (descending ranking).

    Returns
    -------
    pd.DataFrame
        Filtered and ranked DataFrame, sorted by the chosen metric and then
        by player cost to break ties.

    """
    return df[df["minutes"] > mins_threshold].sort_values(
        by=[metric, "now_cost"],
        ascending=[ascending, True],
    )
