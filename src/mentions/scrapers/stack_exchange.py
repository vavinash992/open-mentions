import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

from mentions.scrapers.base import BaseScraper, ScrapedItem


class StackExchangeScraper(BaseScraper):
    """
    Scraper for Stack Exchange using its public API (api.stackexchange.com).

    Fetches questions based on keyword, site, sort method, and date filters.
    Supports pagination via `max_pages`.
    """

    BASE_URL: ClassVar[str] = "https://api.stackexchange.com/2.3/search"
    FILTER_MAP: ClassVar[dict[str, int]] = {
        "day": 1,
        "week": 7,
        "month": 30,
        "year": 365,
    }

    def __init__(
        self,
        use_free_proxies: bool = True,
        USER_PROXIES: list[str] | None = None,
        max_pages: int = 3,
        page_size: int = 50,
    ):
        """
        Initialize the StackExchangeScraper.

        Args:
            use_free_proxies (bool): Whether to use free proxies.
            USER_PROXIES (list[str] | None): Custom proxy list.
            max_pages (int): Maximum number of pages to fetch.
            page_size (int): Number of results per page (max 100).
        """
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.max_pages = max_pages
        self.page_size = min(max(page_size, 1), 100)

    def get_data(self, keyword: str, site: str, filter_by: str) -> list[dict[str, Any]]:
        """
        Fetch questions from Stack Exchange for a given keyword and site, with pagination.

        Args:
            keyword (str): Search query.
            site (str): Stack Exchange site (e.g., 'stackoverflow').
            filter_by (str): Time filter (day/week/month/year).

        Returns:
            list[dict]: List of question dictionaries.
        """
        headers = {"User-Agent": secrets.choice(self.USER_AGENTS)}
        params_base: dict[str, Any] = {
            "order": "desc",
            "sort": "relevance",
            "intitle": keyword,
            "site": site,
            "pagesize": self.page_size,
        }

        if filter_by in self.FILTER_MAP:
            days = self.FILTER_MAP[filter_by]
            fromdate = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
            params_base["fromdate"] = fromdate

        all_items: list[dict[str, Any]] = []
        page = 1

        while page <= self.max_pages:
            params = {**params_base, "page": page}
            response = self.call_url(self.BASE_URL, headers=headers, params=params)
            if not response:
                break

            items = response.get("items", [])
            all_items.extend(items)

            if not response.get("has_more"):
                break
            page += 1

        return all_items

    # stackexchange_scraper.py (only search changes shown)

    def search(self, keyword: str, filter_by: str, site: str = "stackoverflow") -> list[ScrapedItem]:
        """
        Search Stack Exchange for questions.

        Args:
            keyword (str): Query keyword.
            filter_by (str): Time window (day/week/month/year).
            site (str): Specific StackExchange site (default: stackoverflow).

        Returns:
            list[ScrapedItem]: Parsed and filtered results.
        """
        self.validate_filter(filter_by)

        def fetch_page(page: int) -> tuple[list[dict], bool]:
            headers = {"User-Agent": secrets.choice(self.USER_AGENTS)}
            params: dict[str, Any] = {
                "order": "desc",
                "sort": "relevance",
                "intitle": keyword,
                "site": site,
                "pagesize": self.page_size,  # ensure you have self.page_size set in __init__
                "page": page,
            }
            # fromdate if using filter_by
            if filter_by in self.FILTER_MAP:
                from datetime import datetime, timedelta, timezone

                days = self.FILTER_MAP[filter_by]
                fromdate = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
                params["fromdate"] = fromdate

            data = self.call_url(self.BASE_URL, headers=headers, params=params) or {}
            items = data.get("items", []) or []
            has_more = bool(data.get("has_more"))
            return items, has_more

        results: list[ScrapedItem] = []
        for page_items in self.paginate_numbered(fetch_page, max_pages=self.max_pages):
            for item in page_items:
                ts = item.get("creation_date")
                timestamp = (
                    datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if isinstance(ts, (int, float)) else None
                )
                results.append(
                    ScrapedItem(
                        keyword=keyword,
                        platform="stackexchange",
                        content=item.get("title", ""),
                        url=item.get("link"),
                        upvotes=item.get("score"),
                        user_id=item.get("owner", {}).get("display_name"),
                        user_profile_url=item.get("owner", {}).get("link"),
                        timestamp=timestamp,
                        mention_type="post",
                        comments=item.get("answer_count", 0),
                        sentiment=None,
                    )
                )
        return results


# -------------- TESTING ------------------
if __name__ == "__main__":
    scraper = StackExchangeScraper(max_pages=2, page_size=50)
    keyword = "AI"
    filter_by = "week"
    site = "stackoverflow"

    results = scraper.search(keyword, filter_by, site)
    print(f"\n Scraped {len(results)} posts from Stack Exchange ({site}) for keyword '{keyword}'\n")

    for idx, item in enumerate(results[:10], 1):  # show first 10
        print(f"{idx}. Content: {item.content[:100]}...")
        print(f"   URL: {item.url}")
        print(f"   Author: {item.user_id}")
        print(f"   Upvotes: {item.upvotes}")
        print(f"   Timestamp: {item.timestamp}")
        print("-" * 80)
