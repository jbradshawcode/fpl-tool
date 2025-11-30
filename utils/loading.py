import json
import logging

from fpl import api, history, preprocessing


def initialise_data(endpoint: str) -> None:
    data = fetch_data(endpoint=endpoint)
    save_data(data=data)

    return data


def fetch_data(endpoint: str) -> dict:
    # Fetch static data
    logging.info("Fetching static data...")
    data = api.fetch_data(endpoint=endpoint)

    # Build data structures
    logging.info("Building players dataframe...")
    players_df, team_map = preprocessing.build_players_df(data)

    logging.info("Fetching player histories...")
    history_df = history.fetch_all_histories(players_df.index.tolist(), team_map)

    scoring = data["game_config"]["scoring"]

    return {"players_df": players_df, "history_df": history_df, "scoring": scoring}


def save_data(data: dict) -> None:
    data["players_df"].to_csv("data/players_data.csv", index=False)
    data["history_df"].to_csv("data/player_histories.csv", index=False)

    with open("data/scoring.json", "w") as f:
        json.dump(data["scoring"], f, indent=4)
