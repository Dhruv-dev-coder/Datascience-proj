"""
Reusable HTTP helper: retry logic, rate limiting, timeout handling.
All API clients should use `make_request()` instead of calling
requests / httpx directly.
"""
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.config import (
    API_MAX_RETRIES,
    API_RATE_LIMIT_SECONDS,
    API_RETRY_DELAY_SECONDS,
)
from src.utils.logger import logger


def _build_session() -> requests.Session:
    """Create a requests Session with automatic retry on transient errors."""
    session = requests.Session()
    retry_strategy = Retry(
        total=API_MAX_RETRIES,
        backoff_factor=API_RETRY_DELAY_SECONDS,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_SESSION = _build_session()


def make_request(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 30,
    rate_limit: float = API_RATE_LIMIT_SECONDS,
) -> dict | list:
    """
    Perform a GET request and return parsed JSON.

    Args:
        url:        Full URL to request.
        params:     Optional query parameters.
        headers:    Optional HTTP headers.
        timeout:    Request timeout in seconds.
        rate_limit: Seconds to sleep *before* the request (be kind to APIs).

    Returns:
        Parsed JSON response (dict or list).

    Raises:
        requests.HTTPError: on 4xx / 5xx responses.
        ValueError:         when response is not valid JSON.
    """
    if rate_limit > 0:
        time.sleep(rate_limit)

    logger.debug(f"GET {url} params={params}")
    response = _SESSION.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()

    try:
        return response.json()
    except ValueError as exc:
        logger.error(f"Non-JSON response from {url}: {response.text[:200]}")
        raise ValueError(f"Expected JSON from {url}") from exc
