"""Product Hunt scraper using the public website search."""

import secrets
from typing import Any, ClassVar, Optional

from mentions.scrapers.base import BaseScraper, ScrapedItem


class ProductHuntScraper(BaseScraper):
    """
    Scraper for Product Hunt posts via the public search endpoint.

    Product Hunt doesn't have a fully public free API with search,
    so we use the undocumented frontend search endpoint that returns JSON.

    Pagination:
        Cursor-based via `page` parameter (1-based).
    """

    URL = "https://www.producthunt.com/frontend/graphql"
    FILTER_MAP: ClassVar[dict[str, str]] = {
        "day": "daily",
        "week": "weekly",
        "month": "monthly",
        "year": "yearly",
    }

    def __init__(
        self,
        use_free_proxies: bool = True,
        USER_PROXIES: Optional[list[str]] = None,
        max_pages: int = 2,
    ):
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.max_pages = max_pages
        # Fall back to a simpler REST search if GraphQL doesn't work
        self.search_url = "https://www.producthunt.com/search/posts"

    def get_data(self, keyword: str, filter_by: str, page: int) -> list[dict[str, Any]]:
        """Fetch search results from Product Hunt's search page (returns HTML parsed as JSON isn't always available)."""
        headers = {
            "User-Agent": secrets.choice(self.USER_AGENTS),
            "Accept": "application/json",
        }
        params: dict[str, Any] = {
            "q": keyword,
            "page": page,
        }
        # Try the JSON search endpoint
        payload = self.call_url(self.search_url, headers=headers, params=params)
        if payload and isinstance(payload, list):
            return payload
        if payload and isinstance(payload, dict):
            return payload.get("results", payload.get("posts", []))
        return []

    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        self.validate_filter(filter_by)

        results: list[ScrapedItem] = []
        for page_num in range(1, self.max_pages + 1):
            items = self.get_data(keyword, filter_by, page=page_num)
            if not items:
                break

            for item in items:
                name = item.get("name", "")
                tagline = item.get("tagline", "")
                content = f"{name}: {tagline}" if tagline else name

                results.append(
                    ScrapedItem(
                        keyword=keyword,
                        platform="producthunt",
                        content=content,
                        url=item.get(
                            "url",
                            item.get("discussion_url", f"https://www.producthunt.com/posts/{item.get('slug', '')}"),
                        ),
                        upvotes=item.get("votes_count", item.get("vote_count", 0)),
                        user_id=None,
                        user_profile_url=None,
                        timestamp=item.get("created_at", item.get("day", "")),
                        mention_type="product",
                        sentiment=None,
                        comments=item.get("comments_count", item.get("review_count", 0)),
                    )
                )
        return results


if __name__ == "__main__":
    scraper = ProductHuntScraper()
    results = scraper.search("AI", "week")
    print(f"\nScraped {len(results)} items from Product Hunt for 'AI'\n")
    for idx, item in enumerate(results[:5], 1):
        print(f"{idx}. {item.content[:100]}...")
        print(f"   URL: {item.url}")
        print("-" * 80)
