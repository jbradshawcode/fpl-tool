"""Pytest configuration and fixtures for FPL analysis tests."""

import pandas as pd
import pytest


@pytest.fixture
def sample_scoring():
    """Sample FPL scoring rules."""
    return {
        "goals_scored": {"GKP": 6, "DEF": 6, "MID": 5, "FWD": 4},
        "assists": 3,
        "clean_sheets": {"GKP": 4, "DEF": 4, "MID": 1, "FWD": 0},
        "goals_conceded": {"GKP": -1, "DEF": -1, "MID": 0, "FWD": 0},
        "yellow_cards": -1,
        "red_cards": -3,
        "saves": 1,
        "penalties_saved": 5,
        "penalties_missed": -2,
        "own_goals": -2,
        "bonus": 3,
        "long_play": 2,
        "short_play": 1,
    }


@pytest.fixture
def sample_parameters():
    """Sample parameters configuration."""
    return {
        "long_play_threshold": 60,
        "defcon_threshold": {"def": 10, "non_def": 12},
    }


@pytest.fixture
def sample_players_df():
    """Sample players dataframe."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "web_name": ["Player1", "Player2", "Player3", "Player4"],
            "position": ["Goalkeeper", "Defender", "Midfielder", "Forward"],
            "pos_abbr": ["GKP", "DEF", "MID", "FWD"],
            "team": [1, 1, 2, 2],
            "team_name": ["Arsenal", "Arsenal", "Chelsea", "Chelsea"],
            "now_cost": [50, 55, 75, 95],  # In 0.1 millions
            "element_type": [1, 2, 3, 4],
        }
    ).set_index("id")


@pytest.fixture
def sample_history_df():
    """Sample history dataframe with various match scenarios."""
    return pd.DataFrame(
        {
            "element": [1, 1, 2, 2, 3, 3, 4, 4],
            "round": [1, 2, 1, 2, 1, 2, 1, 2],
            "minutes": [90, 45, 90, 0, 60, 90, 90, 90],
            "total_points": [6, 2, 8, 0, 4, 7, 5, 6],
            "expected_goals": [0.1, 0.0, 0.2, 0.0, 0.3, 0.5, 0.8, 1.2],
            "expected_assists": [0.2, 0.1, 0.1, 0.0, 0.4, 0.3, 0.2, 0.1],
            "expected_goals_conceded": [1.5, 2.0, 1.2, 0.0, 2.5, 1.8, 0.5, 0.3],
            "defensive_contribution": [8, 5, 12, 0, 10, 15, 3, 4],
            "goals_scored": [0, 0, 1, 0, 0, 1, 1, 2],
            "assists": [1, 0, 0, 0, 1, 0, 0, 0],
            "clean_sheets": [0, 0, 1, 0, 0, 1, 1, 1],
            "goals_conceded": [2, 1, 0, 0, 1, 0, 0, 0],
            "yellow_cards": [0, 1, 0, 0, 1, 0, 0, 0],
            "red_cards": [0, 0, 0, 0, 0, 0, 0, 0],
            "saves": [3, 2, 0, 0, 0, 0, 0, 0],
            "penalties_saved": [0, 0, 0, 0, 0, 0, 0, 0],
            "penalties_missed": [0, 0, 0, 0, 0, 0, 0, 0],
            "own_goals": [0, 0, 0, 0, 0, 0, 0, 0],
            "bonus": [0, 0, 1, 0, 0, 0, 0, 3],
            "fixture_difficulty": [3, 4, 2, 3, 4, 3, 2, 2],
            "opponent_team_name": [
                "TeamA",
                "TeamB",
                "TeamC",
                "TeamD",
                "TeamE",
                "TeamF",
                "TeamG",
                "TeamH",
            ],
        }
    )


@pytest.fixture
def empty_history_df():
    """Empty history dataframe for edge case testing."""
    return pd.DataFrame()


@pytest.fixture
def minimal_history_df():
    """Minimal history with only required columns."""
    return pd.DataFrame(
        {
            "element": [1],
            "round": [1],
            "minutes": [90],
            "total_points": [2],
            "expected_goals": [0.0],
            "expected_assists": [0.0],
            "expected_goals_conceded": [2.0],
            "defensive_contribution": [5],
            "goals_scored": [0],
            "assists": [0],
            "clean_sheets": [0],
            "goals_conceded": [2],
            "yellow_cards": [0],
            "red_cards": [0],
            "saves": [0],
            "penalties_saved": [0],
            "penalties_missed": [0],
            "own_goals": [0],
            "bonus": [0],
            "fixture_difficulty": [3],
            "opponent_team_name": ["TeamA"],
        }
    )


@pytest.fixture
def players_for_pagination():
    """Players dataframe for pagination testing."""
    data = {
        "web_name": [f"Player{i}" for i in range(1, 26)],
        "now_cost": [50 + i * 2 for i in range(25)],
        "expected_points": [5.0 + i * 0.5 for i in range(25)],
        "team_name": ["Team" + str(i % 5) for i in range(25)],
        "pos_abbr": [
            "DEF" if i < 10 else "MID" if i < 20 else "FWD" for i in range(25)
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def players_for_filtering():
    """Players dataframe for filtering tests with edge cases."""
    return pd.DataFrame(
        {
            "web_name": ["Haaland", "Salah", "Saka", "White", "Raya"],
            "now_cost": [140, 125, 85, 55, 50],
            "expected_points": [6.5, 5.8, 4.2, 3.1, 3.8],
            "team_name": ["Man City", "Liverpool", "Arsenal", "Arsenal", "Arsenal"],
            "pos_abbr": ["FWD", "MID", "MID", "DEF", "GKP"],
        }
    )
