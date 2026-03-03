"""HTTP fetcher with rate limiting, retries, and session management."""
import time
import random
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from scraper.config import (
    HEADERS,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
    MAX_RETRIES,
    RETRY_DELAY,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


class Fetcher:
    """HTTP fetcher with rate limiting and retry logic."""

    def __init__(self):
        self.session = self._create_session()
        self._last_request_time = 0.0
        self.total_requests = 0
        self.failed_requests = 0

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(HEADERS)

        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _rate_limit(self):
        """Enforce delay between requests."""
        elapsed = time.time() - self._last_request_time
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        if elapsed < delay:
            sleep_time = delay - elapsed
            time.sleep(sleep_time)

    def get(self, url: str) -> requests.Response | None:
        """Fetch a URL with rate limiting and error handling."""
        self._rate_limit()
        self.total_requests += 1

        try:
            logger.debug(f"GET {url}")
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            self._last_request_time = time.time()

            if resp.status_code == 200:
                return resp
            elif resp.status_code == 404:
                logger.warning(f"404 Not Found: {url}")
                return None
            else:
                logger.warning(f"HTTP {resp.status_code}: {url}")
                self.failed_requests += 1
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            self.failed_requests += 1
            self._last_request_time = time.time()
            return None

    def get_html(self, url: str) -> str | None:
        """Fetch URL and return HTML text, or None on failure."""
        resp = self.get(url)
        if resp is not None:
            # Check for bot protection / captcha
            text_lower = resp.text.lower()
            if "servicepipe" in text_lower or "captcha" in text_lower or "докажите, что вы не робот" in text_lower:
                logger.error(f"BOT PROTECTION DETECTED at {url}! Stopping scraper to prevent empty data.")
                raise Exception("Bot protection / Captcha triggered. Scraper stopped.")
            return resp.text
        return None

    def stats(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
        }
