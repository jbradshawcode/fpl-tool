"""Player-level preprocessing utilities for Fantasy Premier League data.

This module provides:
- Cleaning and enrichment of the raw FPL player dataset
- Mapping of teams and positions to readable names
- Construction of a filtered players DataFrame restricted to supported metrics
"""

import pandas as pd

from fpl.config import SUPPORTED_METRICS


def preprocess_players_df(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and enrich the raw players DataFrame.

    Adds a combined full name, converts the cost into millions, and removes
    unused name fields.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame of FPL players as returned by the API.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with a full name column and adjusted cost.

    """
    df = df.copy()
    df["now_cost"] = df["now_cost"] / 10  # convert to millions
    return df


def build_players_df(data: dict) -> tuple[pd.DataFrame, pd.Series]:
    """Construct a cleaned players DataFrame with readable team and position fields.

    Parameters
    ----------
    data : dict
        Dictionary returned by the FPL bootstrap-static endpoint, containing
        'elements', 'teams', and 'element_types'.

    Returns
    -------
    tuple[pd.DataFrame, pd.Series]
        players_df : pd.DataFrame
            The processed and filtered players DataFrame, containing only
            supported metrics.
        team_map : pd.Series
            Mapping from team ID to team name.

    """
    players_df = preprocess_players_df(
        pd.DataFrame(data["elements"]).set_index("id").sort_index(),
    )

    teams_df = pd.DataFrame(data["teams"])
    positions_df = pd.DataFrame(data["element_types"])

    # Maps
    team_map = teams_df.set_index("id")["name"]
    players_df["team_name"] = players_df["team"].map(team_map)

    positions_map = positions_df.set_index("id")["singular_name"]
    players_df["position"] = players_df["element_type"].map(positions_map)

    # Keep only supported metrics
    players_df = players_df[SUPPORTED_METRICS]

    return players_df, team_map
