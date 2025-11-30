"""Data initialization and storage utilities for Fantasy Premier League.

This module provides functions to:
- Retrieve FPL data from the API
- Build structured DataFrames for players and histories
- Extract and save scoring rules
- Persist data locally as CSV and JSON
"""

import json
import logging
from pathlib import Path

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
        - 'scoring': dict of FPL scoring rules

    """
    data = retrieve_data(endpoint=endpoint)
    save_data(data=data)
    return data


def retrieve_data(endpoint: str) -> dict:
    """Retrieve FPL data and build DataFrames without saving to disk.

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
        - 'scoring': dict of FPL scoring rules

    """
    try:
        # Fetch static data
        logger.info("Fetching static data...")
        data = fetch_data(endpoint=endpoint)
    except Exception as e:
        logger.error(f"Failed to fetch data from API: {e}")
        raise

    # Build data structures
    logger.info("Building players dataframe...")
    players_df, team_map = preprocessing.build_players_df(data)

    logger.info("Fetching player histories...")
    history_df = history.fetch_all_histories(players_df.index.tolist(), team_map)

    scoring = data["game_config"]["scoring"]

    return {"players_df": players_df, "history_df": history_df, "scoring": scoring}


def save_data(data: dict) -> None:
    """Save player, history, and scoring data to local files.

    Args:
        data: Dictionary containing 'players_df', 'history_df', and 'scoring' keys.
    """
    required_keys = ['players_df', 'history_df', 'scoring']
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValueError(f"Missing required keys in data dict: {missing_keys}")
    
    required_keys = ['players_df', 'history_df', 'scoring']
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValueError(f"Missing required keys in data dict: {missing_keys}")

    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Save DataFrames to CSV
        data["players_df"].to_csv(data_dir / "players_data.csv", index=True, index_label='id')
        data["history_df"].to_csv(data_dir / "player_histories.csv", index=False)

        # Save scoring data to JSON
        with (data_dir / "scoring.json").open("w") as f:
            json.dump(data["scoring"], f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save data: {e}")
        raise


def load_parameters() -> dict:
    """Load and return parameters from the parameters.json file.

    Returns:
        dict: Dictionary containing the loaded parameters.

    """
    try:
        with Path("data/parameters.json").open() as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Parameters file not found at data/parameters.json")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in parameters file: {e}")
        raise
