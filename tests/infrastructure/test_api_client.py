"""Tests for API client infrastructure."""

import pytest
import requests
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
        """Should raise exception on network errors."""
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            fetch_data("endpoint/")


class TestAPIErrorHandling:
    """Tests for API error scenarios."""

    @patch("infrastructure.api_client.requests.get")
    def test_non_200_status(self, mock_get):
        """Should raise HTTPError on non-200 status codes."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError, match="404 Not Found"):
            fetch_data("nonexistent/")
