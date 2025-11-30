"""Load Fantasy Premier League data, compute expected points, and rank players.

This module:
- Fetches or loads cached player history and metadata
- Computes expected points using the `history` helper
- Filters players based on minutes played, position, and recent rounds
- Outputs the top performers in a formatted table
"""

import json
import logging
from copy import deepcopy
from pathlib import Path

import pandas as pd
from tabulate import tabulate

from fpl import history
from helpers.config import BOOTSTRAP_STATIC_ENDPOINT, DISPLAY_COLS, DISPLAY_MAPPING
from helpers.loading import initialise_data
from helpers.update_guard import mark_updated, should_update

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Execute the main program flow.

    Loads or fetches player data depending on cache state, computes expected
    points per 90 minutes for a specified position and time window, and prints
    a ranked table of the top performers.
    """
    # Fetch/update histories
    if should_update():
        data = initialise_data(endpoint=BOOTSTRAP_STATIC_ENDPOINT)
        players_df, history_df, scoring = (
            data["players_df"],
            data["history_df"],
            data["scoring"],
        )

        mark_updated()
    else:
        logger.info("Loading data from local files...")
        players_df = pd.read_csv("data/players_data.csv", index_col='id')
        history_df = pd.read_csv("data/player_histories.csv")

        with Path("data/scoring.json").open() as f:
            scoring = json.load(f)

    # Calculate expected points
    history_df = history.calculate_expected_points(
        history_df=history_df,
        players_df=players_df,
        scoring=scoring,
    )

    # Assess players
    df = expected_points_per_90(
        history_df=history_df,
        players_df=players_df,
        position="MID",
        mins_threshold=60,
        time_period=5,
    ).head(10)
    display_df(df)


def expected_points_per_90(
    history_df: pd.DataFrame,
    players_df: pd.DataFrame,
    position: str or None = None,
    mins_threshold: float = 60,
    time_period: int or None = None,
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

    # Group by player
    grouped = df.groupby("element").agg(
        avg_minutes=("minutes", "mean"),
        expected_points_per_90=("expected_points_per_90", "mean"),
        actual_points_per_90=("actual_points_per_90", "mean"),
        percentage_of_mins_played=("percentage_of_mins_played", "mean"),
    )

    # Apply minutes filter
    grouped = grouped[grouped["avg_minutes"] >= mins_threshold]

    # Merge with players_df for names, teams, etc.
    merged = grouped.merge(players_df, left_index=True, right_index=True, how="left")

    # Sort by expected points per 90
    merged = merged.sort_values("expected_points_per_90", ascending=False)

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
    df["actual_points_per_90"] = df["actual_points_per_90"].round(2)
    df["expected_points_per_90"] = df["expected_points_per_90"].round(2)
    df["now_cost"] = df["now_cost"] / 10  # convert to millions
    df["percentage_of_mins_played"] = (df["percentage_of_mins_played"] * 100).map(
        "{:.2f}%".format,
    )

    output_df = df[DISPLAY_COLS].rename(columns=DISPLAY_MAPPING)
    logger.info("\n%s", tabulate(output_df, headers="keys", tablefmt="psql"))


if __name__ == "__main__":
    main()
