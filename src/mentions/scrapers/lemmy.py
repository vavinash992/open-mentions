# lemmy.py
import secrets
from collections.abc import Iterable
from typing import Any, ClassVar, Optional

from mentions.scrapers.base import BaseScraper, ScrapedItem


class LemmyScraper(BaseScraper):
    """
    Scraper for Lemmy (federated Reddit-like) using the public v3 API.

    Endpoint:
        GET {instance_base}/api/v3/search

    Core params used:
        q              : search term
        type_          : 'Posts'
        page           : 1-based page number
        limit          : results per page (API caps at ~50)
        sort           : one of ['TopDay','TopWeek','TopMonth','TopYear','TopAll','New','Hot',...]
        community_name : optional community to restrict results (e.g., 'programming')
        listing_type   : 'All' (default)
    """

    PLATFORM: ClassVar[str] = "lemmy"
    FILTER_MAP: ClassVar[dict[str, str]] = {
        "day": "TopDay",
        "week": "TopWeek",
        "month": "TopMonth",
        "year": "TopYear",
    }

    def __init__(
        self,
        instance_base: str = "https://lemmy.world",
        use_free_proxies: bool = True,
        USER_PROXIES: Optional[list[str]] = None,
        max_pages: int = 3,
        limit: int = 50,
        communities: Optional[Iterable[str]] = None,
    ):
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.instance_base = instance_base.rstrip("/")
        self.max_pages = max(1, max_pages)
        self.limit = max(1, min(limit, 50))
        self.communities = list(communities or [])

    def get_data(
        self,
        keyword: str,
        filter_by: str,
        page: int,
        community_name: Optional[str] = None,
    ) -> dict[str, Any] | None:
        headers = {"User-Agent": secrets.choice(self.USER_AGENTS)}
        params: dict[str, Any] = {
            "q": keyword,
            "type_": "Posts",
            "page": page,
            "limit": self.limit,
            "sort": self.FILTER_MAP.get(filter_by, "TopAll"),
            "listing_type": "All",
        }
        if community_name:
            params["community_name"] = community_name

        url = f"{self.instance_base}/api/v3/search"
        return self.call_url(url=url, headers=headers, params=params)

    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        """
        Search Lemmy posts for a keyword with pagination and optional community scoping.

        Args:
            keyword: Search term.
            filter_by: One of {'day','week','month','year'}.

        Returns:
            list[ScrapedItem]: Unified, structured results.
        """
        self.validate_filter(filter_by)
        targets = self.communities or [None]
        results: list[ScrapedItem] = []

        for community in targets:

            def fetch_page(page: int, community=community) -> tuple[list[dict], bool]:
                data = (
                    self.get_data(
                        keyword=keyword,
                        filter_by=filter_by,
                        page=page,
                        community_name=community,
                    )
                    or {}
                )
                posts = data.get("posts") or []

                # Lemmy search doesn't return has_more; infer it by whether page is full
                has_more = len(posts) == self.limit
                return posts, has_more

            for page_posts in self.paginate_numbered(fetch_page, max_pages=self.max_pages):
                for row in page_posts:
                    post = row.get("post") or {}
                    creator = row.get("creator") or {}
                    counts = row.get("counts") or {}

                    url = (
                        post.get("ap_id")
                        or post.get("url")
                        or (f"{self.instance_base}/post/{post.get('id')}" if post.get("id") else None)
                    )
                    if not url:
                        continue

                    results.append(
                        ScrapedItem(
                            keyword=keyword,
                            platform=self.PLATFORM,
                            content=post.get("name") or "",
                            url=url,
                            upvotes=counts.get("score"),
                            user_id=creator.get("name"),
                            user_profile_url=(
                                f"{self.instance_base}/u/{creator.get('name')}" if creator.get("name") else None
                            ),
                            timestamp=post.get("published"),
                            mention_type="post",
                            sentiment=None,
                            comments=counts.get("comments"),
                        )
                    )
        return results


# -------------- TEST --------------
if __name__ == "__main__":
    scraper = LemmyScraper(
        instance_base="https://lemmy.world",
        max_pages=5,
        limit=50,
    )
    keyword = "AI"
    filter_by = "month"

    results = scraper.search(keyword, filter_by)
    print(f"\n Scraped {len(results)} posts from Lemmy for keyword '{keyword}'\n")

    for idx, item in enumerate(results, 1):
        print(f"--- Result #{idx} ---")
        print(f"Keyword         : {item.keyword}")
        print(f"Platform        : {item.platform}")
        print(f"Content         : {item.content}")
        print(f"URL             : {item.url}")
        print(f"Upvotes         : {item.upvotes}")
        print(f"User ID         : {item.user_id}")
        print(f"User Profile URL: {item.user_profile_url}")
        print(f"Timestamp       : {item.timestamp}")
        print(f"Mention Type    : {item.mention_type}")
        print(f"Sentiment       : {item.sentiment}")
        print(f"Comments        : {item.comments}")
        print("-" * 80)
