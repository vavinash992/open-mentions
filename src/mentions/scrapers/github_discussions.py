"""GitHub Discussions/Issues scraper using the public search API."""

import secrets
from typing import Any, ClassVar, Optional

from mentions.scrapers.base import BaseScraper, ScrapedItem


class GitHubDiscussionsScraper(BaseScraper):
    """
    Scraper for GitHub issues and discussions via the public search API.

    Uses: GET https://api.github.com/search/issues?q=<keyword>
    Rate limit: 10 requests/min without authentication.

    Pagination:
        Uses `page` (1-based) and `per_page` query params.
    """

    URL = "https://api.github.com/search/issues"
    FILTER_MAP: ClassVar[dict[str, str]] = {
        "day": "1",
        "week": "7",
        "month": "30",
        "year": "365",
    }

    def __init__(
        self,
        use_free_proxies: bool = True,
        USER_PROXIES: Optional[list[str]] = None,
        max_pages: int = 3,
        per_page: int = 30,
    ):
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.max_pages = max_pages
        self.per_page = max(1, min(per_page, 100))

    def _build_date_qualifier(self, filter_by: str) -> str:
        """Build GitHub date qualifier like 'created:>2024-01-01'."""
        from datetime import datetime, timedelta, timezone

        days_back = int(self.FILTER_MAP.get(filter_by, "7"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        return f"created:>{cutoff.strftime('%Y-%m-%d')}"

    def get_data(self, keyword: str, filter_by: str, page: int) -> dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": secrets.choice(self.USER_AGENTS),
        }
        date_qualifier = self._build_date_qualifier(filter_by)
        params: dict[str, Any] = {
            "q": f"{keyword} {date_qualifier}",
            "sort": "updated",
            "order": "desc",
            "per_page": self.per_page,
            "page": page,
        }
        payload = self.call_url(self.URL, headers=headers, params=params)
        return payload or {}

    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        self.validate_filter(filter_by)

        def fetch_page(page_num: int) -> tuple[list[dict], bool]:
            data = self.get_data(keyword, filter_by, page=page_num)
            items = data.get("items", []) or []
            total = data.get("total_count", 0)
            has_more = bool(items) and (page_num * self.per_page < total)
            return items, has_more

        results: list[ScrapedItem] = []
        for items in self.paginate_numbered(fetch_page, max_pages=self.max_pages):
            for item in items:
                title = item.get("title", "")
                body = (item.get("body") or "")[:500]
                content = f"{title}\n{body}" if body else title

                user = item.get("user", {}) or {}
                reactions = item.get("reactions", {}) or {}
                upvotes = reactions.get("+1", 0) or 0

                results.append(
                    ScrapedItem(
                        keyword=keyword,
                        platform="github",
                        content=content,
                        url=item.get("html_url", ""),
                        upvotes=upvotes,
                        user_id=user.get("login"),
                        user_profile_url=user.get("html_url"),
                        timestamp=item.get("created_at"),
                        mention_type="issue" if "/issues/" in item.get("html_url", "") else "discussion",
                        sentiment=None,
                        comments=item.get("comments", 0),
                    )
                )
        return results


if __name__ == "__main__":
    scraper = GitHubDiscussionsScraper()
    results = scraper.search("OpenAI", "week")
    print(f"\nScraped {len(results)} items from GitHub for 'OpenAI'\n")
    for idx, item in enumerate(results[:5], 1):
        print(f"{idx}. {item.content[:100]}...")
        print(f"   URL: {item.url}")
        print("-" * 80)
