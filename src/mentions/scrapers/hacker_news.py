import secrets
import time
from typing import Any, ClassVar, Optional

from mentions.scrapers.base import BaseScraper, ScrapedItem


class HackerNewsScraper(BaseScraper):
    """
    Scraper for Hacker News platform using Algolia's public API.

    Pagination:
        Uses Algolia `page` (0-based) and `hitsPerPage`.
        We stop when current page >= nbPages-1 or when no hits.

    Date filter:
        Uses `created_at_i > cutoff` (server-side) computed from FILTER_MAP.
    """

    URL = "https://hn.algolia.com/api/v1/search"
    FILTER_MAP: ClassVar[dict[str, int]] = {
        "day": 1 * 86400,
        "week": 7 * 86400,
        "month": 30 * 86400,
        "year": 365 * 86400,
    }

    def __init__(
        self,
        use_free_proxies: bool = True,
        USER_PROXIES: Optional[list[str]] = None,
        max_pages: int = 3,
        hits_per_page: int = 100,
    ):
        """
        Args:
            use_free_proxies: Whether to use proxies from BaseScraper.
            USER_PROXIES: Optional custom proxy list.
            max_pages: Maximum number of pages to fetch (Algolia page is 0-based).
            hits_per_page: Items per page (Algolia caps at ~1000, but 100 is typical).
        """
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.max_pages = max_pages
        self.hits_per_page = max(1, min(hits_per_page, 1000))

    def _get_unix_cutoff(self, filter_by: str) -> int:
        """
        Compute UNIX timestamp cutoff for time filtering.
        """
        now = int(time.time())
        return now - int(self.FILTER_MAP[filter_by])

    def get_data(self, keyword: str, filter_by: str, page: int) -> dict[str, Any]:
        """
        Fetch a single page from HN Algolia.

        Args:
            keyword: Search query.
            filter_by: One of {'day','week','month','year'}.
            page: 0-based page index for Algolia.

        Returns:
            dict: The JSON payload (empty dict on failure).
        """
        headers = {"User-Agent": secrets.choice(self.USER_AGENTS)}
        params: dict[str, Any] = {
            "query": keyword,
            "tags": "story",
            "hitsPerPage": self.hits_per_page,
            "numericFilters": f"created_at_i>{self._get_unix_cutoff(filter_by)}",
            "page": page,
        }
        payload = self.call_url(self.URL, headers=headers, params=params)
        return payload or {}

    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        """
        Search Hacker News for stories containing the keyword (paginated).

        Returns:
            list[ScrapedItem]
        """
        self.validate_filter(filter_by)

        def fetch_page(page_num: int) -> tuple[list[dict], bool]:
            data = self.get_data(keyword, filter_by, page=page_num - 1)  # our paginator is 1-based; Algolia is 0-based
            hits = data.get("hits", []) or []
            nb_pages = data.get("nbPages")
            has_more = bool(hits) and (nb_pages is None or (page_num - 1) < nb_pages - 1)
            return hits, has_more

        results: list[ScrapedItem] = []
        for hits in self.paginate_numbered(fetch_page, max_pages=self.max_pages):
            for item in hits:
                content = item.get("title") or item.get("story_text") or ""
                url = item.get("url") or (f"https://news.ycombinator.com/item?id={item.get('objectID')}")
                author = item.get("author")
                created_at = item.get("created_at")  # ISO string from Algolia
                comments = item.get("num_comments")
                upvotes = item.get("points")

                results.append(
                    ScrapedItem(
                        keyword=keyword,
                        platform="hackernews",
                        content=content,
                        url=url,
                        upvotes=upvotes,
                        user_id=author,
                        user_profile_url=f"https://news.ycombinator.com/user?id={author}" if author else None,
                        timestamp=created_at,
                        mention_type="post",
                        sentiment=None,
                        comments=comments,
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
