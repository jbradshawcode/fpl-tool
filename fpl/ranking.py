import pandas as pd


def rank_players(df: pd.DataFrame, metric: str, mins_threshold: int,
                 ascending: bool = False) -> pd.DataFrame:
    """
    Rank players by a metric with filtering and tie-breaking on price.

    :param df: DataFrame with player data
    :param metric: Column name to rank by
    :param mins_threshold: Minimum minutes played
    :param ascending: Whether to sort ascending (default False for descending)
    :return: Ranked DataFrame
    """
    return (
        df[df["minutes"] > mins_threshold]
        .sort_values(by=[metric, "now_cost"], ascending=[ascending, True])
    )
