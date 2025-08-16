import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Optional

from mentions.scrapers.base import BaseScraper, ScrapedItem


class DevtoScraper(BaseScraper):
    """
    Scraper for Dev.to using Algolia (public) API.

    NOTE:
        Dev.to search is backed by Algolia. We use the same HN endpoint with
        adjusted params (query, tags, restrictSearchableAttributes).

    Pagination:
        Algolia `page` (0-based) + `hitsPerPage`. Stop at last page or empty.

    Date filter:
        Server-side via `created_at_i > cutoff` derived from FILTER_MAP.
    """

    URL: ClassVar[str] = "https://hn.algolia.com/api/v1/search"
    PLATFORM: ClassVar[str] = "devto"
    FILTER_MAP: ClassVar[dict[str, int]] = {
        "day": 1,
        "week": 7,
        "month": 30,
        "year": 365,
        "all": 10_000,
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
            USER_PROXIES: Optional explicit proxies.
            max_pages: Max number of Algolia pages to fetch.
            hits_per_page: Items per page.
        """
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.max_pages = max_pages
        self.hits_per_page = max(1, min(hits_per_page, 1000))

    def _get_unix_cutoff(self, filter_by: str) -> int:
        """
        Convert filter key into UNIX timestamp.
        """
        days_ago = self.FILTER_MAP.get(filter_by, 10_000)
        dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
        return int(dt.timestamp())

    def get_data(self, keyword: str, filter_by: str, page: int) -> dict[str, Any]:
        """
        Fetch a single page of results from the Algolia API (Dev.to index behavior).

        Args:
            keyword: Search term.
            filter_by: Time window key.
            page: 0-based Algolia page index.

        Returns:
            dict: JSON payload.
        """
        headers = {"User-Agent": secrets.choice(self.USER_AGENTS)}
        unix_cutoff = self._get_unix_cutoff(filter_by)
        params: dict[str, Any] = {
            "query": keyword,
            "tags": "story",
            "hitsPerPage": self.hits_per_page,
            "numericFilters": f"created_at_i>{unix_cutoff}",
            "restrictSearchableAttributes": "title,story_text",
            "page": page,
        }
        payload = self.call_url(self.URL, headers=headers, params=params)
        return payload or {}

    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        """
        Search Dev.to posts by keyword and date filter (paginated).

        Returns:
            list[ScrapedItem]
        """
        self.validate_filter(filter_by)

        def fetch_page(page_num: int) -> tuple[list[dict], bool]:
            data = self.get_data(keyword, filter_by, page=page_num - 1)
            hits = data.get("hits", []) or []
            nb_pages = data.get("nbPages")
            has_more = bool(hits) and (nb_pages is None or (page_num - 1) < nb_pages - 1)
            return hits, has_more

        results: list[ScrapedItem] = []
        for hits in self.paginate_numbered(fetch_page, max_pages=self.max_pages):
            for item in hits:
                content = item.get("title") or item.get("story_text") or ""
                url = item.get("url") or (f"https://dev.to/{item.get('author')}/{item.get('objectID')}")
                author = item.get("author")
                upvotes = item.get("points")
                created_at = item.get("created_at")
                comments = item.get("num_comments")

                results.append(
                    ScrapedItem(
                        keyword=keyword,
                        platform=self.PLATFORM,
                        content=content,
                        url=url,
                        upvotes=upvotes,
                        user_id=author,
                        user_profile_url=f"https://dev.to/{author}" if author else None,
                        timestamp=created_at,
                        mention_type="post",
                        sentiment=None,
                        comments=comments,
                    )
                )
        return results


if __name__ == "__main__":
    scraper = DevtoScraper()
    keyword = "AI"
    filter_by = "week"

    results = scraper.search(keyword, filter_by)
    print(f"\n Scraped {len(results)} posts from Dev.to for keyword '{keyword}'\n")

    for idx, item in enumerate(results, 1):
        print(f"{idx}. Content: {item.content[:100]}...")
        print(f"   URL: {item.url}")
        print(f"   Author: {item.user_id}")
        print(f"   Upvotes: {item.upvotes}")
        print(f"   Timestamp: {item.timestamp}")
        print("-" * 80)
