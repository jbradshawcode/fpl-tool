"""Data loading and orchestration service layer.

This module handles high-level data operations that coordinate between
domain logic and infrastructure.
"""

import json
from typing import Tuple

import pandas as pd

from config import BOOTSTRAP_STATIC_ENDPOINT
from domain import calculations, history
from infrastructure.loading import initialise_data
from infrastructure.logger import get_logger
from infrastructure.update_guard import mark_updated, should_update


logger = get_logger(__name__)


def load_fpl_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Load and prepare FPL data with expected points calculated.

    Returns:
        Tuple of (players_df, history_df, fdr_df, scoring)
    """
    if should_update():
        data = initialise_data(endpoint=BOOTSTRAP_STATIC_ENDPOINT)
        players_df, history_df, fdr_df, scoring = (
            data["players_df"],
            data["history_df"],
            data["fdr_df"],
            data["scoring"],
        )
        mark_updated()
    else:
        logger.info("Loading data from local files...")
        players_df = pd.read_csv("data/players_data.csv", index_col="id")
        history_df = pd.read_csv("data/player_histories.csv")
        fdr_df = pd.read_csv("data/fixture_difficulty_ratings.csv")
        fdr_df["round"] = fdr_df["round"].astype(int)
        fdr_df["team_id"] = fdr_df["team_id"].astype(int)
        fdr_df["fixture_difficulty"] = fdr_df["fixture_difficulty"].astype(int)

        with open("data/scoring.json") as f:
            scoring = json.load(f)

    # Calculate expected points (domain logic)
    history_df = history.calculate_expected_points(
        history_df=history_df,
        players_df=players_df,
        scoring=scoring,
    )

    return players_df, history_df, fdr_df, scoring


def fetch_players_for_analysis(
    players_df: pd.DataFrame,
    history_df: pd.DataFrame,
    fdr_df: pd.DataFrame,
    selected_position: str,
    mins_threshold: int,
    time_period: int,
    max_games: int,
    adjust_difficulty: bool,
    horizon: int,
) -> pd.DataFrame:
    """Fetch player expected points data for analysis.

    Handles single position or all positions based on selection.
    """
    fdr_arg = fdr_df if adjust_difficulty else None
    horizon_arg = horizon if adjust_difficulty else None

    if selected_position:
        return calculations.expected_points_per_90(
            history_df=history_df,
            players_df=players_df,
            position=selected_position,
            mins_threshold=mins_threshold / 100,
            time_period=time_period if time_period < max_games else None,
            fdr_df=fdr_arg,
            horizon=horizon_arg,
        )

    # Combine all positions
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
        for pos in ["GKP", "DEF", "MID", "FWD"]
    ]
    return pd.concat(dfs, ignore_index=True)
