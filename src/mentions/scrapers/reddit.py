import secrets
from datetime import datetime, timezone
from typing import Any, ClassVar, Optional

from mentions.scrapers.base import BaseScraper, ScrapedItem


class RedditScraper(BaseScraper):
    """
    Scraper for Reddit search (public, unauthenticated).

    Endpoint:
        GET https://www.reddit.com/search.json

    Pagination:
        Uses cursor `after` returned in `data.after`.
        We stop when `after` is None or after max_pages steps.

    Time filter:
        `t` ∈ {'day','week','month','year'} maps directly to Reddit's time filter.
    """

    URL = "https://www.reddit.com/search.json"
    FILTER_MAP: ClassVar[dict[str, str]] = {
        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year",
    }

    def __init__(
        self,
        use_free_proxies: bool = True,
        USER_PROXIES: Optional[list[str]] = None,
        max_pages: int = 3,
        limit: int = 100,
        sort: str = "relevance",  # 'relevance', 'new', 'hot', 'top', 'comments'
        search_type: str = "posts",  # 'link'/'sr' etc.; Reddit UI uses 'posts'
    ):
        """
        Args:
            use_free_proxies: Whether to use proxies from BaseScraper.
            USER_PROXIES: Optional custom proxies.
            max_pages: Maximum cursor steps to fetch.
            limit: Items per request (Reddit caps at 100).
            sort: Sort strategy for search endpoint.
            search_type: Search type; 'posts' is what UI sends for posts.
        """
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.max_pages = max_pages
        self.limit = max(1, min(limit, 100))
        self.sort = sort
        self.search_type = search_type

    def get_data(self, keyword: str, filter_by: str, after: Optional[str]) -> dict[Any, Any] | None:
        """
        Fetch a single page of Reddit search results.

        Args:
            keyword: Search query.
            filter_by: One of {'day','week','month','year'}.
            after: Reddit cursor token (fullname) or None for first page.

        Returns:
            dict | None: JSON payload or None on failure.
        """
        headers = {"User-Agent": secrets.choice(self.USER_AGENTS)}
        params: dict[str, Any] = {
            "q": keyword,
            "type": self.search_type,
            "sort": self.sort,
            "t": self.FILTER_MAP.get(filter_by),
            "limit": self.limit,
        }
        if after:
            params["after"] = after

        return self.call_url(url=self.URL, headers=headers, params=params)

    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        """
        Search Reddit posts for a keyword with cursor pagination.

        Returns:
            list[ScrapedItem]
        """
        self.validate_filter(filter_by)

        def fetch_cursor(token: Optional[str]) -> tuple[list[dict], Optional[str], bool]:
            payload = self.get_data(keyword, filter_by, after=token) or {}
            data = payload.get("data") or {}
            children = data.get("children") or []
            next_after = data.get("after")
            has_more = bool(next_after) and bool(children)
            return children, next_after, has_more

        results: list[ScrapedItem] = []
        for children in self.paginate_cursor(fetch_cursor, max_pages=self.max_pages, start_cursor=None):
            for child in children:
                d = child.get("data") or {}
                title = d.get("title") or ""
                permalink = d.get("permalink") or ""
                url = d.get("url") or (f"https://www.reddit.com{permalink}" if permalink else None)
                if not url:
                    continue

                created_utc = d.get("created_utc")
                ts_iso = (
                    datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
                    if isinstance(created_utc, (int, float))
                    else None
                )

                results.append(
                    ScrapedItem(
                        keyword=keyword,
                        platform="reddit",
                        content=title,
                        url=url,
                        upvotes=d.get("ups"),
                        sentiment=None,
                        mention_type="post",
                        user_id=d.get("author"),
                        user_profile_url=f"https://www.reddit.com/user/{d.get('author')}" if d.get("author") else None,
                        timestamp=ts_iso,
                        comments=d.get("num_comments"),
                    )
                )
        return results
