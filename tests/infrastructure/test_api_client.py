"""Tests for API client infrastructure."""

from unittest.mock import patch, Mock

from infrastructure.api_client import fetch_data


class TestFetchData:
    """Tests for API fetching functionality."""

    @patch("infrastructure.api_client.requests.get")
    def test_successful_fetch(self, mock_get):
        """Should return JSON on successful API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"players": []}
        mock_get.return_value = mock_response

        result = fetch_data("bootstrap-static/")

        assert result == {"players": []}
        mock_get.assert_called_once()

    @patch("infrastructure.api_client.requests.get")
    def test_fetch_with_exception(self, mock_get):
        """Should handle request exceptions gracefully."""
        mock_get.side_effect = Exception("Network error")

        result = fetch_data("endpoint/")

        assert result is None


class TestAPIErrorHandling:
    """Tests for API error scenarios."""

    @patch("infrastructure.api_client.requests.get")
    def test_non_200_status(self, mock_get):
        """Should handle non-200 status codes."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = fetch_data("nonexistent/")

        assert result is None
