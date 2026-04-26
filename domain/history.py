"""Retrieve, process, and analyze Fantasy Premier League player history data.

This module provides:
- Concurrent download of individual player history records
- Mapping and cleaning of FPL API history fields
- Vectorised calculation of expected points and per-90 metrics
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
from typing import List, Dict
from tqdm import tqdm

from infrastructure.api_client import fetch_data
from config import POS_MAP, SUPPORTED_HISTORY_METRICS
from infrastructure.loading import load_parameters


def fetch_player_history(element_id: int, team_map: Dict[int, str]) -> pd.DataFrame:
    """Retrieve and format historical match data for a single player.

    Parameters
    ----------
    element_id : int
        Player ID used by the FPL API.
    team_map : Dict[int, str]
        Mapping from team ID to readable team name.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the player's match-by-match history with
        opponent names mapped in. If no data is returned, an empty
        DataFrame is provided.

    """
    data = fetch_data(f"element-summary/{element_id}/")

    # Check if data exists and history is not empty
    if not data or "history" not in data or not data["history"]:
        return pd.DataFrame()

    df = pd.DataFrame(data["history"])

    # Only map opponent_team if the column exists
    if "opponent_team" in df.columns:
        df["opponent_team_name"] = df["opponent_team"].map(team_map)

    # Only select supported metrics that exist in the DataFrame
    available_metrics = [col for col in SUPPORTED_HISTORY_METRICS if col in df.columns]

    if not available_metrics:
        return pd.DataFrame()

    return df[available_metrics]


def fetch_all_histories(
    player_ids: List[int],
    team_map: Dict[int, str],
    max_workers: int = 20,
) -> pd.DataFrame:
    """Fetch match histories for multiple players concurrently.

    Parameters
    ----------
    player_ids : List[int]
        List of player element IDs.
    team_map : Dict[int, str]
        Mapping from team ID to readable team names.
    max_workers : int, optional
        Number of worker threads to use for parallel requests.

    Returns
    -------
    pd.DataFrame
        Combined and sorted match history for all players. Returns an empty
        DataFrame if no histories could be retrieved.

    """
    all_histories = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_player_history, pid, team_map): pid
            for pid in player_ids
        }
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Fetching player histories",
        ):
            df = future.result()
            if not df.empty:
                all_histories.append(df)

    if not all_histories:
        return pd.DataFrame()

    return (
        pd.concat(all_histories, ignore_index=True)
        .sort_values(by=["element", "round"])
        .reset_index(drop=True)
    )


def _add_position_info(
    history_df: pd.DataFrame, players_df: pd.DataFrame
) -> pd.DataFrame:
    """Add position and position abbreviation to history dataframe."""
    history_df["position"] = history_df["element"].map(players_df["position"])
    history_df["pos_abbr"] = history_df["position"].map(POS_MAP)
    return history_df


def _calculate_play_points(
    history_df: pd.DataFrame, params: dict, scoring: dict
) -> pd.Series:
    """Calculate appearance points based on minutes played."""
    return (history_df["minutes"] >= params["long_play_threshold"]) * scoring[
        "long_play"
    ] + (
        (history_df["minutes"] > 0)
        & (history_df["minutes"] < params["long_play_threshold"])
    ) * scoring["short_play"]


def _calculate_defensive_points(history_df: pd.DataFrame, params: dict) -> pd.Series:
    """Calculate defensive contribution bonus points."""
    return np.where(
        (history_df["pos_abbr"] == "DEF")
        & (history_df["defensive_contribution"] >= params["defcon_threshold"]["def"]),
        2,
        np.where(
            (history_df["pos_abbr"] != "DEF")
            & (
                history_df["defensive_contribution"]
                >= params["defcon_threshold"]["non_def"]
            ),
            2,
            0,
        ),
    )


def _calculate_clean_sheet_points(
    history_df: pd.DataFrame, params: dict, scoring: dict
) -> pd.Series:
    """Calculate expected clean sheet points using exponential probability model."""
    probability_clean_sheet = np.where(
        history_df["minutes"] >= params["long_play_threshold"],
        np.exp(-history_df["expected_goals_conceded"].astype(float)),
        0,
    )
    return history_df["pos_abbr"].map(scoring["clean_sheets"]) * probability_clean_sheet


def _calculate_gc_penalty_points(
    history_df: pd.DataFrame, params: dict, scoring: dict
) -> pd.Series:
    """Calculate expected goals conceded penalty points (-0.5 per xGC)."""
    xgc = history_df["expected_goals_conceded"].astype(float)
    return np.where(
        history_df["minutes"] >= params["long_play_threshold"],
        xgc * history_df["pos_abbr"].map(scoring["goals_conceded"]) / 2,
        0,
    )


def _calculate_attack_points(history_df: pd.DataFrame, scoring: dict) -> pd.Series:
    """Calculate points from expected goals and assists."""
    return (
        history_df["expected_goals"].astype(float)
        * history_df["pos_abbr"].map(scoring["goals_scored"])
        + history_df["expected_assists"].astype(float) * scoring["assists"]
    )


def _calculate_event_points(history_df: pd.DataFrame, scoring: dict) -> pd.Series:
    """Calculate points from actual match events (cards, saves, etc.)."""
    return (
        history_df["own_goals"] * scoring["own_goals"]
        + history_df["penalties_saved"] * scoring["penalties_saved"]
        + history_df["penalties_missed"] * scoring["penalties_missed"]
        + history_df["yellow_cards"] * scoring["yellow_cards"]
        + history_df["red_cards"] * scoring["red_cards"]
        + (history_df["saves"] // 3) * scoring["saves"]
        + history_df["bonus"] * scoring["bonus"]
    )


def _calculate_per_90_metrics(history_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate per-90 metrics and percentage of minutes played."""
    history_df["expected_points_per_90"] = np.where(
        history_df["minutes"] != 0,
        np.where(
            history_df["red_cards"] == 0,
            (history_df["expected_points"] / history_df["minutes"]) * 90,
            history_df["expected_points"],
        ),
        0,
    )

    history_df["actual_points_per_90"] = np.where(
        history_df["minutes"] != 0,
        np.where(
            history_df["red_cards"] == 0,
            (history_df["total_points"] / history_df["minutes"]) * 90,
            history_df["total_points"],
        ),
        0,
    )

    history_df["percentage_of_mins_played"] = history_df["minutes"] / 90
    return history_df


def calculate_expected_points(
    history_df: pd.DataFrame,
    players_df: pd.DataFrame,
    scoring: dict,
) -> pd.DataFrame:
    """Compute expected points and per-90 metrics for each match entry.

    Parameters
    ----------
    history_df : pd.DataFrame
        Player match-history table containing minutes, goals, xG, xA,
        defensive actions, and other event data.
    players_df : pd.DataFrame
        Player metadata including position and team.
    scoring : dict
        FPL scoring rules dict (goals, assists, cards, clean sheets, etc.).

    Returns
    -------
    pd.DataFrame
        Updated DataFrame with expected_points, per-90 metrics,
        and position information added.
    """
    if history_df.empty:
        return history_df

    params = load_parameters()

    # Add position info
    history_df = _add_position_info(history_df, players_df)

    # Calculate all scoring components
    play_points = _calculate_play_points(history_df, params, scoring)
    defensive_points = _calculate_defensive_points(history_df, params)
    clean_sheet_points = _calculate_clean_sheet_points(history_df, params, scoring)
    gc_penalty_points = _calculate_gc_penalty_points(history_df, params, scoring)
    attack_points = _calculate_attack_points(history_df, scoring)
    event_points = _calculate_event_points(history_df, scoring)

    # Combine all components
    history_df["expected_points"] = (
        attack_points
        + clean_sheet_points
        + gc_penalty_points
        + event_points
        + defensive_points
        + play_points
    )

    # Calculate per-90 metrics
    return _calculate_per_90_metrics(history_df)
