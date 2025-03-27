import urllib.parse
from typing import Any, Dict

import requests
from helpers.config import BASE_URL
from helpers.logger import logger
from helpers.utils import raise_error


def make_request(url: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """
    A helper function to send an HTTP GET request. If any error occurs,
    it logs the error and raises an exception (thus crashing the code).
    """
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise_error(f"An unexpected error occurred during the request to {url}: {e}")

def fetch_file_content(file_path: str) -> str:
    logger.info(f"Fetching file content for {file_path}")
    try:
        response = requests.get(
            url=f"{BASE_URL}/{urllib.parse.quote_plus(file_path)}",
            params={"alt": "media"},
        )
        response.raise_for_status()
        return response.content.decode("UTF-8")
    except Exception as e:
        raise_error(f"An unexpected error occurred in fetch_file_content: {e}")
