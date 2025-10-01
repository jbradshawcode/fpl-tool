import logging
import pandas as pd
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
    players_df["expected_points"] = history.aggregate_expected_points(history_df)

    # Rankings
    top_assisters = ranking.rank_players(players_df, metric="assists", mins_threshold=90)
    top_scorers = ranking.rank_players(players_df, metric="goals_scored", mins_threshold=90)
    logging.info(f"Top assisters:\n{top_assisters.head()}")
    logging.info(f"Top scorers:\n{top_scorers.head()}")

    print(history_df[['element', 'round', 'position', 'minutes', 'expected_points', 'total_points']].head())


if __name__ == "__main__":
    main()
