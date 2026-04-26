"""Player data processing and filtering service.

This module handles player-related business logic including
filtering, sorting, and pagination.
"""

from typing import Tuple

import pandas as pd

from infrastructure.loading import search_players
from infrastructure.logger import get_logger


logger = get_logger(__name__)


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


def apply_price_filter(df: pd.DataFrame, price_max: float) -> pd.DataFrame:
    """Filter players by maximum price."""
    return df[df["now_cost"] <= price_max]


def apply_team_filter(df: pd.DataFrame, selected_team: str) -> pd.DataFrame:
    """Filter players by team."""
    if not selected_team or "team_name" not in df.columns:
        return df
    return df[df["team_name"] == selected_team]


def apply_search_filter(
    df: pd.DataFrame, search_term: str, players_df: pd.DataFrame
) -> pd.DataFrame:
    """Filter players by name search term."""
    if not search_term or not search_term.strip():
        return df

    filtered_players = search_players(players_df, search_term)
    if "web_name" in df.columns and len(filtered_players) > 0:
        return df[df["web_name"].isin(filtered_players["web_name"])]
    elif len(filtered_players) == 0:
        return pd.DataFrame()
    return df


def apply_all_filters(
    df: pd.DataFrame,
    price_max: float,
    selected_team: str,
    search_term: str,
    players_df: pd.DataFrame,
) -> pd.DataFrame:
    """Apply all filters to player data."""
    df = apply_price_filter(df, price_max)
    df = apply_team_filter(df, selected_team)
    df = apply_search_filter(df, search_term, players_df)
    return df


def sort_by_column(df: pd.DataFrame, sort_by: str, sort_order: str) -> pd.DataFrame:
    """Sort dataframe by specified column with position handling."""
    if len(df) == 0:
        return df

    ascending = sort_order == "asc"

    if sort_by not in df.columns:
        default_col = "web_name" if "web_name" in df.columns else df.columns[0]
        logger.warning(f"Sort column '{sort_by}' not found, using '{default_col}'")
        return df.sort_values(by=default_col, ascending=ascending).reset_index(
            drop=True
        )

    # Custom position sort
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


def paginate_results(
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
