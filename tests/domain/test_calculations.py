"""Tests for domain calculations module."""

import numpy as np
import pandas as pd
import pytest

from domain.calculations import (
    build_difficulty_lookup,
    _filter_by_time_period,
    _filter_by_position,
    _ensure_numeric_dtypes,
    _aggregate_player_stats,
    _apply_horizon_scaling,
    _apply_minutes_filter,
    expected_points_per_90,
)


class TestBuildDifficultyLookup:
    """Tests for difficulty factor calculation."""

    def test_builds_lookup_correctly(self):
        """Should build lookup from mean expected points per difficulty."""
        history = pd.DataFrame(
            {
                "fixture_difficulty": [1, 2, 3, 3, 4, 5],
                "expected_points": [10.0, 8.0, 6.0, 6.0, 4.0, 2.0],
            }
        )
        xp, yp = build_difficulty_lookup(history)

        # Check normalized at difficulty 3 = 1.0
        assert len(xp) == 5  # Difficulties 1-5
        assert 3 in xp
        idx_3 = np.where(xp == 3)[0][0]
        assert yp[idx_3] == 1.0

    def test_handles_empty_difficulty(self):
        """Should handle edge cases in difficulty calculation."""
        history = pd.DataFrame(
            {
                "fixture_difficulty": [3],
                "expected_points": [6.0],
            }
        )
        xp, yp = build_difficulty_lookup(history)

        assert len(xp) == 1
        assert xp[0] == 3
        assert yp[0] == 1.0  # Normalized to self


class TestFilterByTimePeriod:
    """Tests for time period filtering."""

    def test_filters_recent_rounds(self):
        """Should return only recent rounds."""
        history = pd.DataFrame(
            {
                "round": list(range(1, 11)),  # 1-10
                "data": range(10),
            }
        )
        result = _filter_by_time_period(history, time_period=3)

        assert len(result) == 3
        assert result["round"].min() == 8
        assert result["round"].max() == 10

    def test_returns_all_when_no_time_period(self):
        """Should return all data when time_period is None."""
        history = pd.DataFrame(
            {
                "round": list(range(1, 11)),
                "data": range(10),
            }
        )
        result = _filter_by_time_period(history, None)

        assert len(result) == 10


class TestFilterByPosition:
    """Tests for position filtering."""

    def test_filters_by_position(self):
        """Should return only matching position."""
        history = pd.DataFrame(
            {
                "pos_abbr": ["GKP", "DEF", "MID", "FWD", "DEF"],
            }
        )
        result = _filter_by_position(history, "DEF")

        assert len(result) == 2
        assert all(result["pos_abbr"] == "DEF")

    def test_returns_all_when_no_position(self):
        """Should return all when position is None."""
        history = pd.DataFrame(
            {
                "pos_abbr": ["GKP", "DEF", "MID", "FWD"],
            }
        )
        result = _filter_by_position(history, None)

        assert len(result) == 4


class TestEnsureNumericDtypes:
    """Tests for numeric type conversion."""

    def test_converts_object_columns(self):
        """Should convert object columns to numeric."""
        history = pd.DataFrame(
            {
                "minutes": ["90", "45", "0"],
                "expected_points": ["5.5", "3.2", "0.0"],
                "total_points": ["6", "2", "0"],
                "fixture_difficulty": ["3", "4", "5"],
                "other_col": ["text", "text", "text"],  # Should remain
            }
        )
        result = _ensure_numeric_dtypes(history)

        assert pd.api.types.is_numeric_dtype(result["minutes"])
        assert pd.api.types.is_numeric_dtype(result["expected_points"])
        assert result["minutes"].iloc[0] == 90


class TestAggregatePlayerStats:
    """Tests for player stats aggregation."""

    def test_aggregates_by_element(self):
        """Should aggregate stats correctly per player."""
        history = pd.DataFrame(
            {
                "element": [1, 1, 2, 2],
                "round": [1, 2, 1, 2],
                "opponent_team_name": ["A", "B", "C", "D"],
                "minutes": [90, 45, 60, 90],
                "expected_points": [5.0, 3.0, 4.0, 6.0],
                "total_points": [6, 2, 4, 8],
                "fixture_difficulty": [3, 4, 2, 3],
            }
        )
        result = _aggregate_player_stats(history)

        assert len(result) == 2
        assert result.loc[1, "total_minutes"] == 135  # 90 + 45
        assert result.loc[1, "total_expected_points"] == 8.0  # 5.0 + 3.0
        assert result.loc[2, "total_actual_points"] == 12  # 4 + 8


class TestApplyHorizonScaling:
    """Tests for horizon difficulty scaling."""

    def test_applies_scaling_when_enabled(self, sample_players_df):
        """Should apply horizon factor when fdr_df and horizon provided."""
        grouped = pd.DataFrame(
            {
                "avg_fixture_difficulty": [3.0, 4.0, 2.0],
            },
            index=[1, 2, 3],
        )

        fdr_df = pd.DataFrame(
            {
                "round": [6, 6, 7, 7],
                "team_id": [1, 1, 1, 1],
                "fixture_difficulty": [3, 4, 3, 2],
            }
        )

        xp = np.array([1, 2, 3, 4, 5])
        yp = np.array([1.5, 1.2, 1.0, 0.8, 0.5])

        result = _apply_horizon_scaling(
            grouped, sample_players_df, fdr_df, horizon=2, latest_round=5, xp=xp, yp=yp
        )

        assert "horizon_factor" in result.columns
        assert "scale" in result.columns
        assert not result["scale"].isna().any()

    def test_no_scaling_when_disabled(self, sample_players_df):
        """Should set scale=1.0 when scaling disabled."""
        grouped = pd.DataFrame(
            {
                "avg_fixture_difficulty": [3.0],
            },
            index=[1],
        )

        xp = np.array([1, 2, 3, 4, 5])
        yp = np.array([1.5, 1.2, 1.0, 0.8, 0.5])

        result = _apply_horizon_scaling(
            grouped,
            sample_players_df,
            fdr_df=None,
            horizon=None,
            latest_round=5,
            xp=xp,
            yp=yp,
        )

        assert result["scale"].iloc[0] == 1.0


class TestApplyMinutesFilter:
    """Tests for minutes threshold filtering."""

    def test_filters_by_percentage(self):
        """Should filter by percentage of minutes played."""
        grouped = pd.DataFrame(
            {
                "percentage_of_mins_played": [0.8, 0.5, 0.9, 0.3],
                "other": [1, 2, 3, 4],
            }
        )
        result = _apply_minutes_filter(grouped, mins_threshold=0.7)

        assert len(result) == 2
        assert all(result["percentage_of_mins_played"] >= 0.7)

    def test_no_filter_when_none(self):
        """Should return all when threshold is None."""
        grouped = pd.DataFrame(
            {
                "percentage_of_mins_played": [0.5, 0.3],
            }
        )
        result = _apply_minutes_filter(grouped, None)

        assert len(result) == 2


class TestExpectedPointsPer90:
    """Integration tests for expected points calculation."""

    def test_full_calculation(self, sample_players_df, processed_history_df):
        """Should calculate expected points per 90 for all players."""
        # Add pos_abbr to history
        processed_history_df["pos_abbr"] = [
            "GKP",
            "GKP",
            "DEF",
            "DEF",
            "MID",
            "MID",
            "FWD",
            "FWD",
        ]

        result = expected_points_per_90(
            processed_history_df,
            sample_players_df,
            position=None,  # All positions
            mins_threshold=None,
            time_period=None,
        )

        assert "expected_points_per_90" in result.columns
        assert "actual_points_per_90" in result.columns
        assert "expected_points" in result.columns
        assert not result.empty

    def test_position_filter(self, sample_players_df, processed_history_df):
        """Should filter by position correctly."""
        processed_history_df["pos_abbr"] = [
            "GKP",
            "GKP",
            "DEF",
            "DEF",
            "MID",
            "MID",
            "FWD",
            "FWD",
        ]

        result = expected_points_per_90(
            processed_history_df,
            sample_players_df,
            position="FWD",
        )

        assert len(result) == 1  # Only element 4 (Forward)

    def test_empty_history(self, sample_players_df):
        """Should raise error on empty history dataframe."""
        empty_history = pd.DataFrame()
        with pytest.raises((ValueError, KeyError, IndexError)):
            expected_points_per_90(empty_history, sample_players_df)


class TestFixtureFiltering:
    """Tests for fixture finished status filtering."""

    def test_double_gameweek_both_finished(self):
        """Should count both fixtures in double gameweek when both finished."""
        from domain.calculations import _calculate_per_90_stats

        # Player with double gameweek in round 30, both finished
        history_df = pd.DataFrame(
            {
                "element": [1, 1, 1, 1],
                "round": [30, 30, 31, 32],
                "minutes": [90, 90, 90, 90],
                "total_points": [6, 6, 6, 6],
                "finished": [True, True, True, True],
            }
        )

        grouped = pd.DataFrame(
            {
                "element": [1],
                "total_minutes": [360],
                "total_actual_points": [24],
                "total_expected_points": [24],
                "scale": [1.0],
            }
        ).set_index("element")

        result = _calculate_per_90_stats(grouped, history_df)

        assert result.loc[1, "percentage_of_mins_played"] == 1.0  # 360 / (4 * 90)

    def test_double_gameweek_one_finished(self):
        """Should only count finished fixture when one of two is not finished."""
        from domain.calculations import _calculate_per_90_stats

        # Player with double gameweek in round 30, one finished one not
        history_df = pd.DataFrame(
            {
                "element": [1, 1, 1, 1],
                "round": [30, 30, 31, 32],
                "minutes": [90, 90, 90, 90],
                "total_points": [6, 6, 6, 6],
                "finished": [True, False, True, True],
            }
        )

        grouped = pd.DataFrame(
            {
                "element": [1],
                "total_minutes": [360],
                "total_actual_points": [24],
                "total_expected_points": [24],
                "scale": [1.0],
            }
        ).set_index("element")

        result = _calculate_per_90_stats(grouped, history_df)

        assert result.loc[1, "percentage_of_mins_played"] == 1.0  # 270 / (3 * 90)

    def test_blank_gameweek(self):
        """Should handle blank gameweek (no fixture in a round)."""
        from domain.calculations import _calculate_per_90_stats

        # Player with no fixture in round 31 (blank gameweek)
        history_df = pd.DataFrame(
            {
                "element": [1, 1, 1],
                "round": [30, 32, 33],
                "minutes": [90, 90, 90],
                "total_points": [6, 6, 6],
                "finished": [True, True, True],
            }
        )

        grouped = pd.DataFrame(
            {
                "element": [1],
                "total_minutes": [270],
                "total_actual_points": [18],
                "total_expected_points": [18],
                "scale": [1.0],
            }
        ).set_index("element")

        result = _calculate_per_90_stats(grouped, history_df)

        assert result.loc[1, "percentage_of_mins_played"] == 1.0  # 270 / (3 * 90)

    def test_games_not_started(self):
        """Should exclude games not started (finished=False) from calculation."""
        from domain.calculations import _calculate_per_90_stats

        # Player with 5 fixtures, but round 34 not started
        history_df = pd.DataFrame(
            {
                "element": [1, 1, 1, 1, 1],
                "round": [30, 31, 32, 33, 34],
                "minutes": [90, 90, 90, 90, 0],
                "total_points": [6, 6, 6, 6, 0],
                "finished": [True, True, True, True, False],
            }
        )

        grouped = pd.DataFrame(
            {
                "element": [1],
                "total_minutes": [360],
                "total_actual_points": [24],
                "total_expected_points": [24],
                "scale": [1.0],
            }
        ).set_index("element")

        result = _calculate_per_90_stats(grouped, history_df)

        assert result.loc[1, "percentage_of_mins_played"] == 1.0  # 360 / (4 * 90)

    def test_fallback_without_finished_column(self):
        """Should fall back to all fixtures when finished column is missing."""
        from domain.calculations import _calculate_per_90_stats

        # History without finished column (old data)
        history_df = pd.DataFrame(
            {
                "element": [1, 1, 1, 1],
                "round": [30, 31, 32, 33],
                "minutes": [90, 90, 90, 90],
                "total_points": [6, 6, 6, 6],
            }
        )

        grouped = pd.DataFrame(
            {
                "element": [1],
                "total_minutes": [360],
                "total_actual_points": [24],
                "total_expected_points": [24],
                "scale": [1.0],
            }
        ).set_index("element")

        result = _calculate_per_90_stats(grouped, history_df)

        assert result.loc[1, "percentage_of_mins_played"] == 1.0  # 360 / (4 * 90)

    def test_all_fixtures_unfinished(self):
        """Should handle case where all fixtures are unfinished gracefully."""
        from domain.calculations import _calculate_per_90_stats

        # All fixtures not finished
        history_df = pd.DataFrame(
            {
                "element": [1, 1],
                "round": [30, 31],
                "minutes": [0, 0],
                "total_points": [0, 0],
                "finished": [False, False],
            }
        )

        grouped = pd.DataFrame(
            {
                "element": [1],
                "total_minutes": [0],
                "total_actual_points": [0],
                "total_expected_points": [0],
                "scale": [1.0],
            }
        ).set_index("element")

        result = _calculate_per_90_stats(grouped, history_df)

        # Should not crash, percentage should be 0
        assert result.loc[1, "percentage_of_mins_played"] == 0.0
