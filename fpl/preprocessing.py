import pandas as pd
from fpl.config import SUPPORTED_METRICS


def preprocess_players_df(df: pd.DataFrame) -> pd.DataFrame:
    """Clean up player dataframe: add full name, adjust cost."""
    df = df.copy()
    df["full_name"] = df["first_name"] + " " + df["second_name"]
    df["now_cost"] = df["now_cost"] / 10  # convert to millions
    df.drop(columns=["first_name", "second_name"], inplace=True)
    return df


def build_players_df(data: dict) -> tuple[pd.DataFrame, pd.Series]:
    """
    Build players DataFrame with team names and positions mapped.

    Returns:
        players_df: filtered DataFrame with supported metrics
        team_map: mapping of team id -> team name
    """
    players_df = preprocess_players_df(pd.DataFrame(data["elements"]).set_index("id").sort_index())

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
