"""Tests for history module scoring calculations."""

import pandas as pd

from domain.history import (
    calculate_expected_points,
    _calculate_play_points,
    _calculate_attack_points,
    _calculate_clean_sheet_points,
    _calculate_gc_penalty_points,
    _calculate_defensive_points,
    _calculate_event_points,
    _calculate_per_90_metrics,
    _add_position_info,
)


class TestAddPositionInfo:
    """Tests for position mapping functionality."""

    def test_adds_position_and_pos_abbr(self, sample_history_df, sample_players_df):
        """Should add position and pos_abbr columns correctly."""
        result = _add_position_info(sample_history_df.copy(), sample_players_df)

        assert "position" in result.columns
        assert "pos_abbr" in result.columns
        assert result[result["element"] == 1]["position"].iloc[0] == "Goalkeeper"
        assert result[result["element"] == 1]["pos_abbr"].iloc[0] == "GKP"
        assert result[result["element"] == 4]["pos_abbr"].iloc[0] == "FWD"

    def test_handles_missing_elements(self, sample_players_df):
        """Should handle elements not in players_df."""
        history = pd.DataFrame({"element": [999]})
        result = _add_position_info(history, sample_players_df)

        assert pd.isna(result["position"].iloc[0])
        assert pd.isna(result["pos_abbr"].iloc[0])


class TestCalculatePlayPoints:
    """Tests for play points (appearance) calculations."""

    def test_long_play_points(self, sample_parameters, sample_scoring):
        """Should award long play points for >= 60 minutes."""
        history = pd.DataFrame({"minutes": [60, 90, 120]})
        result = _calculate_play_points(history, sample_parameters, sample_scoring)

        assert (result == sample_scoring["long_play"]).all()

    def test_short_play_points(self, sample_parameters, sample_scoring):
        """Should award short play points for 1-59 minutes."""
        history = pd.DataFrame({"minutes": [1, 30, 59]})
        result = _calculate_play_points(history, sample_parameters, sample_scoring)

        assert (result == sample_scoring["short_play"]).all()

    def test_zero_minutes_no_points(self, sample_parameters, sample_scoring):
        """Should award 0 points for 0 minutes."""
        history = pd.DataFrame({"minutes": [0]})
        result = _calculate_play_points(history, sample_parameters, sample_scoring)

        assert (result == 0).all()


class TestCalculateAttackPoints:
    """Tests for attack points (goals + assists) calculations."""

    def test_goal_points_by_position(self, sample_scoring):
        """Should calculate correct points based on position and xG."""
        history = pd.DataFrame(
            {
                "expected_goals": [1.0, 1.0, 1.0, 1.0],
                "expected_assists": [0.0, 0.0, 0.0, 0.0],
                "pos_abbr": ["GKP", "DEF", "MID", "FWD"],
            }
        )
        result = _calculate_attack_points(history, sample_scoring)

        assert result.iloc[0] == 6.0  # GKP: 1.0 * 6
        assert result.iloc[1] == 6.0  # DEF: 1.0 * 6
        assert result.iloc[2] == 5.0  # MID: 1.0 * 5
        assert result.iloc[3] == 4.0  # FWD: 1.0 * 4

    def test_assist_points(self, sample_scoring):
        """Should add assist points correctly."""
        history = pd.DataFrame(
            {
                "expected_goals": [0.0],
                "expected_assists": [2.0],
                "pos_abbr": ["MID"],
            }
        )
        result = _calculate_attack_points(history, sample_scoring)

        assert result.iloc[0] == 6.0  # 2.0 * 3


class TestCalculateCleanSheetPoints:
    """Tests for clean sheet probability calculations."""

    def test_clean_sheet_probability_threshold(self, sample_parameters, sample_scoring):
        """Should only calculate for players with >= 60 minutes."""
        history = pd.DataFrame(
            {
                "minutes": [60, 59, 90],
                "expected_goals_conceded": [0.5, 0.5, 1.0],
                "pos_abbr": ["DEF", "DEF", "DEF"],
            }
        )
        result = _calculate_clean_sheet_points(
            history, sample_parameters, sample_scoring
        )

        # exp(-0.5) * 4 for >= 60 mins, 0 for < 60
        assert result.iloc[0] > 0
        assert result.iloc[1] == 0
        assert result.iloc[2] > 0

    def test_position_based_clean_sheet_points(self, sample_parameters, sample_scoring):
        """Should use position-specific clean sheet values."""
        history = pd.DataFrame(
            {
                "minutes": [90, 90, 90, 90],
                "expected_goals_conceded": [0.0, 0.0, 0.0, 0.0],  # exp(0) = 1
                "pos_abbr": ["GKP", "DEF", "MID", "FWD"],
            }
        )
        result = _calculate_clean_sheet_points(
            history, sample_parameters, sample_scoring
        )

        assert result.iloc[0] == 4.0  # GKP: 4 * 1
        assert result.iloc[1] == 4.0  # DEF: 4 * 1
        assert result.iloc[2] == 1.0  # MID: 1 * 1
        assert result.iloc[3] == 0.0  # FWD: 0 * 1


class TestCalculateGCPenaltyPoints:
    """Tests for goals conceded penalty calculations."""

    def test_gc_penalty_linear_mapping(self, sample_parameters, sample_scoring):
        """Should calculate -0.5 points per xGC."""
        history = pd.DataFrame(
            {
                "minutes": [90],
                "expected_goals_conceded": [2.0],
                "pos_abbr": ["DEF"],
            }
        )
        result = _calculate_gc_penalty_points(
            history, sample_parameters, sample_scoring
        )

        # 2.0 xGC * (-1) / 2 = -1.0
        assert result[0] == -1.0

    def test_no_penalty_for_short_play(self, sample_parameters, sample_scoring):
        """Should not penalize players with < 60 minutes."""
        history = pd.DataFrame(
            {
                "minutes": [30],
                "expected_goals_conceded": [3.0],
                "pos_abbr": ["DEF"],
            }
        )
        result = _calculate_gc_penalty_points(
            history, sample_parameters, sample_scoring
        )

        assert result[0] == 0


class TestCalculateDefensivePoints:
    """Tests for defensive contribution bonus."""

    def test_defender_threshold_bonus(self, sample_parameters):
        """Should award bonus to defenders meeting threshold."""
        history = pd.DataFrame(
            {
                "defensive_contribution": [10, 9, 15],
                "pos_abbr": ["DEF", "DEF", "DEF"],
            }
        )
        result = _calculate_defensive_points(history, sample_parameters)

        assert result[0] == 2  # At threshold
        assert result[1] == 0  # Below threshold
        assert result[2] == 2  # Above threshold

    def test_non_defender_threshold(self, sample_parameters):
        """Should use higher threshold for non-defenders."""
        history = pd.DataFrame(
            {
                "defensive_contribution": [11, 12, 13],
                "pos_abbr": ["MID", "MID", "MID"],
            }
        )
        result = _calculate_defensive_points(history, sample_parameters)

        assert result[0] == 0  # Below 12
        assert result[1] == 2  # At 12
        assert result[2] == 2  # Above 12


class TestCalculateEventPoints:
    """Tests for event-based points (cards, saves, etc.)."""

    def test_yellow_card_penalty(self, sample_scoring):
        """Should subtract points for yellow cards."""
        history = pd.DataFrame(
            {
                "yellow_cards": [1],
                "red_cards": [0],
                "saves": [0],
                "penalties_saved": [0],
                "penalties_missed": [0],
                "own_goals": [0],
                "bonus": [0],
            }
        )
        result = _calculate_event_points(history, sample_scoring)

        assert result.iloc[0] == -1

    def test_saves_points_calculation(self, sample_scoring):
        """Should award 1 point per 3 saves."""
        history = pd.DataFrame(
            {
                "yellow_cards": [0],
                "red_cards": [0],
                "saves": [7],  # 7 // 3 = 2
                "penalties_saved": [0],
                "penalties_missed": [0],
                "own_goals": [0],
                "bonus": [0],
            }
        )
        result = _calculate_event_points(history, sample_scoring)

        assert result.iloc[0] == 2  # 7 // 3 = 2 points

    def test_multiple_events(self, sample_scoring):
        """Should handle multiple events correctly."""
        history = pd.DataFrame(
            {
                "yellow_cards": [1],
                "red_cards": [0],
                "saves": [3],
                "penalties_saved": [1],
                "penalties_missed": [0],
                "own_goals": [0],
                "bonus": [2],
            }
        )
        result = _calculate_event_points(history, sample_scoring)
        # -1 + 1 + 5 + 6 = 11
        expected = -1 + 1 + 5 + 6
        assert result.iloc[0] == expected


class TestCalculatePer90Metrics:
    """Tests for per-90 metrics calculations."""

    def test_expected_points_per_90_calculation(self):
        """Should calculate expected points per 90 correctly."""
        history = pd.DataFrame(
            {
                "expected_points": [4.5],
                "total_points": [6],
                "minutes": [90],
                "red_cards": [0],
            }
        )
        result = _calculate_per_90_metrics(history)

        assert result["expected_points_per_90"].iloc[0] == 4.5
        assert result["actual_points_per_90"].iloc[0] == 6.0
        assert result["percentage_of_mins_played"].iloc[0] == 1.0

    def test_handles_zero_minutes(self):
        """Should handle zero minutes gracefully."""
        history = pd.DataFrame(
            {
                "expected_points": [0],
                "total_points": [0],
                "minutes": [0],
                "red_cards": [0],
            }
        )
        result = _calculate_per_90_metrics(history)

        assert result["expected_points_per_90"].iloc[0] == 0
        assert result["actual_points_per_90"].iloc[0] == 0

    def test_red_card_handling(self):
        """Should handle red cards correctly in per 90 calc."""
        history = pd.DataFrame(
            {
                "expected_points": [3],
                "total_points": [2],
                "minutes": [30],
                "red_cards": [1],
            }
        )
        result = _calculate_per_90_metrics(history)

        # With red card, should return raw points, not per 90
        assert result["expected_points_per_90"].iloc[0] == 3
        assert result["actual_points_per_90"].iloc[0] == 2


class TestCalculateExpectedPoints:
    """Integration tests for full expected points calculation."""

    def test_full_calculation(
        self, sample_history_df, sample_players_df, sample_scoring
    ):
        """Should calculate expected points for all players."""
        result = calculate_expected_points(
            sample_history_df, sample_players_df, sample_scoring
        )

        assert "expected_points" in result.columns
        assert "expected_points_per_90" in result.columns
        assert "actual_points_per_90" in result.columns
        assert "percentage_of_mins_played" in result.columns
        assert "position" in result.columns
        assert "pos_abbr" in result.columns

        # Check no NaN in expected_points
        assert not result["expected_points"].isna().any()

    def test_empty_dataframe(self, sample_players_df, sample_scoring):
        """Should handle empty dataframe gracefully."""
        empty_df = pd.DataFrame()
        result = calculate_expected_points(empty_df, sample_players_df, sample_scoring)

        assert result.empty

    def test_defender_calculation(self, sample_parameters, sample_scoring):
        """Test specific defender scenario."""
        history = pd.DataFrame(
            {
                "element": [2],
                "round": [1],
                "minutes": [90],
                "total_points": [6],
                "expected_goals": [0.1],
                "expected_assists": [0.1],
                "expected_goals_conceded": [0.5],
                "defensive_contribution": [12],
                "goals_scored": [0],
                "assists": [0],
                "clean_sheets": [1],
                "goals_conceded": [0],
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
        players = pd.DataFrame(
            {
                "position": ["Defender"],
                "pos_abbr": ["DEF"],
            },
            index=[2],
        )

        result = calculate_expected_points(history, players, sample_scoring)

        # Should have clean sheet points, defensive bonus, play points
        assert result["expected_points"].iloc[0] > 0
        # 2 (long play) + ~2.43 (clean sheet) + 0.6 (attack) + 2 (def bonus) - 0.25 (GC penalty)
