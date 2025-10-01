import pandas as pd


def preprocess_players_df(df: pd.DataFrame) -> pd.DataFrame:
    """Clean up player dataframe: add full name, adjust cost."""
    df["full_name"] = df["first_name"] + " " + df["second_name"]
    df["now_cost"] = df["now_cost"] / 10  # convert to millions
    return df.drop(columns=["first_name", "second_name"])
