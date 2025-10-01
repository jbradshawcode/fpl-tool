import pandas as pd


def rank_players(df: pd.DataFrame, metric: str, mins_threshold: int,
                 ascending: bool = False) -> pd.DataFrame:
    """
    Rank players by a metric with filtering and tie-breaking on price.
    """
    return (
        df[df["minutes"] > mins_threshold]
        .sort_values(by=[metric, "now_cost"], ascending=[ascending, True])
    )
