import secrets
from typing import Any, ClassVar

from .base import BaseScraper, ScrapedItem


class RedditScraper(BaseScraper):
    """
    Scraper for Reddit platform.
    Inherits from BaseScraper and implements the search method.
    """

    URL = "https://www.reddit.com/search.json"
    FILTER_MAP: ClassVar[dict[str, str]] = {
        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year",
    }

    def get_data(self, keyword: str, filter_by: str) -> dict[Any, Any]:
        """
        Fetch data from Reddit based on the keyword and filter criteria.

        Args:
            keyword (str): The keyword to search for.
            filter_by (str): Time filter criteria (e.g., 'day', 'week', 'month').

        Returns:
            dict: The JSON response from the Reddit API.
        """
        headers = {"User-Agent": secrets.choice(self.USER_AGENTS)}
        params: dict[str, Any] = {
            "q": keyword,
            "type": "posts",
            "sort": "relevance",
            "t": self.FILTER_MAP.get(filter_by),
            "limit": 100,
            "after": None,
        }
        return self.call_url(
            url=self.URL,
            headers=headers,
            params=params,
        )

    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        """
        Search for mentions on Reddit based on the keyword and filter criteria.

        Args:
            keyword (str): The keyword to search for.
            filter_by (str): Time filter criteria (e.g., 'day', 'week', 'month').

        Returns:
            list[ScrapedItem]: A list of ScrapedItem objects containing the search results.

        Raises:
            NotImplementedError: If the method is not implemented.
        """
        self.validate_filter(filter_by)
        data = self.get_data(keyword, filter_by)
