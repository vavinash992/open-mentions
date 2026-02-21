"""Medium scraper using the public search/tag endpoints."""

import secrets
from typing import Any, ClassVar, Optional

from loguru import logger

from mentions.scrapers.base import BaseScraper, ScrapedItem


class MediumScraper(BaseScraper):
    """
    Scraper for Medium articles via the public tag/search endpoints.

    Uses Medium's JSON API endpoints that return article metadata.
    The response is wrapped in an anti-hijacking prefix that must be stripped.

    Pagination:
        Uses `page` parameter (0-based).
    """

    URL = "https://medium.com/search"
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
        max_pages: int = 2,
    ):
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.max_pages = max_pages

    def _search_via_tag_feed(self, keyword: str) -> list[dict[str, Any]]:
        """Use Medium's tag feed as a fallback search approach."""
        tag = keyword.lower().replace(" ", "-")
        url = f"https://medium.com/tag/{tag}/latest"
        headers = {
            "User-Agent": secrets.choice(self.USER_AGENTS),
            "Accept": "application/json",
        }
        payload = self.call_url(url, headers=headers, params={"format": "json"})
        if not payload or not isinstance(payload, dict):
            return []
        # Medium wraps responses — extract posts
        return list(payload.get("payload", {}).get("references", {}).get("Post", {}).values())

    def _search_via_api(self, keyword: str, page: int) -> list[dict[str, Any]]:
        """Use Medium's search endpoint."""
        headers = {
            "User-Agent": secrets.choice(self.USER_AGENTS),
            "Accept": "application/json",
        }
        params: dict[str, Any] = {
            "q": keyword,
            "format": "json",
            "page": page,
        }
        # Medium returns ])}while(1);</x> prefix before JSON
        import requests

        try:
            proxy = None
            if self.proxies:
                import random

                proxy = {"http": random.choice(self.proxies)}  # noqa: S311
            response = requests.get(
                self.URL,
                headers=headers,
                params=params,
                proxies=proxy,
                timeout=30,
            )
            response.raise_for_status()
            text = response.text
            # Strip Medium's anti-hijacking prefix
            if text.startswith("])}while(1);</x>"):
                text = text[len("])}while(1);</x>") :]
            import json

            data = json.loads(text)
            posts = data.get("payload", {}).get("value", [])
            return posts if isinstance(posts, list) else []
        except Exception as e:
            logger.warning(f"Medium search failed: {e}")
            return []

    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        self.validate_filter(filter_by)

        results: list[ScrapedItem] = []
        all_posts: list[dict] = []

        # Try API search first
        for page_num in range(self.max_pages):
            posts = self._search_via_api(keyword, page=page_num)
            if posts:
                all_posts.extend(posts)
            else:
                break

        # Fallback to tag feed if API search returned nothing
        if not all_posts:
            all_posts = self._search_via_tag_feed(keyword)

        for item in all_posts:
            title = item.get("title", "")
            subtitle = item.get("virtuals", {}).get("subtitle", "") if isinstance(item.get("virtuals"), dict) else ""
            content = f"{title}\n{subtitle}" if subtitle else title

            post_id = item.get("id", item.get("uniqueSlug", ""))
            slug = item.get("uniqueSlug", post_id)
            url = f"https://medium.com/p/{slug}" if slug else ""

            # Extract engagement metrics
            virtuals = item.get("virtuals", {}) if isinstance(item.get("virtuals"), dict) else {}
            claps = virtuals.get("totalClapCount", item.get("clapCount", 0)) or 0
            responses = virtuals.get("responsesCreatedCount", item.get("responsesCount", 0)) or 0

            # Extract author
            creator_id = item.get("creatorId", "")

            # Extract timestamp (Medium uses milliseconds)
            first_published = item.get("firstPublishedAt") or item.get("createdAt")
            timestamp = None
            if first_published and isinstance(first_published, int):
                from datetime import datetime, timezone

                timestamp = datetime.fromtimestamp(first_published / 1000, tz=timezone.utc).isoformat()

            results.append(
                ScrapedItem(
                    keyword=keyword,
                    platform="medium",
                    content=content,
                    url=url,
                    upvotes=claps,
                    user_id=creator_id if creator_id else None,
                    user_profile_url=f"https://medium.com/@{creator_id}" if creator_id else None,
                    timestamp=timestamp,
                    mention_type="article",
                    sentiment=None,
                    comments=responses,
                )
            )
        return results


if __name__ == "__main__":
    scraper = MediumScraper()
    results = scraper.search("artificial intelligence", "week")
    print(f"\nScraped {len(results)} articles from Medium for 'artificial intelligence'\n")
    for idx, item in enumerate(results[:5], 1):
        print(f"{idx}. {item.content[:100]}...")
        print(f"   URL: {item.url}")
        print(f"   Claps: {item.upvotes}")
        print("-" * 80)
