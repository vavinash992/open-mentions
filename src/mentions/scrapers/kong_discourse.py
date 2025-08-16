import secrets
from typing import Any, ClassVar, Optional

from mentions.scrapers.base import BaseScraper, ScrapedItem


class KongDiscourseScraper(BaseScraper):
    """
    Relevance-based scraper for Kong Nation forum (Discourse).
    Uses /search.json endpoint with pagination and extracts structured data.
    """

    BASE_URL: ClassVar[str] = "https://discuss.konghq.com"
    SEARCH_URL: ClassVar[str] = f"{BASE_URL}/search.json"
    PLATFORM: ClassVar[str] = "kong_forum"
    FILTER_MAP: ClassVar[dict[str, str]] = {"relevance": "relevance"}

    def __init__(self, use_free_proxies: bool = True, USER_PROXIES: Optional[list[str]] = None, max_pages: int = 3):
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.max_pages = max_pages

    def get_search_results(self, keyword: str, page: int) -> dict[str, Any]:
        headers = {"User-Agent": secrets.choice(self.USER_AGENTS)}
        params = {"q": keyword, "page": page}
        return self.call_url(self.SEARCH_URL, headers=headers, params=params) or {}

    def search(self, keyword: str, filter_by: str = "relevance") -> list[ScrapedItem]:
        self.validate_filter(filter_by)
        results: list[ScrapedItem] = []

        def fetch_page(page_num: int) -> tuple[list[dict], bool]:
            payload = self.get_search_results(keyword, page=page_num)
            topics = payload.get("topics", []) or []
            posts = payload.get("posts", []) or []
            for topic in topics:
                topic["_type"] = "thread"
            for post in posts:
                post["_type"] = "post"
            has_more = bool(topics or posts)
            return topics + posts, has_more

        for items in self.paginate_numbered(fetch_page, max_pages=self.max_pages):
            for item in items:
                if item.get("_type") == "thread":
                    url = f"{self.BASE_URL}/t/{item.get('slug')}/{item.get('id')}"
                    results.append(
                        ScrapedItem(
                            keyword=keyword,
                            platform=self.PLATFORM,
                            content=item.get("fancy_title") or item.get("title", ""),
                            url=url,
                            upvotes=item.get("posts_count"),  # Upvotes not explicitly exposed
                            sentiment=None,
                            mention_type="thread",
                            user_id=str(item.get("poster_user_id")),
                            user_profile_url=None,
                            timestamp=item.get("created_at"),
                            comments=item.get("posts_count"),
                        )
                    )
                elif item.get("_type") == "post":
                    topic_id = item.get("topic_id")
                    post_number = item.get("post_number")
                    slug = item.get("topic_slug") or ""
                    post_url = f"{self.BASE_URL}/t/{slug}/{topic_id}/{post_number}"
                    results.append(
                        ScrapedItem(
                            keyword=keyword,
                            platform=self.PLATFORM,
                            content=item.get("blurb", "")[:200],
                            url=post_url,
                            upvotes=item.get("like_count"),
                            sentiment=None,
                            mention_type="post",
                            user_id=item.get("username"),
                            user_profile_url=f"{self.BASE_URL}/u/{item.get('username')}"
                            if item.get("username")
                            else None,
                            timestamp=item.get("created_at"),
                            comments=None,
                        )
                    )
        return results


# -------- TESTING --------
if __name__ == "__main__":
    scraper = KongDiscourseScraper(max_pages=3)
    keyword = "plugin"
    results = scraper.search(keyword)

    print(f"\n Scraped {len(results)} items from Kong Forum matching '{keyword}'\n")
    for idx, item in enumerate(results, 1):
        print(f"{idx}. {item.mention_type.title()}: {item.content[:80]}...")
        print(f"   URL: {item.url}")
        print(f"   Author: {item.user_id}")
        print(f"   Upvotes: {item.upvotes}")
        print(f"   Timestamp: {item.timestamp}")
        print("-" * 80)
