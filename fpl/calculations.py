import pandas as pd

from copy import deepcopy
from typing import Optional

from tabulate import tabulate

from helpers.config import DISPLAY_COLS, DISPLAY_MAPPING
from helpers.logger import get_logger


# Get logger for this module
logger = get_logger(__name__)


def expected_points_per_90(
    history_df: pd.DataFrame,
    players_df: pd.DataFrame,
    position: Optional[str] = None,
    mins_threshold: float = None,
    time_period: Optional[int] = None,
) -> pd.DataFrame:
    """Compute expected and actual points per 90 minutes for players.

    This function calculates expected and actual points per 90 minutes, with
    optional filtering by position, recent rounds, and minimum minutes played.

    Parameters
    ----------
    history_df : pd.DataFrame
        Player-match history including minutes, expected points, and related metrics.
    players_df : pd.DataFrame
        Player metadata including names, teams, prices, and position data.
    position : str or None, optional
        Optional position filter using the short code (e.g. "DEF", "MID").
    mins_threshold : float, optional
        Minimum average minutes over the period required for inclusion.
    time_period : int or None, optional
        Number of most recent rounds to consider. If None, uses all rounds.

    Returns
    -------
    pd.DataFrame
        Ranked table (descending by expected points per 90) with player
        metadata merged in.

    """
    # Make a copy of history_df to avoid modifying original
    df = deepcopy(history_df)

    # Filter by recent rounds if time_period is specified
    if time_period is not None:
        latest_round = history_df["round"].max()
        recent_rounds = list(range(latest_round - time_period + 1, latest_round + 1))
        df = df[df["round"].isin(recent_rounds)]

    # Filter by position if specified
    if position is not None:
        df = df[df["pos_abbr"] == position]

    # Group by player and sum the raw values first
    grouped = df.groupby("element").agg(
        total_minutes=("minutes", "sum"),
        total_expected_points=("expected_points", "sum"),
        total_actual_points=("total_points", "sum"),
    )

    # Calculate per-90 metrics from the summed values
    grouped["expected_points_per_90"] = (grouped["total_expected_points"] / grouped["total_minutes"]) * 90
    grouped["actual_points_per_90"] = (grouped["total_actual_points"] / grouped["total_minutes"]) * 90
    grouped["percentage_of_mins_played"] = (grouped["total_minutes"] / (len(df["round"].unique()) * 90))
    grouped["actual_points"] = grouped["actual_points_per_90"] * grouped["percentage_of_mins_played"]
    grouped["expected_points"] = grouped["expected_points_per_90"] * grouped["percentage_of_mins_played"]

    # Apply minutes filter (e.g., at least 60% minutes played)
    if mins_threshold is not None:
        grouped = grouped[grouped["percentage_of_mins_played"] >= mins_threshold]

    # Clean up - drop the intermediate columns if not needed
    grouped = grouped.drop(columns=["total_expected_points", "total_actual_points", "total_minutes"])

    # Merge with players_df for names, teams, etc.
    merged = grouped.merge(players_df, left_index=True, right_index=True, how="left")

    # Sort by expected points per 90
    merged = merged.sort_values("expected_points", ascending=False)

    # Reset index
    merged = merged.reset_index(drop=False)
    merged.index = merged.index + 1  # Start index at 1 for display

    return merged


def display_df(df: pd.DataFrame) -> None:
    """Format and print a DataFrame of player metrics in a readable table.

    Rounds key numeric columns, converts percentage fields, selects relevant
    display columns, and prints the result using a PostgreSQL-style table.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing expected and actual points, minutes played
        percentage, and player metadata.

    """
    df["actual_points"] = (df["actual_points"]).round(2)
    df["expected_points"] = (df["expected_points"]).round(2)
    df["actual_points_per_90"] = df["actual_points_per_90"].round(2)
    df["expected_points_per_90"] = df["expected_points_per_90"].round(2)
    df["now_cost"] = df["now_cost"] / 10  # convert to millions
    df["percentage_of_mins_played"] = (df["percentage_of_mins_played"] * 100).map(
        "{:.2f}%".format,
    )

    output_df = df[DISPLAY_COLS].rename(columns=DISPLAY_MAPPING)
    logger.info("\n%s", tabulate(output_df, headers="keys", tablefmt="psql"))
