"""Tests for player service layer."""

import pandas as pd

from services.player_service import (
    extract_pinned_players,
    apply_price_filter,
    apply_team_filter,
    apply_search_filter,
    apply_all_filters,
    sort_by_column,
    paginate_results,
    get_filter_bounds,
)


class TestExtractPinnedPlayers:
    """Tests for pinned player extraction."""

    def test_extracts_pinned_correctly(self, players_for_filtering):
        """Should correctly separate pinned and remaining players."""
        pinned = ["Haaland", "Salah"]
        pinned_df, remaining_df = extract_pinned_players(players_for_filtering, pinned)

        assert len(pinned_df) == 2
        assert len(remaining_df) == 3
        assert "Haaland" in pinned_df["web_name"].values
        assert "Saka" in remaining_df["web_name"].values

    def test_empty_pinned_list(self, players_for_filtering):
        """Should return empty pinned df when no pinned players."""
        pinned_df, remaining_df = extract_pinned_players(players_for_filtering, [])

        assert pinned_df.empty
        assert len(remaining_df) == 5

    def test_no_web_name_column(self):
        """Should handle missing web_name column gracefully."""
        df = pd.DataFrame({"other_col": [1, 2]})
        pinned_df, remaining_df = extract_pinned_players(df, ["Player"])

        assert pinned_df.empty
        assert len(remaining_df) == 2


class TestApplyPriceFilter:
    """Tests for price filtering."""

    def test_filters_by_max_price(self, players_for_filtering):
        """Should only return players <= max price."""
        result = apply_price_filter(players_for_filtering, 100)

        assert len(result) == 3  # Saka (85), White (55), Raya (50)
        assert "Haaland" not in result["web_name"].values
        assert "Salah" not in result["web_name"].values

    def test_all_players_below_max(self, players_for_filtering):
        """Should return all when max is higher than all prices."""
        result = apply_price_filter(players_for_filtering, 150)

        assert len(result) == 5

    def test_no_players_below_max(self, players_for_filtering):
        """Should return empty when max is too low."""
        result = apply_price_filter(players_for_filtering, 40)

        assert result.empty


class TestApplyTeamFilter:
    """Tests for team filtering."""

    def test_filters_by_team(self, players_for_filtering):
        """Should return only players from selected team."""
        result = apply_team_filter(players_for_filtering, "Arsenal")

        assert len(result) == 3
        assert all(result["team_name"] == "Arsenal")

    def test_empty_team_selection(self, players_for_filtering):
        """Should return all players when no team selected."""
        result = apply_team_filter(players_for_filtering, "")

        assert len(result) == 5

    def test_missing_team_name_column(self):
        """Should handle missing team_name column."""
        df = pd.DataFrame({"web_name": ["Player"]})
        result = apply_team_filter(df, "Team")

        assert len(result) == 1


class TestApplySearchFilter:
    """Tests for search term filtering."""

    def test_filters_by_search_term(self, players_for_filtering, sample_players_df):
        """Should find players matching search term."""
        result = apply_search_filter(players_for_filtering, "Haa", sample_players_df)

        assert len(result) == 1
        assert result["web_name"].iloc[0] == "Haaland"

    def test_empty_search_term(self, players_for_filtering, sample_players_df):
        """Should return all players when search is empty."""
        result = apply_search_filter(players_for_filtering, "", sample_players_df)

        assert len(result) == 5

    def test_no_matches(self, players_for_filtering, sample_players_df):
        """Should return empty when no matches found."""
        result = apply_search_filter(players_for_filtering, "XYZ", sample_players_df)

        assert result.empty


class TestApplyAllFilters:
    """Integration tests for applying all filters together."""

    def test_applies_all_filters(self, players_for_filtering, sample_players_df):
        """Should apply price, team, and search filters together."""
        result = apply_all_filters(
            players_for_filtering,
            price_max=100,
            selected_team="Arsenal",
            search_term="",
            players_df=sample_players_df,
        )

        # Should have Arsenal players <= 100: Saka, White, Raya
        assert len(result) == 3
        assert all(result["team_name"] == "Arsenal")
        assert all(result["now_cost"] <= 100)

    def test_combining_filters_narrows_results(
        self, players_for_filtering, sample_players_df
    ):
        """Should narrow results when combining filters."""
        result = apply_all_filters(
            players_for_filtering,
            price_max=80,
            selected_team="Arsenal",
            search_term="",
            players_df=sample_players_df,
        )

        # Only White (55) and Raya (50)
        assert len(result) == 2


class TestSortByColumn:
    """Tests for sorting functionality."""

    def test_sorts_by_expected_points_desc(self, players_for_filtering):
        """Should sort by expected_points descending."""
        result = sort_by_column(players_for_filtering, "expected_points", "desc")

        assert result["expected_points"].iloc[0] == 6.5  # Haaland
        assert result["expected_points"].iloc[-1] == 3.1  # White

    def test_sorts_by_expected_points_asc(self, players_for_filtering):
        """Should sort by expected_points ascending."""
        result = sort_by_column(players_for_filtering, "expected_points", "asc")

        assert result["expected_points"].iloc[0] == 3.1  # White
        assert result["expected_points"].iloc[-1] == 6.5  # Haaland

    def test_custom_position_sort_asc(self, players_for_filtering):
        """Should sort positions GKP->DEF->MID->FWD when asc."""
        # Add GKP to test data
        df = pd.concat(
            [
                players_for_filtering,
                pd.DataFrame(
                    {
                        "web_name": ["NewGKP"],
                        "now_cost": [45],
                        "expected_points": [3.0],
                        "team_name": ["Team"],
                        "pos_abbr": ["GKP"],
                    }
                ),
            ],
            ignore_index=True,
        )

        result = sort_by_column(df, "pos_abbr", "asc")

        assert result["pos_abbr"].iloc[0] == "GKP"
        assert list(result["pos_abbr"].unique()) == ["GKP", "DEF", "MID", "FWD"]

    def test_handles_empty_dataframe(self):
        """Should handle empty dataframe gracefully."""
        empty_df = pd.DataFrame()
        result = sort_by_column(empty_df, "expected_points", "desc")

        assert result.empty

    def test_missing_column_uses_default(self):
        """Should use default column when sort column missing."""
        df = pd.DataFrame(
            {
                "web_name": ["Charlie", "Alice", "Bob"],
                "expected_points": [3.0, 1.0, 2.0],
            }
        )
        result = sort_by_column(df, "missing_column", "asc")

        # Should sort by web_name (alphabetical: Alice, Bob, Charlie)
        assert result["web_name"].iloc[0] == "Alice"


class TestPaginateResults:
    """Tests for pagination functionality."""

    def test_returns_correct_page(self, players_for_pagination):
        """Should return correct subset of players."""
        page_players, total, total_pages, page_num = paginate_results(
            players_for_pagination, page=1, per_page=10
        )

        assert len(page_players) == 10
        assert total == 25
        assert total_pages == 3
        assert page_num == 1
        assert page_players["rank"].iloc[0] == 1

    def test_second_page(self, players_for_pagination):
        """Should return second page correctly."""
        page_players, total, total_pages, page_num = paginate_results(
            players_for_pagination, page=2, per_page=10
        )

        assert len(page_players) == 10
        assert page_num == 2
        assert page_players["rank"].iloc[0] == 11

    def test_last_page_partial(self, players_for_pagination):
        """Should handle last page with fewer items."""
        page_players, total, total_pages, page_num = paginate_results(
            players_for_pagination, page=3, per_page=10
        )

        assert len(page_players) == 5
        assert page_num == 3

    def test_page_beyond_range(self, players_for_pagination):
        """Should clamp page number to valid range."""
        page_players, total, total_pages, page_num = paginate_results(
            players_for_pagination, page=100, per_page=10
        )

        assert page_num == 3  # Max page

    def test_empty_dataframe(self):
        """Should handle empty dataframe."""
        empty_df = pd.DataFrame()
        page_players, total, total_pages, page_num = paginate_results(empty_df, page=1)

        assert total == 0
        assert total_pages == 1  # At least 1 page even when empty
        assert page_players.empty


class TestGetFilterBounds:
    """Tests for filter bounds calculation."""

    def test_extracts_teams_and_prices(self, players_for_filtering):
        """Should extract unique teams and price range."""
        teams, min_price, max_price = get_filter_bounds(players_for_filtering)

        assert "Arsenal" in teams
        assert "Man City" in teams
        assert min_price == 5.0  # 50 / 10
        assert max_price == 14.0  # 140 / 10

    def test_missing_team_name_column(self):
        """Should handle missing team_name column."""
        df = pd.DataFrame({"now_cost": [50, 100]})
        teams, min_price, max_price = get_filter_bounds(df)

        assert teams == []
        assert min_price == 5.0
        assert max_price == 10.0

    def test_empty_dataframe_defaults(self):
        """Should use defaults for empty dataframe."""
        empty_df = pd.DataFrame()
        teams, min_price, max_price = get_filter_bounds(empty_df)

        assert teams == []
        assert min_price == 4.0
        assert max_price == 15.0
