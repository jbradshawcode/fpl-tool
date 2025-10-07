import logging
import pandas as pd
from copy import deepcopy
from tabulate import tabulate
from fpl import api, preprocessing, history, ranking
from utils.update_guard import should_update, mark_updated

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    data = api.fetch_data("bootstrap-static/")
    if not data:
        logging.error("No bootstrap data")
        return

    players_df, team_map = preprocessing.build_players_df(data)

    # Fetch/update histories
    if should_update():
        history_df = history.fetch_all_histories(players_df.index.tolist(), team_map)
        if not history_df.empty:
            history_df.to_csv("player_histories.csv", index=False)
            mark_updated()
    else:
        history_df = pd.read_csv("player_histories.csv") if pd.io.common.file_exists("player_histories.csv") else pd.DataFrame()

    # Calculate expected points
    history_df = history.calculate_expected_points(history_df, players_df, scoring=data["game_config"]["scoring"])

    # Assess players
    df = expected_points_per_90(
        history_df=history_df,
        players_df=players_df,
        position="FWD",
        mins_threshold=60,
        time_period=5,
    )
    display_df(df)


### DEV WORK HERE ###
def expected_points_per_90(
        history_df: pd.DataFrame,
        players_df: pd.DataFrame,
        position: str = None,
        mins_threshold: float = 60,
        time_period: int = None,
    ):
    """
    Filter players by average minutes played over last `time_period` rounds,
    optionally by position, and sort by expected points.
    """
    # Make a copy of history_df to avoid modifying original
    df = deepcopy(history_df)

    # Filter by recent rounds if time_period is specified
    if time_period is not None:
        latest_round = history_df['round'].max()
        recent_rounds = list(range(latest_round - time_period + 1, latest_round + 1))
        df = df[df['round'].isin(recent_rounds)]
    
    # Filter by position if specified
    if position is not None:
        df = df[df['pos_abbr'] == position]

    # Group by player
    grouped = df.groupby("element").agg(
        avg_minutes=("minutes", "mean"),
        expected_points_per_90=("expected_points_per_90", "mean"),
        actual_points_per_90=("actual_points_per_90", "mean"),
        percentage_of_mins_played=("percentage_of_mins_played", "mean"),
    )

    # Apply minutes filter
    grouped = grouped[grouped["avg_minutes"] >= mins_threshold]

    # Merge with players_df for names, teams, etc.
    merged = grouped.merge(players_df, left_index=True, right_index=True, how="left")

    # Sort by expected points per 90
    merged = merged.sort_values("expected_points_per_90", ascending=False)

    # Reset index and return
    return merged.reset_index(drop=False)


def display_df(df: pd.DataFrame):
    df["percentage_of_mins_played"] = (df["percentage_of_mins_played"] * 100).map("{:.2f}%".format)

    output_cols = ["full_name", "expected_points_per_90", "actual_points_per_90", "percentage_of_mins_played", "now_cost", "team_name", "position"]
    print(tabulate(df[output_cols], headers='keys', tablefmt='psql'))


### END DEV WORK ###

if __name__ == "__main__":
    main()
