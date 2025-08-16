# src/mentions/scrapers/wanikani_forum_scraper.py
import secrets
from typing import Any, ClassVar, Optional

from mentions.scrapers.base import BaseScraper, ScrapedItem


class WaniKaniForumScraper(BaseScraper):
    """
    Scraper for WaniKani Community Forums via Discourse search API.
    """

    PLATFORM: ClassVar[str] = "wanikani_forum"
    BASE_URL: ClassVar[str] = "https://community.wanikani.com"
    SEARCH_URL: ClassVar[str] = f"{BASE_URL}/search.json"
    FILTER_MAP: ClassVar[dict[str, str]] = {"relevance": "relevance"}

    def __init__(
        self,
        use_free_proxies: bool = True,
        USER_PROXIES: Optional[list[str]] = None,
        max_pages: int = 3,
    ):
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.max_pages = max_pages

    def get_search_results(self, keyword: str, page: int) -> dict[str, Any]:
        headers = {"User-Agent": secrets.choice(self.USER_AGENTS)}
        params = {"q": keyword, "page": page, "expanded": "true"}
        return self.call_url(self.SEARCH_URL, headers=headers, params=params) or {}

    def _fetch_page(self, keyword: str, page_num: int) -> tuple[list[dict], bool]:
        payload = self.get_search_results(keyword, page=page_num)
        topics = payload.get("topics") or []
        posts = payload.get("posts") or []

        topic_index = {
            t.get("id"): {
                "slug": t.get("slug"),
                "posts_count": t.get("posts_count"),
            }
            for t in topics
            if isinstance(t.get("id"), int)
        }
        for p in posts:
            p["_topic_meta"] = topic_index.get(p.get("topic_id"))

        for t in topics:
            t["_type"] = "thread"
        for p in posts:
            p["_type"] = "post"

        return (topics + posts), bool(topics or posts)

    def search(self, keyword: str, filter_by: str = "relevance") -> list[ScrapedItem]:
        self.validate_filter(filter_by)
        results: list[ScrapedItem] = []

        for items in self.paginate_numbered(lambda p: self._fetch_page(keyword, p), max_pages=self.max_pages):
            for item in items:
                if item.get("_type") == "thread":
                    slug, tid = item.get("slug"), item.get("id")
                    url = f"{self.BASE_URL}/t/{slug}/{tid}" if slug and tid else None
                    if not url:
                        continue
                    results.append(
                        ScrapedItem(
                            keyword=keyword,
                            platform=self.PLATFORM,
                            content=(item.get("fancy_title") or item.get("title") or "").strip(),
                            url=url,
                            upvotes=None,
                            sentiment=None,
                            mention_type="thread",
                            user_id=str(item.get("poster_user_id")) if item.get("poster_user_id") is not None else None,
                            user_profile_url=None,
                            timestamp=item.get("created_at"),
                            comments=item.get("posts_count"),
                        )
                    )

                elif item.get("_type") == "post":
                    topic_id = item.get("topic_id")
                    post_number = item.get("post_number")
                    slug = item.get("topic_slug") or (item.get("_topic_meta") or {}).get("slug") or ""
                    post_url = (
                        f"{self.BASE_URL}/t/{slug}/{topic_id}/{post_number}"
                        if slug and topic_id and post_number
                        else f"{self.BASE_URL}/t/{topic_id}"
                    )
                    blurb = (item.get("blurb") or item.get("raw") or item.get("cooked") or "").strip()[:200]
                    comments = (item.get("_topic_meta") or {}).get("posts_count")
                    results.append(
                        ScrapedItem(
                            keyword=keyword,
                            platform=self.PLATFORM,
                            content=blurb,
                            url=post_url,
                            upvotes=item.get("like_count"),
                            sentiment=None,
                            mention_type="post",
                            user_id=item.get("username"),
                            user_profile_url=f"{self.BASE_URL}/u/{item.get('username')}"
                            if item.get("username")
                            else None,
                            timestamp=item.get("created_at"),
                            comments=comments,
                        )
                    )
        return results


if __name__ == "__main__":
    scraper = WaniKaniForumScraper(max_pages=3)
    keyword = "API"
    filter_by = "relevance"
    results = scraper.search(keyword, filter_by)
    print(f"\n Scraped {len(results)} items from WaniKani forums relevant to '{keyword}'\n")
    for idx, item in enumerate(results, 1):
        print(f"{idx}. {item.mention_type.title()}: {item.content[:80]}...")
        print(f"   URL: {item.url}")
        print(f"   Author: {item.user_id}")
        print(f"   Upvotes: {item.upvotes}")
        print(f"   Comments: {item.comments}")
        print(f"   Timestamp: {item.timestamp}")
        print("-" * 80)
