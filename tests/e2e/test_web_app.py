"""End-to-end tests for the web application."""

from unittest.mock import patch

import pandas as pd
import pytest

from app import app


@pytest.fixture
def client():
    """Create a test client for the app."""
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
        # Clean up session after each test
        with test_client.session_transaction() as sess:
            sess.clear()


class TestWebAppEndpoints:
    """End-to-end tests for web application endpoints."""

    def test_index_page_loads(self, client):
        """Test that the index page loads successfully."""
        # Mock data loading to avoid slow API calls
        mock_players = pd.DataFrame(
            {
                "web_name": ["Test Player"],
                "team": [1],
                "position": "DEF",
                "now_cost": 50,
            },
            index=[1],
        )

        mock_history = pd.DataFrame(
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

        mock_fdr = pd.DataFrame(
            {
                "round": [30],
                "team_id": [1],
                "opponent_id": [2],
                "fixture_difficulty": [3],
                "was_home": True,
            }
        )

        with patch("services.data_service.load_fpl_data") as mock_load:
            mock_load.return_value = (mock_players, mock_history, mock_fdr)

            response = client.get("/")
            assert response.status_code == 200
            assert b"<!DOCTYPE html" in response.data

    def test_pin_player_endpoint(self, client):
        """Test that the pin player endpoint works."""
        # Test pinning a player
        response = client.post(
            "/api/pin-player",
            json={"player_name": "Test Player", "action": "pin"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Test Player" in data["pinned_players"]

        # Test unpinning the player
        response = client.post(
            "/api/pin-player",
            json={"player_name": "Test Player", "action": "unpin"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "Test Player" not in data["pinned_players"]

    def test_invalid_pin_request(self, client):
        """Test that invalid pin requests are handled correctly."""
        # Missing fields
        response = client.post("/api/pin-player", json={})
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False

        # Invalid action
        response = client.post(
            "/api/pin-player",
            json={"player_name": "Test Player", "action": "invalid"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
