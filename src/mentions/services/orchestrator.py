"""Search Orchestrator Service for coordinating multi-platform scraping and classification."""

import asyncio
from typing import Optional

from loguru import logger
from sqlalchemy import select

from mentions.db.session import async_session_maker
from mentions.models.database import Mention, WorkspaceMention
from mentions.scrapers.base import ScrapedItem
from mentions.scrapers.devto import DevtoScraper
from mentions.scrapers.hacker_news import HackerNewsScraper
from mentions.scrapers.reddit import RedditScraper
from mentions.scrapers.stack_exchange import StackExchangeScraper
from mentions.services.llm_processor import LLMProcessor


class SearchOrchestrator:
    """Orchestrator for running all scrapers concurrently and classifying results."""

    def __init__(self, llm_processor: Optional[LLMProcessor] = None):
        """
        Initialize the Search Orchestrator.

        Args:
            llm_processor: Optional LLMProcessor instance. If None, creates a new one.
        """
        self.llm_processor = llm_processor or LLMProcessor()

    async def search_all_platforms(
        self,
        company_name: str,
        filter_by: str = "week",
        max_results_per_platform: int = 50,
        workspace_id: str = "",
        include_existing: bool = True,
    ) -> list[ScrapedItem]:
        """
        Search all available platforms concurrently and classify results.

        Args:
            company_name: The company name to search for.
            filter_by: Time filter (e.g., 'day', 'week', 'month', 'year').
            max_results_per_platform: Maximum results to fetch per platform.
            workspace_id: Workspace ID for multi-tenant isolation.
            include_existing: If True, return all relevant mentions for this search.
                If False, return only newly-linked mentions for this workspace+keyword.

        Returns:
            List of classified ScrapedItem objects (only relevant ones).
        """
        logger.info(f"Starting search for '{company_name}' across all platforms with filter '{filter_by}'")
        if workspace_id:
            logger.info(f"Workspace ID: '{workspace_id}'")

        # Initialize all scrapers
        # Optimized: max_pages=1 for speed, proxies enabled to avoid rate limits
        scrapers = [
            ("reddit", RedditScraper(use_free_proxies=True, max_pages=1)),
            ("hackernews", HackerNewsScraper(use_free_proxies=True, max_pages=1)),
            ("devto", DevtoScraper(use_free_proxies=True, max_pages=1)),
            ("stackexchange", StackExchangeScraper(use_free_proxies=True, max_pages=1)),
        ]

        if not workspace_id:
            # The API layer should enforce this; keep a safe no-op fallback.
            return []

        tasks = [
            self._process_platform_pipeline(
                platform_name=name,
                scraper=scraper,
                keyword=company_name,
                filter_by=filter_by,
                max_results_per_platform=max_results_per_platform,
                workspace_id=workspace_id,
                include_existing=include_existing,
            )
            for name, scraper in scrapers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        linked_items: list[ScrapedItem] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error processing platform pipeline: {result}")
                continue
            linked_items.extend(result)

        logger.info(f"Returning {len(linked_items)} relevant mention(s) for workspace '{workspace_id}'")
        return linked_items

    async def _process_platform_pipeline(
        self,
        *,
        platform_name: str,
        scraper,
        keyword: str,
        filter_by: str,
        max_results_per_platform: int,
        workspace_id: str,
        include_existing: bool,
    ) -> list[ScrapedItem]:
        """
        Run the full pipeline for a single platform.
        """
        try:
            items = await self._scrape_platform(
                platform_name,
                scraper,
                keyword,
                filter_by,
                max_results_per_platform,
            )
        except Exception as e:
            logger.error(f"Error scraping {platform_name}: {e}")
            return []

        if not items:
            return []

        new_items, existing_urls = await self._split_by_global_dedup(items)
        logger.info(
            f"[{platform_name}] Global dedup: {len(existing_urls)} existing, {len(new_items)} new"
        )

        if new_items:
            logger.info(f"[{platform_name}] Classifying {len(new_items)} new item(s) with LLM...")
            classified_new_items = await self.llm_processor.process_mentions(new_items, keyword)
            await self._save_mentions_global(classified_new_items)

        urls_to_link = [item.url for item in items]
        linked_items = await self._link_workspace_mentions(
            workspace_id=workspace_id,
            keyword=keyword,
            urls=urls_to_link,
            include_existing=include_existing,
        )

        logger.info(
            f"[{platform_name}] Linked {len(linked_items)} relevant mention(s) for '{keyword}'"
        )
        return linked_items

    async def _scrape_platform(
        self,
        platform_name: str,
        scraper,
        company_name: str,
        filter_by: str,
        max_results: int,
    ) -> list[ScrapedItem]:
        """
        Scrape a single platform (run in thread pool since scrapers are synchronous).

        Args:
            platform_name: Name of the platform.
            scraper: Scraper instance.
            company_name: Company name to search for.
            filter_by: Time filter.
            max_results: Maximum results to fetch.

        Returns:
            List of ScrapedItem objects from this platform.
        """
        try:
            logger.info(f"Scraping {platform_name} for '{company_name}'...")

            # Run synchronous scraper in thread pool
            loop = asyncio.get_event_loop()
            items = await loop.run_in_executor(
                None,
                lambda: scraper.search(company_name, filter_by),
            )

            # Limit results if needed
            if len(items) > max_results:
                items = items[:max_results]

            logger.info(f"Scraped {len(items)} items from {platform_name}")
        except Exception as e:
            logger.error(f"Error scraping {platform_name}: {e}")
            return []
        else:
            return items

    async def _split_by_global_dedup(self, items: list[ScrapedItem]) -> tuple[list[ScrapedItem], list[str]]:
        """
        Split items into (new_items, existing_urls) using global URL deduplication.

        If a URL already exists in Mention table, we won't call the LLM again.
        """
        if not items:
            return [], []

        # Deduplicate items by URL upfront (keep first occurrence)
        items_by_url = {item.url: item for item in items}
        unique_urls = list(items_by_url.keys())

        async with async_session_maker() as session:
            statement = select(Mention.url).where(Mention.url.in_(unique_urls))
            result = await session.execute(statement)
            existing_urls = {row[0] for row in result.all()}

        # Filter out existing URLs in single pass
        new_items = [item for url, item in items_by_url.items() if url not in existing_urls]

        return new_items, sorted(existing_urls)

    async def _save_mentions_global(self, items: list[ScrapedItem]) -> None:
        """
        Save newly classified mentions globally (one row per URL).
        """
        if not items:
            return

        async with async_session_maker() as session:
            try:
                mentions = [Mention.from_scraped_item(item) for item in items]
                session.add_all(mentions)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.debug("Skipping batch mention save due to error: %s", e)

    async def _link_workspace_mentions(
        self,
        *,
        workspace_id: str,
        keyword: str,
        urls: list[str],
        include_existing: bool,
    ) -> list[ScrapedItem]:
        """
        Ensure WorkspaceMention links exist for relevant mentions for this workspace+keyword.

        Returns ScrapedItem list (relevant only) for API responses.
        """
        if not urls:
            return []

        # Fetch global mentions for these URLs (relevant only)
        async with async_session_maker() as session:
            stmt = select(Mention).where(Mention.url.in_(urls)).where(Mention.is_relevant == True)  # noqa: E712
            result = await session.execute(stmt)
            mentions = result.scalars().all()

        if not mentions:
            return []

        # Determine which links already exist for this workspace+keyword
        async with async_session_maker() as session:
            existing_stmt = (
                select(WorkspaceMention.mention_url)
                .where(WorkspaceMention.workspace_id == workspace_id)
                .where(WorkspaceMention.keyword == keyword)
                .where(WorkspaceMention.mention_url.in_([m.url for m in mentions]))
            )
            existing_result = await session.execute(existing_stmt)
            existing_links = {row[0] for row in existing_result.all()}

        new_links = [m for m in mentions if m.url not in existing_links]

        # Insert new workspace links (idempotent via PK)
        if new_links:
            async with async_session_maker() as session:
                try:
                    links = [
                        WorkspaceMention(workspace_id=workspace_id, mention_url=m.url, keyword=keyword)
                        for m in new_links
                    ]
                    session.add_all(links)
                    await session.commit()
                except Exception:
                    await session.rollback()

        if include_existing:
            return [m.to_scraped_item(keyword=keyword) for m in mentions]
        return [m.to_scraped_item(keyword=keyword) for m in new_links]


async def search_all_platforms(
    company_name: str,
    filter_by: str = "week",
    max_results_per_platform: int = 50,
    workspace_id: Optional[str] = None,
) -> list[ScrapedItem]:
    """
    Convenience function to search all platforms and classify results.

    Args:
        company_name: The company name to search for.
        filter_by: Time filter (e.g., 'day', 'week', 'month', 'year').
        max_results_per_platform: Maximum results to fetch per platform.
        workspace_id: Optional workspace ID for multi-tenant isolation.

    Returns:
        List of classified ScrapedItem objects (only relevant ones).
    """
    orchestrator = SearchOrchestrator()
    return await orchestrator.search_all_platforms(company_name, filter_by, max_results_per_platform, workspace_id)
