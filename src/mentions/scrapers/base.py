import random
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from typing import Any, ClassVar, Optional

import requests
from loguru import logger
from pydantic import BaseModel, Field

from mentions.errors import InValidFilterException


class ScrapedItem(BaseModel):
    """
    Represents a single scraped item with metadata.
    """

    keyword: str = Field(..., description="The keyword that was searched for.")
    platform: str = Field(..., description="The platform from which the item was scraped.")
    content: str = Field(..., description="The main content of the scraped item.")
    url: str = Field(..., description="The URL of the scraped item.")
    upvotes: Optional[int] = Field(None, description="Number of upvotes or likes the item received.")
    mention_type: str | None = Field(None, description="Type of mention (e.g., post, comment).")
    user_id: Optional[str] = Field(None, description="Unique identifier for the user who created the item.")
    user_profile_url: Optional[str] = Field(None, description="URL to the user's profile on the platform.")
    timestamp: Optional[str] = Field(None, description="Timestamp when the item was created or posted.")
    comments: Optional[int] = Field(None, description="Number of comments associated with the item.")
    # LLM Classification fields
    relevance_score: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Relevance score indicating how relevant the mention is to the target company (0.0 to 1.0).",
    )
    is_relevant: bool | None = Field(
        None,
        description="Whether this mention is actually about the target company (LLM classified).",
    )
    sentiment: str | None = Field(
        None,
        description="Sentiment classification of the content (positive, negative, neutral).",
    )
    emotion: str | None = Field(
        None,
        description="Primary emotion detected in the text (e.g., 'frustration', 'joy', 'curiosity', 'disappointment', 'anger', 'neutral', 'excitement', 'concern', 'satisfaction', 'confusion').",
    )
    summary: str | None = Field(
        None,
        max_length=150,
        description="Concise one-sentence summary of what the mention is about (max 150 characters).",
    )
    themes: list[str] = Field(
        default_factory=list,
        description="List of 1-3 key topics or themes discussed (lowercase, hyphenated).",
    )


class ProxyManager:
    """Thread-safe proxy cache with TTL.

    All BaseScraper instances share a single instance so that proxy fetching
    and validation only happens once per TTL window.
    """

    # Cache settings
    PROXY_TTL_SECONDS = 600  # 10 minutes
    REQUIRED_PROXY_COUNT = 2

    def __init__(self) -> None:
        self._proxies: list[str] = []
        self._fetched_at: float = 0.0
        self._fetch_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_proxies(self) -> list[str]:
        """Return cached proxies, refreshing if stale or empty."""
        if self._is_fresh():
            return list(self._proxies)

        with self._fetch_lock:
            # Double-check after acquiring lock (another thread may have refreshed)
            if self._is_fresh():
                return list(self._proxies)

            self._refresh()
            return list(self._proxies)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_fresh(self) -> bool:
        return bool(self._proxies) and (time.monotonic() - self._fetched_at) < self.PROXY_TTL_SECONDS

    def _refresh(self) -> None:
        raw = self._fetch_proxy_list()
        if not raw:
            logger.warning("No free proxies available from provider.")
            self._proxies = []
            self._fetched_at = time.monotonic()
            return

        validated = self._validate_proxies(raw)
        if len(validated) < self.REQUIRED_PROXY_COUNT:
            logger.warning(
                f"Only {len(validated)} valid proxies found (need {self.REQUIRED_PROXY_COUNT}). "
                "Scrapers will use system IP."
            )
            self._proxies = []
        else:
            self._proxies = validated

        self._fetched_at = time.monotonic()

    @staticmethod
    def _fetch_proxy_list() -> list[str]:
        url = (
            "https://api.proxyscrape.com/v4/free-proxy-list/get"
            "?request=display_proxies&proxy_format=protocolipport&format=text"
        )
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return [p.strip() for p in response.text.splitlines() if p.strip()]
        except requests.RequestException as e:
            logger.error(f"Error fetching free proxies: {e}")
            return []

    @staticmethod
    def _validate_proxies(proxies: list[str]) -> list[str]:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _check(proxy: str) -> str | None:
            try:
                resp = requests.get(
                    "http://httpbin.org/ip",
                    proxies={"http": proxy, "https": proxy},
                    timeout=3,
                )
            except requests.RequestException:
                return None
            else:
                return proxy if resp.status_code == 200 else None

        required = ProxyManager.REQUIRED_PROXY_COUNT
        logger.info(f"Validating proxies (need {required} valid, {len(proxies)} candidates)...")

        valid: list[str] = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(_check, p): p for p in proxies}
            try:
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        valid.append(result)
                        if len(valid) >= required:
                            break
            finally:
                # Cancel remaining futures we no longer need
                for f in futures:
                    f.cancel()

        logger.info(f"Found {len(valid)} valid proxies.")
        return valid


# Module-level singleton
_proxy_manager = ProxyManager()


class BaseScraper(ABC):
    """
    Abstract base class for all platform scrapers (e.g., Reddit, X, Instagram).
    """

    REQUIRED_PROXY_COUNT = 2
    USER_AGENTS: ClassVar[list[str]] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0",
        "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36",
    ]
    FILTER_MAP: ClassVar[dict[str, str]] = {}

    def __init__(self, use_free_proxies: bool = True, USER_PROXIES: list[str] | None = None):
        """
        Initialize the scraper.

        No network calls are made here. Proxies are resolved lazily on
        the first ``call_url`` invocation via the shared ``ProxyManager``.
        """
        self._use_free_proxies = use_free_proxies
        self._user_proxies = USER_PROXIES
        self._proxies_resolved = False
        self.proxies: list[str] = []

    def _ensure_proxies(self) -> None:
        """Resolve proxies lazily (called once, on first network request)."""
        if self._proxies_resolved:
            return
        self._proxies_resolved = True

        if self._user_proxies:
            self.proxies = self._user_proxies
            return

        if not self._use_free_proxies:
            logger.warning("No proxies configured. Using system IP.")
            return

        self.proxies = _proxy_manager.get_proxies()

    def validate_filter(self, filter_by: str) -> None:
        """
        Check if the provided filter is valid.

        Args:
            filter_by (str): The filter criteria to check.

        Returns:
            bool: True if the filter is valid, False otherwise.
        """
        if filter_by not in self.FILTER_MAP:
            raise InValidFilterException(filter_by, list(self.FILTER_MAP.keys()))

    def call_url(self, url: str, headers: dict[str, Any], params: dict[str, Any]) -> dict[Any, Any] | None:
        """
        Make a GET request to the specified URL with the given headers and proxy.

        Args:
            url (str): The URL to fetch.
            headers (dict): Headers to include in the request.
            params (dict): Query parameters for the request.

        Returns:
            dict | None: The JSON response from the GET request, or None if error occurred.
        """
        # Lazy proxy resolution on first call
        self._ensure_proxies()

        try:
            proxy = {"http": random.choice(self.proxies)} if self.proxies else None  # noqa: S311
            response = requests.get(url, headers=headers, params=params, proxies=proxy, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
        else:
            logger.info(f"Successfully fetched {url} with status code {response.status_code}")
            return response.json()

    def get_proxies(self) -> list[str]:
        """
        Retrieve a list of proxies to use for scraping.
        Delegates to the shared ProxyManager for caching.
        """
        return _proxy_manager.get_proxies()

    def validate_proxies(self, proxies: list[str]) -> list[str]:
        """
        Validate the provided proxies by checking if they are reachable.
        Returns a list of valid proxies.
        """
        return ProxyManager._validate_proxies(proxies)

    def paginate_numbered(
        self,
        fetch_page: Callable[[int], tuple[list[dict], bool]],  # returns (items, has_more)
        max_pages: int,
    ) -> Iterator[list[dict]]:
        """
        Generic paginator for 'page=1..N' style APIs.
        `fetch_page(page)` must return (items, has_more).
        Yields the list of items for each page.
        """
        page = 1
        while page <= max_pages:
            items, has_more = fetch_page(page)
            if not items:
                break
            yield items
            if not has_more:
                break
            page += 1

    def paginate_cursor(
        self,
        fetch_cursor: Callable[
            [str | None], tuple[list[dict], str | None, bool]
        ],  # returns (items, next_cursor, has_more)
        max_pages: int,
        start_cursor: str | None = None,
    ) -> Iterator[list[dict]]:
        """
        Generic paginator for 'cursor/after' style APIs.
        `fetch_cursor(token)` must return (items, next_token, has_more).
        Yields the list of items for each cursor step.
        """
        token = start_cursor
        steps = 0
        while steps < max_pages:
            items, token, has_more = fetch_cursor(token)
            if not items:
                break
            yield items
            if not has_more:
                break
            steps += 1

    @abstractmethod
    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        """
        Search and scrape content related to a keyword.
        """
        pass
