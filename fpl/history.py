"""Retrieve, process, and analyze Fantasy Premier League player history data.

This module provides:
- Concurrent download of individual player history records
- Mapping and cleaning of FPL API history fields
- Vectorised calculation of expected points and per-90 metrics
- Aggregation helpers for summarising expected returns
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
from tqdm import tqdm

from fpl.api import fetch_data
from helpers.config import POS_MAP, SUPPORTED_HISTORY_METRICS
from helpers.loading import load_parameters


def fetch_player_history(element_id: int, team_map: dict[int, str]) -> pd.DataFrame:
    """Retrieve and format historical match data for a single player.

    Parameters
    ----------
    element_id : int
        Player ID used by the FPL API.
    team_map : dict[int, str]
        Mapping from team ID to readable team name.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the player's match-by-match history with
        opponent names mapped in. If no data is returned, an empty
        DataFrame is provided.

    """
    data = fetch_data(f"element-summary/{element_id}/")
    if not data or "history" not in data:
        return pd.DataFrame()
    df = pd.DataFrame(data["history"])
    df["opponent_team_name"] = df["opponent_team"].map(team_map)
    return df[SUPPORTED_HISTORY_METRICS]


def fetch_all_histories(
    player_ids: list[int],
    team_map: dict[int, str],
    max_workers: int = 20,
) -> pd.DataFrame:
    """Fetch match histories for multiple players concurrently.

    Parameters
    ----------
    player_ids : list[int]
        List of player element IDs.
    team_map : dict[int, str]
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
        Updated DataFrame with:
        - expected_points
        - expected_points_per_90
        - actual_points_per_90
        - percentage_of_mins_played
        plus added position and shorthand position codes.

    """
    if history_df.empty:
        return history_df

    params = load_parameters()

    history_df["position"] = history_df["element"].map(players_df["position"])
    history_df["pos_abbr"] = history_df["position"].map(POS_MAP)

    # Play points
    long_short_points = (
        history_df["minutes"] >= params["long_play_threshold"]
    ) * scoring["long_play"] + (
        (history_df["minutes"] > 0)
        & (history_df["minutes"] < params["long_play_threshold"])
    ) * scoring["short_play"]

    # Defensive contribution bonus
    defensive_contribution_points = np.where(
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

    # Clean sheet probability (exponential model)
    probability_clean_sheet = np.where(
        history_df["minutes"] >= params["long_play_threshold"],
        np.exp(-history_df["expected_goals_conceded"].astype(float)),
        0,
    )
    expected_clean_sheet_points = (
        history_df["pos_abbr"].map(scoring["clean_sheets"]) * probability_clean_sheet
    )

    # Vectorised expected points calculation
    history_df["expected_points"] = (
        history_df["expected_goals"].astype(float)
        * history_df["pos_abbr"].map(scoring["goals_scored"])
        + history_df["expected_assists"].astype(float) * scoring["assists"]
        + expected_clean_sheet_points
        + (history_df["expected_goals_conceded"].astype(float) // 2)
        * history_df["pos_abbr"].map(scoring["goals_conceded"])
        + history_df["own_goals"] * scoring["own_goals"]
        + history_df["penalties_saved"] * scoring["penalties_saved"]
        + history_df["penalties_missed"] * scoring["penalties_missed"]
        + history_df["yellow_cards"] * scoring["yellow_cards"]
        + history_df["red_cards"] * scoring["red_cards"]
        + (history_df["saves"] // 3) * scoring["saves"]
        + history_df["bonus"] * scoring["bonus"]
        + defensive_contribution_points
        + long_short_points
    )

    # Expected & actual points per 90
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
