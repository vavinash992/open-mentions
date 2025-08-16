# src/mentions/scrapers/csdn.py
import secrets
from datetime import datetime, timezone
from typing import Any, ClassVar, Optional

from mentions.scrapers.base import BaseScraper, ScrapedItem


class CsdnScraper(BaseScraper):
    """
    Scraper for CSDN using its public JSON search API.

    Endpoint:
        GET https://so.csdn.net/api/v3/search
    """

    URL: ClassVar[str] = "https://so.csdn.net/api/v3/search"
    PLATFORM: ClassVar[str] = "csdn"
    TM_MAP: ClassVar[dict[str, int]] = {"day": 1, "week": 7, "month": 30, "year": 365}

    def __init__(
        self,
        use_free_proxies: bool = True,
        USER_PROXIES: Optional[list[str]] = None,
        max_pages: int = 3,
        content_type: str = "all",
        sort_flag: int = 0,
    ):
        """
        Initialize the CSDN scraper.
        """
        super().__init__(use_free_proxies=use_free_proxies, USER_PROXIES=USER_PROXIES)
        self.max_pages = max_pages
        self.content_type = content_type
        self.sort_flag = sort_flag

    def _extract_items(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extracts result list from JSON response.
        """
        if not payload:
            return []
        if isinstance(payload.get("result_vos"), list):
            return payload["result_vos"]
        d = payload.get("data")
        if isinstance(d, dict) and isinstance(d.get("v"), list):
            return d["v"]
        return []

    def _fetch_page(self, keyword: str, filter_by: str, page: int) -> tuple[list[dict], bool]:
        headers = {
            "User-Agent": secrets.choice(self.USER_AGENTS),
            "Referer": "https://so.csdn.net/",
            "Origin": "https://so.csdn.net",
            "Accept": "application/json, text/plain, */*",
        }
        params: dict[str, Any] = {
            "q": keyword,
            "t": self.content_type,
            "s": self.sort_flag,
            "tm": self.TM_MAP.get(filter_by, 0),
            "p": page,
        }
        payload = self.call_url(self.URL, headers=headers, params=params) or {}
        return self._extract_items(payload), bool(payload)

    def search(self, keyword: str, filter_by: str) -> list[ScrapedItem]:
        """
        Search CSDN posts using keyword and time filter.
        """
        self.validate_filter(filter_by)
        results: list[ScrapedItem] = []

        for page_items in self.paginate_numbered(
            lambda p: self._fetch_page(keyword, filter_by, p), max_pages=self.max_pages
        ):
            for it in page_items:
                title = (it.get("title") or it.get("article_title") or it.get("name") or "").strip()
                url = (it.get("url") or it.get("article_url") or it.get("detail_url") or "").strip()
                if not url:
                    continue
                raw_ts = it.get("created_at") or it.get("pubtime") or it.get("published_at")
                ts_iso = (
                    datetime.fromtimestamp(int(raw_ts), tz=timezone.utc).isoformat()
                    if isinstance(raw_ts, (int, float))
                    else str(raw_ts)
                )
                author = it.get("nickname") or it.get("author") or it.get("user_name")
                results.append(
                    ScrapedItem(
                        keyword=keyword,
                        platform=self.PLATFORM,
                        content=title,
                        url=url,
                        upvotes=it.get("digg") or it.get("score"),
                        user_id=author,
                        user_profile_url=None,
                        timestamp=ts_iso,
                        mention_type="post",
                        sentiment=None,
                        comments=it.get("comment_count"),
                    )
                )
        return results


# -------------- TEST --------------
if __name__ == "__main__":
    scraper = CsdnScraper(max_pages=5, content_type="all")
    items = scraper.search("ToolJet", "month")
    print(f"\n CSDN results: {len(items)}\n")
    for i, it in enumerate(items[:10], 1):
        print(f"{i}. {it.content[:90]} — {it.url} — {it.timestamp}")
