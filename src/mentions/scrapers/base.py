import random
from abc import ABC, abstractmethod
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
    sentiment: str | None = Field(
        None,
        description="Sentiment classification of the content (e.g., positive, negative, neutral).",
    )
    mention_type: str | None = Field(None, description="Type of mention (e.g., post, comment).")
    user_id: Optional[str] = Field(None, description="Unique identifier for the user who created the item.")
    user_profile_url: Optional[str] = Field(None, description="URL to the user's profile on the platform.")
    timestamp: Optional[str] = Field(None, description="Timestamp when the item was created or posted.")
    comments: Optional[int] = Field(None, description="Number of comments associated with the item.")


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
        if not use_free_proxies and USER_PROXIES is None:
            logger.warning("No proxies are being used. This may lead to rate limiting or IP bans.")
            self.proxies = []
        if use_free_proxies:
            available_proxies = self.get_proxies()
            if not available_proxies:
                msg = "No free proxies available. Using system IP instead."
                logger.warning(msg)
            proxies = self.validate_proxies(available_proxies) if available_proxies else []
            if len(proxies) < self.REQUIRED_PROXY_COUNT:
                logger.warning(
                    f"Only {len(proxies)} valid proxies found. "
                    f"Required: {self.REQUIRED_PROXY_COUNT}. "
                    "Using system IP instead."
                )
                self.proxies = []
        if USER_PROXIES:
            self.proxies = USER_PROXIES

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

    def call_url(self, url: str, headers: dict[str, Any], params: dict[str, Any]) -> dict[Any, Any]:
        """
        Make a GET request to the specified URL with the given headers and proxy.

        Args:
            url (str): The URL to fetch.
            headers (dict): Headers to include in the request.
            params (dict): Query parameters for the request.
            proxy (dict | None): Proxy settings for the request, if any.

        Returns:
            Response: The response object from the GET request.
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

    @abstractmethod
    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        """
        Search and scrape content related to a keyword.
        """
        pass
