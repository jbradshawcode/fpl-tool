import requests

from .config import BASE_URL


def fetch_data(endpoint: str) -> dict or None:
    """Fetch data from the FPL API and return JSON as dict."""
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
