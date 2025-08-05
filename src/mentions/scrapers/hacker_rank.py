import secrets
import time
from typing import Any, ClassVar

from mentions.scrapers.base import BaseScraper, ScrapedItem


class HackerNewsScraper(BaseScraper):
    """
    Scraper for Hacker News platform using Algolia's public API.
    """

    URL = "https://hn.algolia.com/api/v1/search"
    FILTER_MAP: ClassVar[dict[str, str]] = {
        "day": str(1 * 86400),
        "week": str(7 * 86400),
        "month": str(30 * 86400),
        "year": str(365 * 86400),
    }

    def __init__(self, use_free_proxies: bool = True, USER_PROXIES: list[str] | None = None):
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)

    def get_data(self, keyword: str, filter_by: str) -> dict[Any, Any]:
        """
        Fetch data from Hacker News based on keyword and time filter.

        Args:
            keyword (str): Keyword to search for.
            filter_by (str): Time filter (e.g., 'day', 'week').

        Returns:
            dict: JSON response from the API.
        """
        headers = {"User-Agent": secrets.choice(self.USER_AGENTS)}
        params: dict[str, Any] = {
            "query": keyword,
            "tags": "story",
            "hitsPerPage": 100,
            "numericFilters": f"created_at_i>{self._get_unix_time(filter_by)}",
        }

        response = self.call_url(
            url=self.URL,
            headers=headers,
            params=params,
        )

        return response or {}

    def _get_unix_time(self, filter_by: str) -> int:
        """
        Compute UNIX timestamp for time filtering.

        Args:
            filter_by (str): Time window like 'day', 'week', etc.

        Returns:
            int: UNIX timestamp representing cutoff time.
        """
        now = int(time.time())
        return now - int(self.FILTER_MAP[filter_by])

    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        """
        Search Hacker News for stories containing the keyword.

        Args:
            keyword (str): Keyword to look for.
            filter_by (str): Time range to filter results.

        Returns:
            list[ScrapedItem]: List of structured results.
        """
        self.validate_filter(filter_by)
        data = self.get_data(keyword, filter_by)
        results: list[ScrapedItem] = []

        for item in data.get("hits", []):
            content = item.get("title") or item.get("story_text") or ""
            results.append(
                ScrapedItem(
                    keyword=keyword,
                    platform="hackernews",
                    content=content,
                    url=item.get("url") or f"https://news.ycombinator.com/item?id={item['objectID']}",
                    upvotes=item.get("points"),
                    user_id=item.get("author"),
                    user_profile_url=f"https://news.ycombinator.com/user?id={item.get('author')}",
                    timestamp=item.get("created_at"),
                    mention_type="post",
                    sentiment=None,
                    comments=item.get("num_comments"),
                )
            )

        return results


if __name__ == "__main__":
    scraper = HackerNewsScraper()
    keyword = "AI"
    filter_by = "week"

    results = scraper.search(keyword, filter_by)
    print(f"\n Scraped {len(results)} posts from Hacker News for keyword '{keyword}'\n")

    for idx, item in enumerate(results, 1):
        print(f"{idx}. Content: {item.content[:100]}...")
        print(f"   URL: {item.url}")
        print(f"   Author: {item.user_id}")
        print(f"   Upvotes: {item.upvotes}")
        print(f"   Timestamp: {item.timestamp}")
        print("-" * 80)
