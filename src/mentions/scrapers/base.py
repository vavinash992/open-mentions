import random
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from typing import Any, ClassVar, Optional

import requests
from loguru import logger
from pydantic import BaseModel, Field

from mentions.errors import InValidFilterException
from mentions.utils.utils import run_in_parallel


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


class BaseScraper(ABC):
    """
    Abstract base class for all platform scrapers (e.g., Reddit, X, Instagram).
    """

    REQUIRED_PROXY_COUNT = 5
    USER_AGENTS: ClassVar[list[str]] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0",
        "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36",
    ]
    FILTER_MAP: ClassVar[dict[str, str]] = {}

    def __init__(self, use_free_proxies: bool = True, USER_PROXIES: list[str] | None = None):
        """
        Initialize the scraper. This method can be overridden by subclasses
        to set up specific configurations or authentication.
        """
        # Initialize proxies to empty list by default
        self.proxies: list[str] = []

        # If user provided proxies, use them directly
        if USER_PROXIES:
            self.proxies = USER_PROXIES
            return

        # If not using free proxies and no user proxies provided
        if not use_free_proxies:
            logger.warning("No proxies are being used. This may lead to rate limiting or IP bans.")
            return

        # Try to get and validate free proxies
        if use_free_proxies:
            available_proxies = self.get_proxies()
            if not available_proxies:
                msg = "No free proxies available. Using system IP instead."
                logger.warning(msg)
                return

            proxies = self.validate_proxies(available_proxies)
            if len(proxies) < self.REQUIRED_PROXY_COUNT:
                logger.warning(
                    f"Only {len(proxies)} valid proxies found. "
                    f"Required: {self.REQUIRED_PROXY_COUNT}. "
                    "Using system IP instead."
                )
            else:
                self.proxies = proxies

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
            proxy (dict | None): Proxy settings for the request, if any.

        Returns:
            dict | None: The JSON response from the GET request, or None if error occurred.
        """
        try:
            proxy = {"http": random.choice(self.proxies)} if self.proxies else None  # noqa: S311
            response = requests.get(url, headers=headers, params=params, proxies=proxy, timeout=900)
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
        This method can be overridden by subclasses to provide specific proxy configurations.
        """
        url = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            proxies = response.text.splitlines()
            return [proxy.strip() for proxy in proxies if proxy.strip()]
        except requests.RequestException as e:
            logger.error(f"Error while trying to fetch free proxies: {e}")
            return []

    def validate_proxies(self, proxies: list[str]) -> list[str]:
        """
        Validate the provided proxies by checking if they are reachable.
        Returns a list of valid proxies.
        """
        valid_proxies: list[str] = []

        def validate_proxy(proxy: str) -> bool:
            try:
                response = requests.get(
                    "http://httpbin.org/ip",
                    proxies={"http": proxy, "https": proxy},
                    timeout=5,
                )
            except requests.RequestException:
                return False
            else:
                return response.status_code == 200

        logger.info(f"Validating {len(proxies)} proxies...")
        results = run_in_parallel(validate_proxy, [(proxy,) for proxy in proxies], max_workers=5)  # pyright: ignore[reportArgumentType]
        for proxy, is_valid in zip(proxies, results):
            if is_valid:
                valid_proxies.append(proxy)
                if len(valid_proxies) >= self.REQUIRED_PROXY_COUNT:
                    break
        logger.info(f"Found {len(valid_proxies)} valid proxies.")
        return valid_proxies

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
