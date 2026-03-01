import pandas as pd
import numpy as np

from copy import deepcopy
from typing import Optional, Tuple

from helpers.logger import get_logger


logger = get_logger(__name__)


def build_difficulty_lookup(history_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Build interpolation arrays for fixture difficulty scaling factors.

    Computes mean expected_points per difficulty level (1-5), normalised to
    difficulty 3.  Using expected_points (rather than expected_goal_involvements)
    ensures the scaling factor reflects how the *entire* xP metric varies with
    opponent strength, including components that are largely difficulty-invariant
    (appearance points, clean-sheet points, etc.).

    Parameters
    ----------
    history_df : pd.DataFrame
        Full player match history, must contain fixture_difficulty and
        expected_points columns.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        xp : difficulty levels (1-5)
        yp : corresponding scaling factors relative to difficulty 3

    """
    rdf = (
        history_df.assign(
            expected_points=pd.to_numeric(
                history_df["expected_points"], errors="coerce"
            ),
            fixture_difficulty=pd.to_numeric(
                history_df["fixture_difficulty"], errors="coerce"
            ),
        )
        .groupby("fixture_difficulty")["expected_points"]
        .mean()
        .reset_index()
    )
    rdf["expected_points"] /= rdf.loc[
        rdf["fixture_difficulty"] == 3, "expected_points"
    ].values[0]
    return rdf["fixture_difficulty"].values, rdf["expected_points"].values


def compute_horizon_factor(
    players_df: pd.DataFrame,
    fdr_df: pd.DataFrame,
    current_round: int,
    horizon: int,
    xp: np.ndarray,
    yp: np.ndarray,
) -> pd.Series:
    """Compute average difficulty factor for each player's upcoming fixtures.

    Parameters
    ----------
    players_df : pd.DataFrame
        Player metadata; index is element id, must contain 'team' column.
    fdr_df : pd.DataFrame
        Full fixture difficulty map (all rounds, both teams).
    current_round : int
        The most recently completed round.
    horizon : int
        Number of upcoming rounds to look ahead.
    xp, yp : np.ndarray
        Difficulty interpolation arrays from build_difficulty_lookup.

    Returns
    -------
    pd.Series
        Index = element id, values = horizon difficulty factor.

    """
    upcoming_rounds = list(range(current_round + 1, current_round + horizon + 1))
    upcoming = fdr_df[fdr_df["round"].isin(upcoming_rounds)]

    # Average difficulty per team over the horizon
    team_avg = (
        upcoming.groupby("team_id")["fixture_difficulty"]
        .mean()
        .rename("avg_horizon_difficulty")
    )

    # Map element → team → avg difficulty → factor
    element_team = players_df["team"]
    element_avg = element_team.map(team_avg)
    horizon_factor = pd.Series(
        np.interp(element_avg.values, xp, yp),
        index=element_avg.index,
        name="horizon_factor",
    )
    return horizon_factor


def expected_points_per_90(
    history_df: pd.DataFrame,
    players_df: pd.DataFrame,
    position: Optional[str] = None,
    mins_threshold: float = None,
    time_period: Optional[int] = None,
    fdr_df: Optional[pd.DataFrame] = None,
    horizon: Optional[int] = None,
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
    fdr_df : pd.DataFrame or None, optional
        Full fixture difficulty map. Required if horizon is set.
    horizon : int or None, optional
        Number of upcoming rounds to use for forward difficulty scaling.
        If provided alongside fdr_df, xP and xP/90 are scaled by
        (horizon_factor / recency_factor).

    Returns
    -------
    pd.DataFrame
        Ranked table with player metadata merged in. If horizon scaling is
        active, includes adjusted_expected_points and adjusted_expected_points_per_90.

    """
    # Build the difficulty lookup from the full history (not time-filtered)
    xp, yp = build_difficulty_lookup(history_df)

    df = deepcopy(history_df)

    # Filter by recent rounds if time_period is specified
    if time_period is not None:
        latest_round = int(history_df["round"].max())
        recent_rounds = list(range(latest_round - time_period + 1, latest_round + 1))
        df = df[df["round"].isin(recent_rounds)]
    else:
        latest_round = int(history_df["round"].max())

    # Filter by position if specified
    if position is not None:
        df = df[df["pos_abbr"] == position]

    # Ensure numeric dtypes (columns may be object after CSV round-trip)
    for col in ["minutes", "expected_points", "total_points", "fixture_difficulty"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

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

    # Build scale: horizon_factor / recency_factor (1.0 if adjustment off)
    grouped["avg_fixture_difficulty"] = grouped["avg_fixture_difficulty"].fillna(
        3.0
    )  # neutral if unknown
    grouped["recency_factor"] = np.interp(grouped["avg_fixture_difficulty"], xp, yp)

    if fdr_df is not None and horizon is not None:
        horizon_factor = compute_horizon_factor(
            players_df, fdr_df, latest_round, horizon, xp, yp
        )
        grouped["horizon_factor"] = horizon_factor.reindex(grouped.index).fillna(1.0)
        scale = (
            (grouped["horizon_factor"] / grouped["recency_factor"])
            .fillna(1.0)
            .replace([np.inf, -np.inf], 1.0)
        )
    else:
        grouped["horizon_factor"] = np.nan
        scale = 1.0

    # Safe division — 0 minutes gives 0 rather than NaN
    safe_minutes = grouped["total_minutes"].replace(0, np.nan)
    grouped["expected_points_per_90"] = (
        (grouped["total_expected_points"] / safe_minutes) * 90 * scale
    ).fillna(0)
    grouped["actual_points_per_90"] = (
        (grouped["total_actual_points"] / safe_minutes) * 90
    ).fillna(0)
    # Count fixtures per player (each row in df is one fixture)
    fixtures_per_player = df.groupby("element").size().rename("fixture_count")
    grouped["fixture_count"] = fixtures_per_player.reindex(grouped.index)
    grouped["percentage_of_mins_played"] = (
        grouped["total_minutes"] / (grouped["fixture_count"] * 90)
    ).fillna(0)
    grouped["actual_points"] = (
        grouped["total_actual_points"] / grouped["fixture_count"]
    ).fillna(0)
    grouped["expected_points"] = (
        grouped["expected_points_per_90"] * grouped["percentage_of_mins_played"]
    ).fillna(0)

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
