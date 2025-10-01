import logging
import requests
from typing import Dict, Optional
from .config import BASE_URL


def fetch_data(endpoint: str) -> Optional[Dict]:
    """Fetch data from the FPL API and return JSON as dict."""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None
