import pandas as pd
import numpy as np

from copy import deepcopy
from typing import Optional

from tabulate import tabulate

from helpers.config import DISPLAY_COLS, DISPLAY_MAPPING
from helpers.logger import get_logger


logger = get_logger(__name__)


def build_difficulty_lookup(history_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Build interpolation arrays for fixture difficulty scaling factors.

    Computes mean xGI per difficulty level (1-5), normalised to difficulty 3.

    Parameters
    ----------
    history_df : pd.DataFrame
        Full player match history, must contain fixture_difficulty and
        expected_goal_involvements columns.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        xp : difficulty levels (1-5)
        yp : corresponding scaling factors relative to difficulty 3

    """
    rdf = (
        history_df.groupby("fixture_difficulty")["expected_goal_involvements"]
        .mean()
        .reset_index()
    )
    rdf["expected_goal_involvements"] /= rdf.loc[
        rdf["fixture_difficulty"] == 3, "expected_goal_involvements"
    ].values[0]
    return rdf["fixture_difficulty"].values, rdf["expected_goal_involvements"].values


def expected_points_per_90(
    history_df: pd.DataFrame,
    players_df: pd.DataFrame,
    position: Optional[str] = None,
    mins_threshold: float = None,
    time_period: Optional[int] = None,
) -> pd.DataFrame:
    """Compute expected and actual points per 90 minutes for players.

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
        Ranked table (descending by expected points) with player metadata
        merged in, including avg_fixture_difficulty and difficulty_factor.

    """
    # Build the difficulty lookup from the full history (not time-filtered)
    xp, yp = build_difficulty_lookup(history_df)

    df = deepcopy(history_df)

    # Filter by recent rounds if time_period is specified
    if time_period is not None:
        latest_round = history_df["round"].max()
        recent_rounds = list(range(latest_round - time_period + 1, latest_round + 1))
        df = df[df["round"].isin(recent_rounds)]

    # Filter by position if specified
    if position is not None:
        df = df[df["pos_abbr"] == position]

    # Group by player and fixture (opponent disambiguates double gameweeks)
    grouped = df.groupby(["element", "round", "opponent_team_name"]).agg(
        total_minutes=("minutes", "sum"),
        total_expected_points=("expected_points", "sum"),
        total_actual_points=("total_points", "sum"),
        avg_fixture_difficulty=("fixture_difficulty", "mean"),
    )

    # Collapse back to element level
    grouped = grouped.groupby("element").agg(
        total_minutes=("total_minutes", "sum"),
        total_expected_points=("total_expected_points", "sum"),
        total_actual_points=("total_actual_points", "sum"),
        avg_fixture_difficulty=("avg_fixture_difficulty", "mean"),
    )

    # Calculate per-90 metrics
    grouped["expected_points_per_90"] = (
        grouped["total_expected_points"] / grouped["total_minutes"]
    ) * 90
    grouped["actual_points_per_90"] = (
        grouped["total_actual_points"] / grouped["total_minutes"]
    ) * 90
    grouped["percentage_of_mins_played"] = grouped["total_minutes"] / (
        len(df["round"].unique()) * 90
    )
    grouped["actual_points"] = (
        grouped["actual_points_per_90"] * grouped["percentage_of_mins_played"]
    )
    grouped["expected_points"] = (
        grouped["expected_points_per_90"] * grouped["percentage_of_mins_played"]
    )

    # Vectorised difficulty factor using linear interpolation
    grouped["difficulty_factor"] = np.interp(
        grouped["avg_fixture_difficulty"], xp, yp
    )

    # Apply minutes filter
    if mins_threshold is not None:
        grouped = grouped[grouped["percentage_of_mins_played"] >= mins_threshold]

    grouped = grouped.drop(
        columns=["total_expected_points", "total_actual_points", "total_minutes"]
    )

    # Merge with players_df
    merged = grouped.merge(players_df, left_index=True, right_index=True, how="left")
    merged = merged.sort_values("expected_points", ascending=False)
    merged = merged.reset_index(drop=False)
    merged.index = merged.index + 1

    return merged


def display_df(df: pd.DataFrame) -> None:
    """Format and print a DataFrame of player metrics in a readable table."""
    df["actual_points"] = (df["actual_points"]).round(2)
    df["expected_points"] = (df["expected_points"]).round(2)
    df["actual_points_per_90"] = df["actual_points_per_90"].round(2)
    df["expected_points_per_90"] = df["expected_points_per_90"].round(2)
    df["now_cost"] = df["now_cost"] / 10
    df["percentage_of_mins_played"] = (df["percentage_of_mins_played"] * 100).map(
        "{:.2f}%".format,
    )

    output_df = df[DISPLAY_COLS].rename(columns=DISPLAY_MAPPING)
    logger.info("\n%s", tabulate(output_df, headers="keys", tablefmt="psql"))
