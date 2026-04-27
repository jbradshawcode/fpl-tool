"""Integration tests for the full data pipeline."""

import json
import os
import tempfile
from unittest.mock import patch

import pandas as pd
from infrastructure import update_guard


class TestSaveLoadCycle:
    """Integration tests for save/load cycle."""

    def test_save_load_cycle(self):
        """Test that data can be saved and loaded correctly."""
        # Create test data
        players_df = pd.DataFrame(
            {
                "web_name": ["Test Player"],
                "team": [1],
            },
            index=[1],
        )

        history_df = pd.DataFrame(
            {
                "element": [1],
                "round": [30],
                "minutes": [90],
                "total_points": [6],
                "expected_points": [6],
                "fixture_difficulty": 3,
                "finished": True,
            }
        )

        fdr_df = pd.DataFrame(
            {
                "round": [30],
                "team_id": [1],
                "opponent_id": [2],
                "fixture_difficulty": [3],
                "was_home": [True],
            }
        )

        scoring = {"bps": 3}

        data = {
            "players_df": players_df,
            "history_df": history_df,
            "fdr_df": fdr_df,
            "scoring": scoring,
        }

        # Use temporary directory to avoid messing with user's data
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = tmpdir

            data["players_df"].to_csv(
                f"{data_dir}/players_data.csv", index=True, index_label="id"
            )
            data["history_df"].to_csv(f"{data_dir}/player_histories.csv", index=False)
            data["fdr_df"].to_csv(
                f"{data_dir}/fixture_difficulty_ratings.csv", index=False
            )

            with open(f"{data_dir}/scoring.json", "w") as f:
                json.dump(data["scoring"], f, indent=4)

            # Verify files exist
            assert os.path.exists(f"{data_dir}/players_data.csv")
            assert os.path.exists(f"{data_dir}/player_histories.csv")
            assert os.path.exists(f"{data_dir}/fixture_difficulty_ratings.csv")
            assert os.path.exists(f"{data_dir}/scoring.json")

            # Load data back
            loaded_players = pd.read_csv(f"{data_dir}/players_data.csv", index_col="id")
            loaded_history = pd.read_csv(f"{data_dir}/player_histories.csv")
            loaded_fdr = pd.read_csv(f"{data_dir}/fixture_difficulty_ratings.csv")

            # Verify data integrity
            assert len(loaded_players) == len(players_df)
            assert len(loaded_history) == len(history_df)
            assert len(loaded_fdr) == len(fdr_df)

            # Verify column presence
            assert "finished" in loaded_history.columns
            assert "fixture_difficulty" in loaded_history.columns


class TestUpdateGuard:
    """Integration tests for update guard logic."""

    def test_update_guard_prevents_unnecessary_updates(self):
        """Test that update guard prevents unnecessary API calls."""
        # Use temp directory for test
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = f"{tmpdir}/last_update.txt"

            # Mock the STAMP_FILE constant
            with patch.object(update_guard, "STAMP_FILE", test_file):
                # Mark as updated
                update_guard.mark_updated()

                # Should not need update immediately
                assert not update_guard.should_update()

                # Force update by removing last_update file
                if os.path.exists(test_file):
                    os.remove(test_file)

                # Should need update now
                assert update_guard.should_update()
