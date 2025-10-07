import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import Dict, List
from fpl.api import fetch_data
from fpl.config import SUPPORTED_HISTORY_METRICS


def fetch_player_history(element_id: int, team_map: Dict[int, str]) -> pd.DataFrame:
    data = fetch_data(f"element-summary/{element_id}/")
    if not data or "history" not in data:
        return pd.DataFrame()
    df = pd.DataFrame(data["history"])
    df["opponent_team_name"] = df["opponent_team"].map(team_map)
    return df[SUPPORTED_HISTORY_METRICS]


def fetch_all_histories(player_ids: List[int], team_map: Dict[int, str], max_workers: int = 20) -> pd.DataFrame:
    all_histories = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_player_history, pid, team_map): pid for pid in player_ids}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching player histories"):
            df = future.result()
            if not df.empty:
                all_histories.append(df)
    if not all_histories:
        return pd.DataFrame()
    return pd.concat(all_histories, ignore_index=True).sort_values(by=["element", "round"]).reset_index(drop=True)


def calculate_expected_points(history_df: pd.DataFrame, players_df: pd.DataFrame, scoring: dict) -> pd.DataFrame:
    """Add expected_points to a history DataFrame"""
    if history_df.empty:
        return history_df

    pos_map = {'Goalkeeper': 'GKP', 'Defender': 'DEF', 'Midfielder': 'MID', 'Forward': 'FWD'}
    history_df['position'] = history_df['element'].map(players_df['position'])
    history_df['pos_abbr'] = history_df['position'].map(pos_map)

    # Play points
    long_short_points = (
        (history_df['minutes'] >= 60) * scoring['long_play'] +
        ((history_df['minutes'] > 0) & (history_df['minutes'] < 60)) * scoring['short_play']
    )

    # Defensive contribution bonus
    defensive_contribution_points = np.where(
        (history_df['pos_abbr'] == 'DEF') & (history_df['defensive_contribution'] >= 10),
        2,
        np.where(
            (history_df['pos_abbr'] != 'DEF') & (history_df['defensive_contribution'] >= 12),
            2,
            0
        )
    )

    # Clean sheet probability
    probability_clean_sheet = np.where(
        history_df['minutes'] >= 60,
        np.exp(-history_df['expected_goals_conceded'].astype(float)),
        0
    )
    expected_clean_sheet_points = history_df['pos_abbr'].map(scoring['clean_sheets']) * probability_clean_sheet

    # Vectorised expected points calculation
    history_df['expected_points'] = (
        history_df['expected_goals'].astype(float) * history_df['pos_abbr'].map(scoring['goals_scored']) +
        history_df['expected_assists'].astype(float) * scoring['assists'] +
        expected_clean_sheet_points +
        (history_df['expected_goals_conceded'].astype(float) // 2) * history_df['pos_abbr'].map(scoring['goals_conceded']) +
        history_df['own_goals'] * scoring['own_goals'] +
        history_df['penalties_saved'] * scoring['penalties_saved'] +
        history_df['penalties_missed'] * scoring['penalties_missed'] +
        history_df['yellow_cards'] * scoring['yellow_cards'] +
        history_df['red_cards'] * scoring['red_cards'] +
        (history_df['saves'] // 3) * scoring['saves'] +
        history_df['bonus'] * scoring['bonus'] +
        defensive_contribution_points +
        long_short_points
    )

    history_df[history_df["red_cards"] != 0]

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


def aggregate_expected_points(history_df: pd.DataFrame) -> pd.Series:
    """Return a Series of expected points summed per player"""
    if history_df.empty:
        return pd.Series(dtype=float)
    return history_df.groupby("element")["expected_points"].sum()
