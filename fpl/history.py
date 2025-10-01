import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import Dict, List
from .api import fetch_data
from .config import SUPPORTED_HISTORY_METRICS


def fetch_player_history(element_id: int, team_map: Dict[int, str]) -> pd.DataFrame:
    """Fetch historical data for a single player."""
    data = fetch_data(f"element-summary/{element_id}/")
    if not data or "history" not in data:
        return pd.DataFrame()

    df = pd.DataFrame(data["history"])
    df["opponent_team_name"] = df["opponent_team"].map(team_map)
    return df[SUPPORTED_HISTORY_METRICS]


def fetch_all_histories(player_ids: List[int], team_map: Dict[int, str]) -> pd.DataFrame:
    """Fetch all players' histories in parallel."""
    all_histories = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch_player_history, pid, team_map): pid for pid in player_ids}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Fetching player histories"):
            df = future.result()
            if not df.empty:
                all_histories.append(df)

    if not all_histories:
        return pd.DataFrame()

    return (
        pd.concat(all_histories, ignore_index=True)
        .sort_values(by=["element", "round"])
        .reset_index(drop=True)
    )
