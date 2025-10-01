import logging
import pandas as pd
from fpl import api, preprocessing, ranking, history, config


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    # Fetch bootstrap data
    data = api.fetch_data("bootstrap-static/")
    if not data:
        logging.error("No data fetched from API")
        return

    # Preprocess players
    players_df = preprocessing.preprocess_players_df(
        pd.DataFrame(data["elements"]).set_index("id").sort_index()
    )
    teams_df = pd.DataFrame(data["teams"])
    positions_df = pd.DataFrame(data["element_types"])

    # Map team and position names
    team_map = teams_df.set_index("id")["name"]
    players_df["team_name"] = players_df["team"].map(team_map)
    positions_map = positions_df.set_index("id")["singular_name"]
    players_df["position"] = players_df["element_type"].map(positions_map)

    # Keep only supported metrics
    players_df = players_df[config.SUPPORTED_METRICS]

    # Fetch and save history
    history_df = history.fetch_all_histories(players_df.index.tolist(), team_map)
    if not history_df.empty:
        history_df.to_csv("player_histories.csv", index=False)
        logging.info("Saved player histories to player_histories.csv")
    else:
        logging.warning("No player history data available")

    # Example: rank players by assists
    top_assisters = ranking.rank_players(players_df, metric="assists", mins_threshold=90)
    logging.info(f"Top assisters:\n{top_assisters.head()}")


if __name__ == "__main__":
    main()
