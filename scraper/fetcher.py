"""HTTP fetcher with rate limiting, retries, and session management."""
import time
import random
import logging
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from zenrows import ZenRowsClient

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
    """HTTP fetcher with rate limiting, retry logic, and ZenRows integration."""

    def __init__(self):
        self.session = self._create_session()
        self._last_request_time = 0.0
        self.total_requests = 0
        self.failed_requests = 0
        
        # Initialize ZenRows client if API key is provided
        # Use env var or fallback to hardcoded key for this project
        zenrows_key = os.environ.get("ZENROWS_API_KEY", "d1800de85f07a36264310be0b592a56fdeb253b4")
        self.zenrows_client = ZenRowsClient(zenrows_key) if zenrows_key else None
        
        if self.zenrows_client:
            logger.info("ZenRows API enabled for anti-bot bypass")

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
        # ZenRows manages its own concurrency, but we still want to be gentle
        elapsed = time.time() - self._last_request_time
        delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
        if elapsed < delay:
            sleep_time = delay - elapsed
            time.sleep(sleep_time)

    def get(self, url: str) -> requests.Response | None:
        """Fetch a URL with rate limiting, error handling, and ZenRows fallback."""
        self._rate_limit()
        self.total_requests += 1

        try:
            logger.debug(f"GET {url}")
            
            if self.zenrows_client:
                # Use ZenRows to bypass Cloudflare/ServicePipe
                # Remove Accept-Encoding to prevent ZenRows from returning raw gzip bytes 
                # that requests won't auto-decode due to Zr- prefixed headers.
                zr_headers = HEADERS.copy()
                zr_headers.pop("Accept-Encoding", None)
                
                resp = self.zenrows_client.get(
                    url, 
                    params={"antibot": "true", "premium_proxy": "true"}, 
                    headers=zr_headers
                )
            else:
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
        # Retry logic specifically for ZenRows failures
        retries = 3
        for attempt in range(retries):
            resp = self.get(url)
            if resp is not None:
                # Check for bot protection / captcha even with ZenRows (sometimes it slips through)
                text_lower = resp.text.lower()
                if "servicepipe" in text_lower or "captcha" in text_lower or "докажите, что вы не робот" in text_lower:
                    logger.warning(f"BOT PROTECTION DETECTED at {url} on attempt {attempt+1}! Retrying...")
                    time.sleep(5)
                    continue
                return resp.text
            
            # If resp is None (failed request), retry
            logger.warning(f"Failed to get {url} on attempt {attempt+1}. Retrying...")
            time.sleep(5)
            
        logger.error(f"Failed to fetch {url} after {retries} attempts.")
        return None

    def stats(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
        }
