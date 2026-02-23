"""Configuration constants for Fantasy Premier League data processing.

This module defines:
- The base API URL
- Columns and metrics for player profiles
- Metrics supported for ranking and historical analysis
"""

# Base URL for FPL API
BASE_URL = "https://fantasy.premierleague.com/api/"

# Bootstrap Static Endpoint
BOOTSTRAP_STATIC_ENDPOINT = "bootstrap-static/"

# Display Columns
DISPLAY_COLS = [
    "web_name",
    "expected_points",
    "actual_points",
    "expected_points_per_90",
    "actual_points_per_90",
    "percentage_of_mins_played",
    "now_cost",
    "team_name",
]

# Display Mapping
DISPLAY_MAPPING = {
    "web_name": "Player",
    "expected_points": "xPoints",
    "actual_points": "Points",
    "expected_points_per_90": "xPoints\n/90",
    "actual_points_per_90": "Points\n/90",
    "percentage_of_mins_played": "% of Mins\nPlayed",
    "now_cost": "Cost",
    "team_name": "Team",
}

# Positions Mapping
POS_MAP = {
    "Goalkeeper": "GKP",
    "Defender": "DEF",
    "Midfielder": "MID",
    "Forward": "FWD",
}

# Columns for player profiles
PROFILE_COLS = [
    "web_name",
    "team_name",
    "position",
    "now_cost",
]

# Supported metrics for ranking/analysis
SUPPORTED_METRICS = [
    "assists",
    "bonus",
    "bps",
    "clean_sheets",
    "clean_sheets_per_90",
    "clearances_blocks_interceptions",
    "defensive_contribution",
    "defensive_contribution_per_90",
    "expected_assists",
    "expected_assists_per_90",
    "expected_goal_involvements",
    "expected_goal_involvements_per_90",
    "expected_goals",
    "expected_goals_conceded",
    "expected_goals_conceded_per_90",
    "expected_goals_per_90",
    "form",
    "web_name",
    "goals_conceded",
    "goals_conceded_per_90",
    "goals_scored",
    "minutes",
    "now_cost",
    "own_goals",
    "penalties_missed",
    "penalties_saved",
    "position",
    "recoveries",
    "red_cards",
    "saves",
    "selected_by_percent",
    "starts_per_90",
    "tackles",
    "team",
    "team_name",
    "total_points",
    "transfers_in",
    "transfers_out",
    "yellow_cards",
]

# Metrics supported for history
SUPPORTED_HISTORY_METRICS = [
    "element",
    "opponent_team_name",
    "total_points",
    "round",
    "minutes",
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "own_goals",
    "penalties_saved",
    "penalties_missed",
    "yellow_cards",
    "red_cards",
    "saves",
    "bonus",
    "bps",
    "clearances_blocks_interceptions",
    "recoveries",
    "tackles",
    "defensive_contribution",
    "starts",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
    "fixture_difficulty",
]
