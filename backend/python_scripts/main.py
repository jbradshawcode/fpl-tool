import requests
import pandas as pd


url = "https://fantasy.premierleague.com/api/bootstrap-static/"
profile_cols = [
    "full_name",
    "team_name",
    "position",
    "now_cost",
]

supported_metrics = [
    "assists",
    "bonus",
    "bps",
    "clean_sheets",
    "clean_sheets_per_90",
    "clearances_blocks_interceptions",
    "defensive_contribution",
    "defensive_contribution_per_90",
    "expected_assists",
    "expected_assists_per_90",
    "expected_goal_involvements",
    "expected_goal_involvements_per_90",
    "expected_goals",
    "expected_goals_conceded",
    "expected_goals_conceded_per_90",
    "expected_goals_per_90",
    "form",
    "full_name",
    "goals_conceded",
    "goals_conceded_per_90",
    "goals_scored",
    "minutes",
    "now_cost",
    "own_goals",
    "penalties_missed",
    "penalties_saved",
    "position",
    "recoveries",
    "red_cards",
    "saves",
    "selected_by_percent",
    "starts_per_90",
    "tackles",
    "team_name",
    "total_points",
    "transfers_in",
    "transfers_out",
    "yellow_cards",
]


def fetch_fpl_data(url: str) -> dict:
    # Send GET request
    response = requests.get(url)

    # Check if request was successful
    if response.status_code == 200:
        return response.json()  # Parse JSON into Python dict
    else:
        print("Failed to fetch data:", response.status_code)


def preprocess_players_df(df: pd.DataFrame) -> pd.DataFrame:
    # Preprocess the players DataFrame
    df["full_name"] = df["first_name"] + " " + df["second_name"]
    df["now_cost"] = df["now_cost"] / 10  # Convert to actual cost
    return df.drop(columns=["first_name", "second_name"])


def rank_players(df: pd.DataFrame, metric: str, mins_threshold: int, ascending: bool = False) -> pd.DataFrame:
    """
    Rank players based on a metric, filtering by minutes played,
    and break ties by lowest price.
    
    :param df: DataFrame with player data
    :param metric: Column name to rank by
    :param mins_threshold: Minimum minutes played
    :param ascending: Whether to sort ascending (default False for descending)
    :return: Ranked DataFrame
    """
    return (
        df[df["minutes"] > mins_threshold]
        .sort_values(by=[metric, "now_cost"], ascending=[ascending, True])
        [profile_cols + [metric]]
    )


if __name__ == "__main__":
    data = fetch_fpl_data(url=url)
    players_df = preprocess_players_df(df=pd.DataFrame(data["elements"]).set_index("id").sort_index(ascending=True))
    teams_df = pd.DataFrame(data["teams"]).rename(columns={"name": "team_name"})
    positions_df = pd.DataFrame(data["element_types"]).rename(columns={"singular_name": "position"})
    
    players_df["team_name"] = players_df.merge(teams_df, left_on="team", right_on="id")["team_name"]
    players_df["position"] = players_df.merge(positions_df, left_on="element_type", right_on="id")["position"]

    players_df = players_df[supported_metrics]

    rank_players(df=players_df, metric="assists", mins_threshold=90)
