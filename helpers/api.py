"""Simple helper for requesting JSON data from the Fantasy Premier League API.

This module provides a thin wrapper around `requests.get` that:
- Builds full API URLs using the configured base path
- Performs the HTTP request with sensible timeouts
- Raises appropriate errors for unsuccessful responses
- Returns parsed JSON as a Python dictionary
"""

import requests

from .config import BASE_URL


def fetch_data(endpoint: str) -> dict:
    """Retrieve JSON data from the Fantasy Premier League API.

    Parameters
    ----------
    endpoint : str
        Relative API endpoint to query (e.g. "bootstrap-static/").

    Returns
    -------
    dict
        Parsed JSON response as a dictionary.


    Raises
    ------
    requests.HTTPError
        If the request returns an unsuccessful HTTP status code.
    requests.RequestException
        For network-related issues such as timeouts or connection errors.
    requests.exceptions.JSONDecodeError
        If the response body is not valid JSON.
    TypeError
        If the response JSON is not a dictionary.

    """
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data
