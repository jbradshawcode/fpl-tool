import pandas as pd
import numpy as np

from copy import deepcopy
from typing import Optional, Tuple

from infrastructure.logger import get_logger


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


def _filter_by_time_period(
    df: pd.DataFrame, time_period: Optional[int]
) -> pd.DataFrame:
    """Filter history dataframe by recent rounds."""
    if time_period is None:
        return df
    latest_round = int(df["round"].max())
    recent_rounds = list(range(latest_round - time_period + 1, latest_round + 1))
    return df[df["round"].isin(recent_rounds)]


def _filter_by_position(df: pd.DataFrame, position: Optional[str]) -> pd.DataFrame:
    """Filter history dataframe by position code."""
    if position is None:
        return df
    return df[df["pos_abbr"] == position]


def _ensure_numeric_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure key columns are numeric after CSV round-trip."""
    for col in ["minutes", "expected_points", "total_points", "fixture_difficulty"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _aggregate_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate player statistics grouped by element."""
    # Group by player and fixture (opponent disambiguates double gameweeks)
    grouped = df.groupby(["element", "round", "opponent_team_name"]).agg(
        total_minutes=("minutes", "sum"),
        total_expected_points=("expected_points", "sum"),
        total_actual_points=("total_points", "sum"),
        avg_fixture_difficulty=("fixture_difficulty", "mean"),
    )

    # Collapse back to element level
    return grouped.groupby("element").agg(
        total_minutes=("total_minutes", "sum"),
        total_expected_points=("total_expected_points", "sum"),
        total_actual_points=("total_actual_points", "sum"),
        avg_fixture_difficulty=("avg_fixture_difficulty", "mean"),
    )


def _apply_horizon_scaling(
    grouped: pd.DataFrame,
    players_df: pd.DataFrame,
    fdr_df: Optional[pd.DataFrame],
    horizon: Optional[int],
    latest_round: int,
    xp: np.ndarray,
    yp: np.ndarray,
) -> pd.DataFrame:
    """Apply horizon difficulty scaling to player stats."""
    grouped["avg_fixture_difficulty"] = grouped["avg_fixture_difficulty"].fillna(3.0)
    grouped["recency_factor"] = np.interp(grouped["avg_fixture_difficulty"], xp, yp)

    if fdr_df is not None and horizon is not None:
        horizon_factor = compute_horizon_factor(
            players_df, fdr_df, latest_round, horizon, xp, yp
        )
        grouped["horizon_factor"] = horizon_factor.reindex(grouped.index).fillna(1.0)
        grouped["scale"] = (
            (grouped["horizon_factor"] / grouped["recency_factor"])
            .fillna(1.0)
            .replace([np.inf, -np.inf], 1.0)
        )
    else:
        grouped["horizon_factor"] = np.nan
        grouped["scale"] = 1.0

    return grouped


def _calculate_per_90_stats(grouped: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Calculate per-90 and percentage statistics."""
    safe_minutes = grouped["total_minutes"].replace(0, np.nan)

    grouped["expected_points_per_90"] = (
        (grouped["total_expected_points"] / safe_minutes) * 90 * grouped["scale"]
    ).fillna(0)
    grouped["actual_points_per_90"] = (
        (grouped["total_actual_points"] / safe_minutes) * 90
    ).fillna(0)

    # Count fixtures per player
    fixtures_per_player = df.groupby("element").size().rename("fixture_count")
    grouped["fixture_count"] = fixtures_per_player.reindex(grouped.index)

    # Count only finished fixtures for percentage calculation
    if "finished" in df.columns:
        # Filter to only finished fixtures
        finished_df = df[df["finished"]]

        # Count finished fixtures per player
        finished_fixtures = (
            finished_df.groupby("element").size().rename("finished_fixture_count")
        )
        grouped["finished_fixture_count"] = finished_fixtures.reindex(
            grouped.index
        ).fillna(0)

        # Calculate total minutes and actual points only from finished fixtures
        finished_minutes = (
            finished_df.groupby("element")["minutes"]
            .sum()
            .rename("finished_total_minutes")
        )
        finished_actual_points = (
            finished_df.groupby("element")["total_points"]
            .sum()
            .rename("finished_total_actual_points")
        )

        grouped["finished_total_minutes"] = finished_minutes.reindex(
            grouped.index
        ).fillna(0)
        grouped["finished_total_actual_points"] = finished_actual_points.reindex(
            grouped.index
        ).fillna(0)

        # Use finished fixtures as denominator and finished minutes as numerator
        safe_finished_fixtures = grouped["finished_fixture_count"].replace(0, 1)
        grouped["percentage_of_mins_played"] = (
            grouped["finished_total_minutes"] / (safe_finished_fixtures * 90)
        ).fillna(0)
        grouped["actual_points"] = (
            grouped["finished_total_actual_points"] / safe_finished_fixtures
        ).fillna(0)

        # Drop intermediate columns
        grouped = grouped.drop(
            columns=[
                "finished_fixture_count",
                "finished_total_minutes",
                "finished_total_actual_points",
            ],
            errors="ignore",
        )
    else:
        # Fallback to all fixtures if finished column not available
        safe_fixture_count = grouped["fixture_count"].replace(0, 1)
        grouped["percentage_of_mins_played"] = (
            grouped["total_minutes"] / (safe_fixture_count * 90)
        ).fillna(0)
        grouped["actual_points"] = (
            grouped["total_actual_points"] / safe_fixture_count
        ).fillna(0)

    grouped["expected_points"] = (
        grouped["expected_points_per_90"] * grouped["percentage_of_mins_played"]
    ).fillna(0)

    return grouped


def _apply_minutes_filter(
    grouped: pd.DataFrame, mins_threshold: Optional[float]
) -> pd.DataFrame:
    """Filter players by minimum minutes percentage."""
    if mins_threshold is None:
        return grouped
    return grouped[grouped["percentage_of_mins_played"] >= mins_threshold]


def _merge_and_rank(grouped: pd.DataFrame, players_df: pd.DataFrame) -> pd.DataFrame:
    """Merge with player metadata and rank by expected points."""
    # Drop intermediate columns
    grouped = grouped.drop(
        columns=[
            "total_expected_points",
            "total_actual_points",
            "total_minutes",
            "scale",
        ],
        errors="ignore",
    )

    merged = grouped.merge(players_df, left_index=True, right_index=True, how="left")
    merged = merged.sort_values("expected_points", ascending=False)
    merged = merged.reset_index(drop=False)
    merged.index = merged.index + 1
    return merged


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

    Returns
    -------
    pd.DataFrame
        Ranked table with player metadata merged in.
    """
    # Build difficulty lookup
    xp, yp = build_difficulty_lookup(history_df)
    latest_round = int(history_df["round"].max())

    # Filter and prepare data
    df = deepcopy(history_df)
    df = _filter_by_time_period(df, time_period)
    df = _filter_by_position(df, position)
    df = _ensure_numeric_dtypes(df)

    # Aggregate stats
    grouped = _aggregate_player_stats(df)

    # Apply difficulty scaling
    grouped = _apply_horizon_scaling(
        grouped, players_df, fdr_df, horizon, latest_round, xp, yp
    )

    # Calculate per-90 stats
    grouped = _calculate_per_90_stats(grouped, df)

    # Apply filters and merge
    grouped = _apply_minutes_filter(grouped, mins_threshold)
    return _merge_and_rank(grouped, players_df)
