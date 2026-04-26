"""Flask route handlers and helper functions for FPL analysis app.

This module contains all route definitions and helper functions
to keep app.py as a minimal entry point.
"""

import webbrowser

import pandas as pd

from infrastructure.logger import get_logger


logger = get_logger(__name__)


def open_browser():
    """Open the web browser to the Flask app URL."""
    webbrowser.open_new("http://127.0.0.1:5002/")


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
