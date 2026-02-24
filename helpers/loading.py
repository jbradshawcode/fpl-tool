"""Data initialization and storage utilities for Fantasy Premier League.

This module provides functions to:
- Retrieve FPL data from the API
- Build structured DataFrames for players and histories
- Extract and save scoring rules
- Persist data locally as CSV and JSON
"""

import json
import logging
import os

import pandas as pd

from helpers.api import fetch_data
from fpl import history, preprocessing

logger = logging.getLogger(__name__)


def initialise_data(endpoint: str) -> dict:
    """Fetch FPL data from the API, build structured DataFrames, and save locally.

    Parameters
    ----------
    endpoint : str
        Relative API endpoint to fetch (e.g., "bootstrap-static/").

    Returns
    -------
    dict
        Dictionary containing:
        - 'players_df': pd.DataFrame of processed player data
        - 'history_df': pd.DataFrame of match histories
        - 'fdr_df':     pd.DataFrame of fixture difficulty ratings (all rounds)
        - 'scoring':    dict of FPL scoring rules

    """
    data = retrieve_data(endpoint=endpoint)
    save_data(data=data)
    return data


def _build_fixture_difficulty_map(fixtures: list[dict]) -> pd.DataFrame:
    """Build a lookup table of fixture difficulty for all fixtures.

    Each fixture produces two rows — one per team perspective.
    Includes both past and future fixtures.

    Parameters
    ----------
    fixtures : list[dict]
        Raw fixture objects from the FPL fixtures endpoint.

    Returns
    -------
    pd.DataFrame
        Columns: round, team_id, opponent_id, fixture_difficulty, was_home

    """
    rows = []
    for f in fixtures:
        event = f.get("event")
        if event is None:
            continue  # skip unscheduled fixtures
        rows.append(
            {
                "round": event,
                "team_id": f["team_h"],
                "opponent_id": f["team_a"],
                "fixture_difficulty": f["team_h_difficulty"],
                "was_home": True,
            }
        )
        rows.append(
            {
                "round": event,
                "team_id": f["team_a"],
                "opponent_id": f["team_h"],
                "fixture_difficulty": f["team_a_difficulty"],
                "was_home": False,
            }
        )
    return pd.DataFrame(rows)


def _merge_fixture_difficulty(
    history_df: pd.DataFrame,
    players_df: pd.DataFrame,
    fdr_df: pd.DataFrame,
) -> pd.DataFrame:
    """Join fixture difficulty onto the player history DataFrame.

    Parameters
    ----------
    history_df : pd.DataFrame
        Player match-history table (element, round, opponent_team_name, ...).
    players_df : pd.DataFrame
        Player metadata; used to look up each player's team ID.
    fdr_df : pd.DataFrame
        Fixture difficulty map from _build_fixture_difficulty_map.

    Returns
    -------
    pd.DataFrame
        history_df with fixture_difficulty column appended.

    """
    element_to_team = players_df["team"]
    history_df = history_df.copy()
    history_df["_team_id"] = history_df["element"].map(element_to_team)

    history_df = history_df.merge(
        fdr_df[["round", "team_id", "fixture_difficulty"]],
        left_on=["round", "_team_id"],
        right_on=["round", "team_id"],
        how="left",
    ).drop(columns=["_team_id", "team_id"])

    # Deduplicate on the natural fixture key — keeps each actual fixture once
    # (handles merge fan-out) without collapsing double gameweek rows
    history_df = history_df.drop_duplicates(
        subset=["element", "round", "opponent_team_name"]
    ).reset_index(drop=True)

    return history_df


def retrieve_data(endpoint: str) -> dict:
    """Retrieve FPL data and build DataFrames without saving to disk."""
    try:
        logger.info("Fetching static data...")
        data = fetch_data(endpoint=endpoint)
    except Exception as e:
        logger.error(f"Failed to fetch data from API: {e}")
        raise

    logger.info("Building players dataframe...")
    players_df, team_map = preprocessing.build_players_df(data)

    logger.info("Fetching player histories...")
    history_df = history.fetch_all_histories(players_df.index.tolist(), team_map)

    logger.info("Fetching fixtures and merging difficulty ratings...")
    fixtures = fetch_data("fixtures/")
    fdr_df = _build_fixture_difficulty_map(fixtures)
    history_df = _merge_fixture_difficulty(history_df, players_df, fdr_df)

    scoring = data["game_config"]["scoring"]

    return {
        "players_df": players_df,
        "history_df": history_df,
        "fdr_df": fdr_df,
        "scoring": scoring,
    }


def save_data(data: dict) -> None:
    """Save player, history, fdr, and scoring data to local files."""
    required_keys = ["players_df", "history_df", "fdr_df", "scoring"]
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValueError(f"Missing required keys in data dict: {missing_keys}")

    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)

    try:
        data["players_df"].to_csv(
            f"{data_dir}/players_data.csv", index=True, index_label="id"
        )
        data["history_df"].to_csv(f"{data_dir}/player_histories.csv", index=False)
        data["fdr_df"].to_csv(f"{data_dir}/fixture_difficulty_ratings.csv", index=False)

        with open(f"{data_dir}/scoring.json", "w") as f:
            json.dump(data["scoring"], f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save data: {e}")
        raise


def load_parameters() -> dict:
    """Load and return parameters from the parameters.json file."""
    try:
        with open("data/parameters.json") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Parameters file not found at data/parameters.json")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in parameters file: {e}")
        raise
