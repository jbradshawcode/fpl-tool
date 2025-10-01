import logging
import pandas as pd
from fpl import api, preprocessing, ranking, history, config
from utils.update_guard import should_update, mark_updated

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_bootstrap_data():
    """Fetch and return raw bootstrap data from FPL API."""
    data = api.fetch_data("bootstrap-static/")
    if not data:
        logging.error("No data fetched from API")
        return None
    return data


def build_players_df(data: dict) -> pd.DataFrame:
    """Preprocess player data, map teams/positions, and filter metrics."""
    players_df = preprocessing.preprocess_players_df(
        pd.DataFrame(data["elements"]).set_index("id").sort_index()
    )

    teams_df = pd.DataFrame(data["teams"])
    positions_df = pd.DataFrame(data["element_types"])

    # Maps
    team_map = teams_df.set_index("id")["name"]
    players_df["team_name"] = players_df["team"].map(team_map)

    positions_map = positions_df.set_index("id")["singular_name"]
    players_df["position"] = players_df["element_type"].map(positions_map)

    # Keep only supported metrics
    players_df = players_df[config.SUPPORTED_METRICS]

    return players_df, team_map


def update_history(players_df: pd.DataFrame, team_map: dict) -> None:
    """Fetch and save player histories if not updated today."""
    if not should_update():
        logging.info("Skipping history update (already updated today)")
        return

    history_df = history.fetch_all_histories(players_df.index.tolist(), team_map)
    if not history_df.empty:
        history_df.to_csv("player_histories.csv", index=False)
        mark_updated()
        logging.info("Saved player histories to player_histories.csv")
    else:
        logging.warning("No player history data available")


def run_rankings(players_df: pd.DataFrame) -> None:
    """Run and log example rankings."""
    top_assisters = ranking.rank_players(players_df, metric="assists", mins_threshold=90)
    logging.info(f"Top assisters:\n{top_assisters.head()}")

    # Example extra ranking
    top_scorers = ranking.rank_players(players_df, metric="goals_scored", mins_threshold=90)
    logging.info(f"Top scorers:\n{top_scorers.head()}")


def main():
    data = load_bootstrap_data()
    if not data:
        return

    players_df, team_map = build_players_df(data)

    update_history(players_df, team_map)
    run_rankings(players_df)

if __name__ == "__main__":
    main()
