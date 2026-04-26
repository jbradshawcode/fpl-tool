"""Flask route handlers and helper functions for FPL analysis app.

This module contains all route definitions and helper functions
to keep app.py as a minimal entry point.
"""

import json
import webbrowser
from typing import Tuple

import pandas as pd

from domain import calculations, history
from config import BOOTSTRAP_STATIC_ENDPOINT
from infrastructure.loading import initialise_data, search_players
from infrastructure.logger import get_logger
from infrastructure.update_guard import mark_updated, should_update


logger = get_logger(__name__)


def open_browser():
    """Open the web browser to the Flask app URL."""
    webbrowser.open_new("http://127.0.0.1:5002/")


def load_data():
    """Load and prepare FPL data with expected points calculations."""
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

    history_df = history.calculate_expected_points(
        history_df=history_df,
        players_df=players_df,
        scoring=scoring,
    )

    return players_df, history_df, fdr_df, scoring


def format_player_data(df: pd.DataFrame) -> pd.DataFrame:
    """Format DataFrame for display with proper rounding and conversions."""
    df = df.copy()
    df["actual_points"] = df["actual_points"].round(2)
    df["expected_points"] = df["expected_points"].round(2)
    df["actual_points_per_90"] = df["actual_points_per_90"].round(2)
    df["expected_points_per_90"] = df["expected_points_per_90"].round(2)
    df["now_cost"] = df["now_cost"] / 10
    df["percentage_of_mins_played"] = (df["percentage_of_mins_played"] * 100).round(2)
    return df


def get_game_metadata(history_df: pd.DataFrame) -> dict:
    """Calculate game metadata like max games and remaining rounds."""
    max_games = int(history_df["round"].max()) if len(history_df) > 0 else 38
    total_rounds = 38
    return {
        "max_games": max_games,
        "remaining_games": total_rounds - max_games,
        "default_games": min(5, max_games),
    }


def parse_query_params(flask_request, default_games: int, remaining_games: int) -> dict:
    """Parse and return all query parameters from request."""
    return {
        "selected_position": flask_request.args.get("position", "", type=str),
        "page": flask_request.args.get("page", 1, type=int),
        "mins_threshold": flask_request.args.get("mins", 70, type=int),
        "time_period": flask_request.args.get("games", default_games, type=int),
        "sort_by": flask_request.args.get("sort", "expected_points", type=str),
        "sort_order": flask_request.args.get("order", "desc", type=str),
        "selected_team": flask_request.args.get("team", "", type=str),
        "price_max": flask_request.args.get("price_max", None, type=float),
        "search_term": flask_request.args.get("search", "", type=str),
        "adjust_difficulty": flask_request.args.get(
            "adjust_difficulty", "true", type=str
        )
        == "true",
        "horizon": min(flask_request.args.get("horizon", 5, type=int), remaining_games),
    }


def get_position_names() -> dict:
    """Return mapping of position codes to display names."""
    return {
        "GKP": "Goalkeepers",
        "DEF": "Defenders",
        "MID": "Midfielders",
        "FWD": "Forwards",
    }


def fetch_player_data(
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
    """Fetch expected points data for selected position(s)."""
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


def extract_pinned_players(
    df: pd.DataFrame, pinned_players: list
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Extract pinned players from dataframe and return both sets."""
    if not pinned_players or len(df) == 0 or "web_name" not in df.columns:
        return pd.DataFrame(), df

    pinned_df = df[df["web_name"].isin(pinned_players)].copy()
    remaining_df = df[~df["web_name"].isin(pinned_players)].copy()

    if len(pinned_df) > 0:
        logger.info(f"Extracted {len(pinned_df)} pinned players")

    return pinned_df, remaining_df


def apply_filters(
    df: pd.DataFrame,
    price_max: float,
    selected_team: str,
    search_term: str,
    players_df: pd.DataFrame,
) -> pd.DataFrame:
    """Apply price, team, and search filters to player data."""
    df = df[df["now_cost"] <= price_max]

    if selected_team and "team_name" in df.columns:
        df = df[df["team_name"] == selected_team]

    if search_term and search_term.strip():
        filtered_players = search_players(players_df, search_term)
        if "web_name" in df.columns and len(filtered_players) > 0:
            df = df[df["web_name"].isin(filtered_players["web_name"])]
        elif len(filtered_players) == 0:
            return pd.DataFrame()

    return df


def sort_players(df: pd.DataFrame, sort_by: str, sort_order: str) -> pd.DataFrame:
    """Sort players by specified column with custom position handling."""
    if len(df) == 0:
        return df

    ascending = sort_order == "asc"

    if sort_by not in df.columns:
        default_col = "web_name" if "web_name" in df.columns else df.columns[0]
        logger.warning(f"Sort column '{sort_by}' not found, using '{default_col}'")
        return df.sort_values(by=default_col, ascending=ascending).reset_index(
            drop=True
        )

    if sort_by == "pos_abbr" and "pos_abbr" in df.columns:
        position_order = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}
        df["_sort_key"] = df["pos_abbr"].map(position_order)
        df = df.sort_values(by="_sort_key", ascending=ascending).reset_index(drop=True)
        df = df.drop(columns=["_sort_key"])
    else:
        df = df.sort_values(by=sort_by, ascending=ascending).reset_index(drop=True)

    logger.info(
        f"Sorting by {sort_by} ({'asc' if ascending else 'desc'}) - {len(df)} results"
    )
    return df


def paginate(
    df: pd.DataFrame, page: int, per_page: int = 10
) -> Tuple[pd.DataFrame, int, int, int]:
    """Calculate pagination and return page of players."""
    total_players = len(df)
    total_pages = max(1, (total_players + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_players = df.iloc[start_idx:end_idx].copy()
    page_players["rank"] = range(start_idx + 1, start_idx + len(page_players) + 1)

    return page_players, total_players, total_pages, page


def get_filter_bounds(df: pd.DataFrame) -> Tuple[list, float, float]:
    """Extract team list and price bounds for filter controls."""
    all_teams = (
        sorted(df["team_name"].dropna().unique().tolist())
        if "team_name" in df.columns
        else []
    )

    if len(df) > 0:
        price_min = round(float(df["now_cost"].min()), 1)
        price_max = round(float(df["now_cost"].max()), 1)
    else:
        price_min, price_max = 4.0, 15.0

    return all_teams, price_min, price_max
