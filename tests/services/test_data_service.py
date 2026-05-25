"""Tests for data service — season detection, archiving, concatenation, and new-player logic."""

import pandas as pd

from services.data_service import (
    _is_season_complete,
    _get_season_name,
    _try_archive_season,
    _concatenate_archived_history,
    _detect_new_to_league,
    _get_archived_seasons,
    has_archived_data,
)


def _make_events(finished_flags, data_checked_flags, start_year=2024):
    """Build a minimal bootstrap events list for testing."""
    events = []
    for i, (fin, chk) in enumerate(zip(finished_flags, data_checked_flags), start=1):
        events.append(
            {
                "id": i,
                "finished": fin,
                "data_checked": chk,
                "deadline_time": f"{start_year}-08-{i:02d}T11:00:00Z",
            }
        )
    return events


class TestIsSeasonComplete:
    """Tests for _is_season_complete."""

    def test_all_finished_and_checked(self):
        bootstrap = {"events": _make_events([True] * 38, [True] * 38)}
        assert _is_season_complete(bootstrap) is True

    def test_one_event_not_finished(self):
        finished = [True] * 37 + [False]
        bootstrap = {"events": _make_events(finished, [True] * 38)}
        assert _is_season_complete(bootstrap) is False

    def test_one_event_not_data_checked(self):
        checked = [True] * 37 + [False]
        bootstrap = {"events": _make_events([True] * 38, checked)}
        assert _is_season_complete(bootstrap) is False

    def test_empty_events(self):
        assert _is_season_complete({"events": []}) is False

    def test_missing_events_key(self):
        assert _is_season_complete({}) is False

    def test_single_event_complete(self):
        bootstrap = {"events": _make_events([True], [True])}
        assert _is_season_complete(bootstrap) is True


class TestGetSeasonName:
    """Tests for _get_season_name."""

    def test_derives_season_name_from_2024(self):
        bootstrap = {"events": _make_events([True], [True], start_year=2024)}
        assert _get_season_name(bootstrap) == "2024-25"

    def test_derives_season_name_from_2025(self):
        bootstrap = {"events": _make_events([True], [True], start_year=2025)}
        assert _get_season_name(bootstrap) == "2025-26"

    def test_empty_events(self):
        assert _get_season_name({"events": []}) is None

    def test_missing_events_key(self):
        assert _get_season_name({}) is None

    def test_short_deadline_time(self):
        bootstrap = {"events": [{"deadline_time": "20"}]}
        assert _get_season_name(bootstrap) is None


class TestGetArchivedSeasons:
    """Tests for _get_archived_seasons."""

    def test_no_archive_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path / "nope"))
        assert _get_archived_seasons() == []

    def test_empty_archive_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))
        assert _get_archived_seasons() == []

    def test_returns_sorted_season_dirs(self, tmp_path, monkeypatch):
        (tmp_path / "2024-25").mkdir()
        (tmp_path / "2023-24").mkdir()
        (tmp_path / "not_a_dir.txt").touch()
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))
        assert _get_archived_seasons() == ["2023-24", "2024-25"]


class TestHasArchivedData:
    """Tests for has_archived_data."""

    def test_false_when_no_archive(self, tmp_path, monkeypatch):
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path / "nope"))
        assert has_archived_data() is False

    def test_true_when_archive_exists(self, tmp_path, monkeypatch):
        (tmp_path / "2024-25").mkdir()
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))
        assert has_archived_data() is True


class TestConcatenateArchivedHistory:
    """Tests for _concatenate_archived_history."""

    def _setup_archive(self, tmp_path, season="2023-24"):
        """Create a minimal archive for testing concatenation."""
        season_dir = tmp_path / season
        season_dir.mkdir(parents=True)

        arch_players = pd.DataFrame(
            {"code": [1001, 1002]},
            index=pd.Index([10, 20], name="id"),
        )
        arch_players.to_csv(
            season_dir / "players_data.csv", index=True, index_label="id"
        )

        arch_history = pd.DataFrame(
            {
                "element": [10, 10, 20, 20],
                "round": [1, 2, 1, 2],
                "minutes": [90, 90, 90, 90],
                "total_points": [5, 6, 3, 4],
            }
        )
        arch_history.to_csv(season_dir / "player_histories.csv", index=False)
        return arch_players, arch_history

    def test_no_archived_seasons(self, tmp_path, monkeypatch):
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))
        history_df = pd.DataFrame({"element": [1], "round": [1], "code": [1001]})
        players_df = pd.DataFrame({"code": [1001]}, index=pd.Index([1], name="id"))

        result = _concatenate_archived_history(history_df, players_df)
        assert len(result) == 1

    def test_concatenates_with_offset_rounds(self, tmp_path, monkeypatch):
        self._setup_archive(tmp_path, "2023-24")
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))

        # Current season: players have same code but different element IDs
        players_df = pd.DataFrame(
            {"code": [1001, 1002]},
            index=pd.Index([100, 200], name="id"),
        )
        history_df = pd.DataFrame(
            {
                "element": [100, 100, 200],
                "round": [1, 2, 1],
                "minutes": [90, 90, 90],
                "total_points": [7, 8, 5],
            }
        )

        result = _concatenate_archived_history(history_df, players_df)

        # Archived: 4 rows, current: 3 rows
        assert len(result) == 7
        # Archived rounds should be negative (offset by -(max_round+1) = -3)
        archived_rows = result[result["round"] < 0]
        assert len(archived_rows) == 4
        assert archived_rows["round"].min() == -2  # round 1 -> 1 - 2 - 1 = -2
        assert archived_rows["round"].max() == -1  # round 2 -> 2 - 2 - 1 = -1

    def test_players_missing_code_column(self, tmp_path, monkeypatch):
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))
        self._setup_archive(tmp_path)

        players_df = pd.DataFrame(
            {"web_name": ["P1"]},
            index=pd.Index([1], name="id"),
        )
        history_df = pd.DataFrame({"element": [1], "round": [1]})

        result = _concatenate_archived_history(history_df, players_df)
        assert len(result) == 1

    def test_archive_missing_code_column(self, tmp_path, monkeypatch):
        season_dir = tmp_path / "2023-24"
        season_dir.mkdir()
        # Archive without code column
        arch_players = pd.DataFrame(
            {"web_name": ["Old"]},
            index=pd.Index([10], name="id"),
        )
        arch_players.to_csv(
            season_dir / "players_data.csv", index=True, index_label="id"
        )
        pd.DataFrame({"element": [10], "round": [1]}).to_csv(
            season_dir / "player_histories.csv", index=False
        )
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))

        players_df = pd.DataFrame({"code": [1001]}, index=pd.Index([1], name="id"))
        history_df = pd.DataFrame({"element": [1], "round": [1]})

        result = _concatenate_archived_history(history_df, players_df)
        # Should skip the archive with no code column
        assert len(result) == 1

    def test_archive_missing_files(self, tmp_path, monkeypatch):
        (tmp_path / "2023-24").mkdir()
        # Dir exists but no CSV files
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))

        players_df = pd.DataFrame({"code": [1001]}, index=pd.Index([1], name="id"))
        history_df = pd.DataFrame({"element": [1], "round": [1]})

        result = _concatenate_archived_history(history_df, players_df)
        assert len(result) == 1

    def test_sorted_by_code_and_round(self, tmp_path, monkeypatch):
        self._setup_archive(tmp_path, "2023-24")
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))

        players_df = pd.DataFrame(
            {"code": [1001, 1002]},
            index=pd.Index([100, 200], name="id"),
        )
        history_df = pd.DataFrame(
            {
                "element": [200, 100],
                "round": [1, 1],
                "minutes": [90, 90],
                "total_points": [5, 7],
            }
        )

        result = _concatenate_archived_history(history_df, players_df)
        codes = result["code"].tolist()
        # Should be sorted by code, then round
        assert codes == sorted(codes) or all(
            codes[i] <= codes[i + 1] for i in range(len(codes) - 1)
        )


class TestDetectNewToLeague:
    """Tests for _detect_new_to_league."""

    def test_no_archived_seasons(self, tmp_path, monkeypatch):
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path / "nope"))
        players_df = pd.DataFrame(
            {"code": [1001, 1002]}, index=pd.Index([1, 2], name="id")
        )
        result = _detect_new_to_league(players_df)
        assert "is_new_to_league" in result.columns
        assert not result["is_new_to_league"].any()

    def test_detects_new_and_existing_players(self, tmp_path, monkeypatch):
        season_dir = tmp_path / "2023-24"
        season_dir.mkdir()
        arch_players = pd.DataFrame(
            {"code": [1001, 1003]},
            index=pd.Index([10, 30], name="id"),
        )
        arch_players.to_csv(
            season_dir / "players_data.csv", index=True, index_label="id"
        )
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))

        players_df = pd.DataFrame(
            {"code": [1001, 1002, 1003]},
            index=pd.Index([1, 2, 3], name="id"),
        )
        result = _detect_new_to_league(players_df)

        assert not result.loc[1, "is_new_to_league"]  # 1001 existed
        assert result.loc[2, "is_new_to_league"]  # 1002 is new
        assert not result.loc[3, "is_new_to_league"]  # 1003 existed

    def test_missing_code_column(self, tmp_path, monkeypatch):
        (tmp_path / "2023-24").mkdir()
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))

        players_df = pd.DataFrame({"web_name": ["P1"]}, index=pd.Index([1], name="id"))
        result = _detect_new_to_league(players_df)
        assert "is_new_to_league" in result.columns
        assert not result["is_new_to_league"].any()

    def test_archive_missing_players_file(self, tmp_path, monkeypatch):
        (tmp_path / "2023-24").mkdir()
        # No players_data.csv in archive
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))

        players_df = pd.DataFrame({"code": [1001]}, index=pd.Index([1], name="id"))
        result = _detect_new_to_league(players_df)
        assert not result["is_new_to_league"].any()

    def test_all_players_new(self, tmp_path, monkeypatch):
        season_dir = tmp_path / "2023-24"
        season_dir.mkdir()
        arch_players = pd.DataFrame(
            {"code": [9999]},
            index=pd.Index([99], name="id"),
        )
        arch_players.to_csv(
            season_dir / "players_data.csv", index=True, index_label="id"
        )
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))

        players_df = pd.DataFrame(
            {"code": [1001, 1002]},
            index=pd.Index([1, 2], name="id"),
        )
        result = _detect_new_to_league(players_df)
        assert result["is_new_to_league"].all()

    def test_multiple_archived_seasons(self, tmp_path, monkeypatch):
        for season, codes in [("2022-23", [1001]), ("2023-24", [1002])]:
            d = tmp_path / season
            d.mkdir()
            pd.DataFrame(
                {"code": codes},
                index=pd.Index(range(len(codes)), name="id"),
            ).to_csv(d / "players_data.csv", index=True, index_label="id")
        monkeypatch.setattr("services.data_service.ARCHIVE_DIR", str(tmp_path))

        players_df = pd.DataFrame(
            {"code": [1001, 1002, 1003]},
            index=pd.Index([1, 2, 3], name="id"),
        )
        result = _detect_new_to_league(players_df)

        assert not result.loc[1, "is_new_to_league"]  # in 2022-23
        assert not result.loc[2, "is_new_to_league"]  # in 2023-24
        assert result.loc[3, "is_new_to_league"]  # not in any


class TestTryArchiveSeason:
    """Tests for _try_archive_season."""

    def test_skips_when_no_bootstrap(self):
        _try_archive_season({})

    def test_skips_when_season_incomplete(self):
        data = {
            "raw_bootstrap": {
                "events": _make_events([True, False], [True, True]),
            }
        }
        _try_archive_season(data)

    def test_skips_when_no_season_name(self):
        data = {
            "raw_bootstrap": {
                "events": [
                    {"finished": True, "data_checked": True, "deadline_time": ""}
                ]
            }
        }
        _try_archive_season(data)
