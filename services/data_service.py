"""Data loading and orchestration service layer.

This module handles high-level data operations that coordinate between
domain logic and infrastructure.
"""

import json
import os
from typing import Optional, Tuple

import pandas as pd

from config import ARCHIVE_DIR, BOOTSTRAP_STATIC_ENDPOINT
from domain import calculations, history
from infrastructure.loading import archive_season, initialise_data
from infrastructure.logger import get_logger
from infrastructure.update_guard import mark_updated, should_update


logger = get_logger(__name__)


def _is_season_complete(bootstrap_data: dict) -> bool:
    """Check if all gameweek events are finished with bonus points confirmed."""
    events = bootstrap_data.get("events", [])
    if not events:
        return False
    return all(e.get("finished") and e.get("data_checked") for e in events)


def _get_season_name(bootstrap_data: dict) -> Optional[str]:
    """Derive season name (e.g., '2024-25') from bootstrap events."""
    events = bootstrap_data.get("events", [])
    if not events:
        return None
    first_deadline = events[0].get("deadline_time", "")
    if len(first_deadline) < 4:
        return None
    start_year = int(first_deadline[:4])
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def _try_archive_season(data: dict) -> None:
    """Archive season data if the season is complete and not already archived."""
    bootstrap = data.get("raw_bootstrap")
    if not bootstrap:
        return
    if not _is_season_complete(bootstrap):
        return
    season_name = _get_season_name(bootstrap)
    if not season_name:
        return
    archive_season(season_name, data)


def _get_archived_seasons() -> list[str]:
    """Return sorted list of archived season directory names."""
    if not os.path.isdir(ARCHIVE_DIR):
        return []
    return sorted(
        d
        for d in os.listdir(ARCHIVE_DIR)
        if os.path.isdir(os.path.join(ARCHIVE_DIR, d))
    )


def _concatenate_archived_history(
    history_df: pd.DataFrame, players_df: pd.DataFrame
) -> pd.DataFrame:
    """Prepend archived season history rows to current season data.

    Maps element IDs to stable `code` values so players are matched
    across seasons even when their seasonal ID changes.
    """
    archived_seasons = _get_archived_seasons()
    if not archived_seasons or "code" not in players_df.columns:
        return history_df

    # Build current season's element→code mapping
    current_id_to_code = players_df["code"]

    # Map current history to code
    history_df = history_df.copy()
    history_df["code"] = history_df["element"].map(current_id_to_code)

    archived_parts = []
    for season in archived_seasons:
        season_dir = os.path.join(ARCHIVE_DIR, season)
        players_path = os.path.join(season_dir, "players_data.csv")
        history_path = os.path.join(season_dir, "player_histories.csv")

        if not os.path.exists(players_path) or not os.path.exists(history_path):
            continue

        arch_players = pd.read_csv(players_path, index_col="id")
        if "code" not in arch_players.columns:
            logger.warning(f"Archive {season} missing 'code' column, skipping")
            continue

        arch_history = pd.read_csv(history_path)
        arch_id_to_code = arch_players["code"]
        arch_history["code"] = arch_history["element"].map(arch_id_to_code)

        # Offset rounds so archived seasons come before current season
        # e.g., 2024-25 GW1-38 become rounds -38 to -1
        max_round = int(arch_history["round"].max()) if len(arch_history) > 0 else 38
        arch_history["round"] = arch_history["round"] - max_round - 1

        archived_parts.append(arch_history)
        logger.info(f"Loaded {len(arch_history)} archived history rows from {season}")

    if not archived_parts:
        return history_df

    combined = pd.concat([*archived_parts, history_df], ignore_index=True)
    return combined.sort_values(by=["code", "round"]).reset_index(drop=True)


def _detect_new_to_league(players_df: pd.DataFrame) -> pd.DataFrame:
    """Add is_new_to_league column by checking against archived seasons."""
    archived_seasons = _get_archived_seasons()
    if not archived_seasons or "code" not in players_df.columns:
        players_df["is_new_to_league"] = False
        return players_df

    archived_codes = set()
    for season in archived_seasons:
        players_path = os.path.join(ARCHIVE_DIR, season, "players_data.csv")
        if not os.path.exists(players_path):
            continue
        arch_players = pd.read_csv(players_path, index_col="id")
        if "code" in arch_players.columns:
            archived_codes.update(arch_players["code"].dropna().astype(int).tolist())

    if not archived_codes:
        players_df["is_new_to_league"] = False
        return players_df

    players_df = players_df.copy()
    players_df["is_new_to_league"] = ~players_df["code"].isin(archived_codes)
    logger.info(
        f"Detected {players_df['is_new_to_league'].sum()} new-to-league players"
    )
    return players_df


def has_archived_data() -> bool:
    """Check if any archived season data exists."""
    return len(_get_archived_seasons()) > 0


def load_fpl_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and prepare FPL data with expected points calculated.

    Returns:
        Tuple of (players_df, history_df, fdr_df)
    """
    if should_update():
        data = initialise_data(endpoint=BOOTSTRAP_STATIC_ENDPOINT)
        players_df, history_df, fdr_df, scoring = (
            data["players_df"],
            data["history_df"],
            data["fdr_df"],
            data["scoring"],
        )
        _try_archive_season(data)
        mark_updated()
    else:
        logger.info("Loading data from local files...")
        players_df = pd.read_csv("data/players/players_data.csv", index_col="id")
        history_df = pd.read_csv("data/players/player_histories.csv")
        fdr_df = pd.read_csv("data/fixtures/fixture_difficulty_ratings.csv")
        fdr_df["round"] = fdr_df["round"].astype(int)
        fdr_df["team_id"] = fdr_df["team_id"].astype(int)
        fdr_df["fixture_difficulty"] = fdr_df["fixture_difficulty"].astype(int)

        with open("data/rules/scoring.json") as f:
            scoring = json.load(f)

    # Calculate expected points (domain logic)
    history_df = history.calculate_expected_points(
        history_df=history_df,
        players_df=players_df,
        scoring=scoring,
    )

    # Concatenate archived season data for a continuous timeline
    history_df = _concatenate_archived_history(history_df, players_df)

    # Detect new-to-league players
    players_df = _detect_new_to_league(players_df)

    return players_df, history_df, fdr_df


def fetch_players_for_analysis(
    players_df: pd.DataFrame,
    history_df: pd.DataFrame,
    fdr_df: pd.DataFrame,
    selected_positions: list,
    mins_threshold: int,
    time_period: int,
    max_games: int,
    adjust_difficulty: bool,
    horizon: int,
) -> pd.DataFrame:
    """Fetch player expected points data for analysis.

    Handles multiple positions or all positions based on selection.
    """
    fdr_arg = fdr_df if adjust_difficulty else None
    horizon_arg = horizon if adjust_difficulty else None

    positions = (
        selected_positions if selected_positions else ["GKP", "DEF", "MID", "FWD"]
    )

    if len(positions) == 1:
        return calculations.expected_points_per_90(
            history_df=history_df,
            players_df=players_df,
            position=positions[0],
            mins_threshold=mins_threshold / 100,
            time_period=time_period if time_period < max_games else None,
            fdr_df=fdr_arg,
            horizon=horizon_arg,
        )

    dfs = [
        calculations.expected_points_per_90(
            history_df=history_df,
            players_df=players_df,
            position=pos,
            mins_threshold=mins_threshold / 100,
            time_period=time_period if time_period < max_games else None,
            fdr_df=fdr_arg,
            horizon=horizon_arg,
        )
        for pos in positions
    ]
    return pd.concat(dfs, ignore_index=True)
