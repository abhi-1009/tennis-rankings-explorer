"""Thin SportRadar client with rate-limit handling and retries."""
import logging
import time

import requests

from api import config

logger = logging.getLogger(__name__)


class SportRadarError(Exception):
    """Raised when the API cannot return usable data."""


def fetch_json(endpoint_key: str) -> dict:
    """Fetch one endpoint and return the parsed JSON.

    Retries on HTTP 429 (rate limit) and 5xx with exponential backoff.
    """
    if not config.API_KEY:
        raise SportRadarError("SPORTRADAR_API_KEY is not set (check your .env file).")

    url = config.BASE_URL + config.ENDPOINTS[endpoint_key]
    headers = {"x-api-key": config.API_KEY}  # key goes in the header, not the URL

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=config.TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            logger.warning("Network error on %s (attempt %d): %s", endpoint_key, attempt, exc)
        else:
            if response.status_code == 200:
                time.sleep(config.REQUEST_DELAY_SECONDS)  # stay under the rate limit
                return response.json()
            if response.status_code == 429 or response.status_code >= 500:
                logger.warning("HTTP %s on %s (attempt %d)", response.status_code, endpoint_key, attempt)
            else:
                raise SportRadarError(
                    f"HTTP {response.status_code} on {endpoint_key} (403 = bad/missing key or product not added to your key): {response.text[:200]}"
                )
        time.sleep(2 ** attempt)  # exponential backoff

    raise SportRadarError(f"Gave up on {endpoint_key} after {config.MAX_RETRIES} attempts.")
