"""Performance tests for load handling."""

import time

import pandas as pd


class TestLargeDatasetHandling:
    """Tests for handling large datasets efficiently."""

    def test_large_history_dataframe_performance(self):
        """Test that large history dataframes are processed efficiently."""
        # Simulate large dataset (1000 players, 38 rounds each = 38,000 rows)
        n_players = 1000
        n_rounds = 38

        history_df = pd.DataFrame(
            {
                "element": [i % n_players + 1 for i in range(n_players * n_rounds)],
                "round": [i // n_players + 1 for i in range(n_players * n_rounds)],
                "minutes": [90] * (n_players * n_rounds),
                "total_points": [6] * (n_players * n_rounds),
                "expected_points": [6] * (n_players * n_rounds),
                "fixture_difficulty": [3] * (n_players * n_rounds),
                "finished": [True] * (n_players * n_rounds),
            }
        )

        # Measure aggregation performance
        start = time.time()
        grouped = history_df.groupby("element").agg(
            {
                "minutes": "sum",
                "total_points": "sum",
                "expected_points": "sum",
            }
        )
        elapsed = time.time() - start

        # Should complete in less than 1 second
        assert elapsed < 1.0, f"Aggregation took {elapsed}s, expected < 1s"

        # Verify result
        assert len(grouped) == n_players

    def test_large_player_dataframe_performance(self):
        """Test that large player dataframes are processed efficiently."""
        # Simulate 1000 players with many columns
        n_players = 1000

        players_df = pd.DataFrame(
            {
                "web_name": [f"Player{i}" for i in range(n_players)],
                "team": [i % 20 + 1 for i in range(n_players)],
                "position": ["DEF"] * 500 + ["MID"] * 500,
                "now_cost": [50] * n_players,
            },
            index=range(1, n_players + 1),
        )

        # Measure filtering performance
        start = time.time()
        filtered = players_df[players_df["position"] == "DEF"]
        elapsed = time.time() - start

        # Should complete in less than 0.1 seconds
        assert elapsed < 0.1, f"Filtering took {elapsed}s, expected < 0.1s"

        # Verify result
        assert len(filtered) == 500
