"""Search Orchestrator Service for coordinating multi-platform scraping and classification."""

import asyncio
from typing import Optional

from loguru import logger
from sqlalchemy import select

from mentions.db.session import async_session_maker
from mentions.models.database import Mention
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
        workspace_id: Optional[str] = None,
    ) -> list[ScrapedItem]:
        """
        Search all available platforms concurrently and classify results.

        Args:
            company_name: The company name to search for.
            filter_by: Time filter (e.g., 'day', 'week', 'month', 'year').
            max_results_per_platform: Maximum results to fetch per platform.
            workspace_id: Optional workspace ID for multi-tenant isolation.

        Returns:
            List of classified ScrapedItem objects (only relevant ones).
        """
        logger.info(f"Starting search for '{company_name}' across all platforms with filter '{filter_by}'")
        if workspace_id:
            logger.info(f"Workspace ID: '{workspace_id}'")

        # Initialize all scrapers
        scrapers = [
            ("reddit", RedditScraper()),
            ("hackernews", HackerNewsScraper()),
            ("devto", DevtoScraper()),
            ("stackexchange", StackExchangeScraper()),
        ]

        # Run all scrapers concurrently using asyncio
        tasks = [
            self._scrape_platform(name, scraper, company_name, filter_by, max_results_per_platform)
            for name, scraper in scrapers
        ]

        # Wait for all scrapers to complete
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and handle exceptions
        items: list[ScrapedItem] = []
        for i, result in enumerate(all_results):
            platform_name = scrapers[i][0]
            if isinstance(result, Exception):
                logger.error(f"Error scraping {platform_name}: {result}")
                continue
            if isinstance(result, list):
                items.extend(result)
            else:
                logger.warning(f"Unexpected result type from {platform_name}: {type(result)}")

        logger.info(f"Scraped {len(items)} total items across all platforms")

        if not items:
            logger.info("No items to process")
            return []

        # Check database for existing URLs to avoid re-processing
        new_items, existing_urls = await self._filter_existing_urls(items, workspace_id)

        logger.info(f"Found {len(existing_urls)} existing mentions in database, {len(new_items)} new items to process")

        # Process only new items through LLM processor for classification and summarization
        # This enriches items with: relevance_score, is_relevant, sentiment, emotion, summary
        if new_items:
            logger.info(f"Processing {len(new_items)} new mentions through LLM classifier...")
            classified_items = await self.llm_processor.process_mentions(new_items, company_name)
        else:
            logger.info("No new items to classify")
            classified_items = []

        # Save new classified items to database
        if classified_items:
            await self._save_to_database(classified_items, workspace_id)
            logger.info(f"Saved {len(classified_items)} new mentions to database")

        # Fetch existing items from database to include in results
        existing_items = await self._fetch_existing_items(existing_urls, company_name, workspace_id)

        # Combine new and existing items
        all_items = classified_items + existing_items

        # Filter to only relevant items
        relevant_items = [item for item in all_items if item.is_relevant]

        logger.info(f"After classification: {len(relevant_items)} relevant items out of {len(all_items)} total")

        return relevant_items

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

    async def _filter_existing_urls(
        self, items: list[ScrapedItem], workspace_id: Optional[str] = None
    ) -> tuple[list[ScrapedItem], list[str]]:
        """
        Filter out items that already exist in the database.

        Args:
            items: List of ScrapedItem objects to check.
            workspace_id: Optional workspace ID to scope the check.

        Returns:
            Tuple of (new_items, existing_urls) where new_items are items not in DB,
            and existing_urls is a list of URLs that already exist.
        """
        if not items:
            return [], []

        urls = [item.url for item in items]

        async with async_session_maker() as session:
            # Query for existing URLs
            statement = select(Mention.url).where(Mention.url.in_(urls))
            if workspace_id:
                statement = statement.where(Mention.workspace_id == workspace_id)
            result = await session.execute(statement)
            existing_urls = {row[0] for row in result.all()}

        # Filter out existing items
        new_items = [item for item in items if item.url not in existing_urls]

        return new_items, list(existing_urls)

    async def _save_to_database(self, items: list[ScrapedItem], workspace_id: Optional[str] = None) -> None:
        """
        Save classified items to the database.

        Since url is primary key, duplicates will raise IntegrityError which we catch and skip.

        Args:
            items: List of ScrapedItem objects to save.
            workspace_id: Workspace ID to associate with mentions.
        """
        if not items:
            return

        # Default workspace_id if not provided
        if workspace_id is None:
            workspace_id = "default"

        saved_count = 0
        async with async_session_maker() as session:
            for item in items:
                try:
                    # Convert ScrapedItem to Mention with workspace_id
                    mention = Mention.from_scraped_item(item, workspace_id)
                    session.add(mention)
                    await session.commit()
                    saved_count += 1
                except Exception as e:
                    # Skip duplicates (IntegrityError) or other errors
                    await session.rollback()
                    logger.debug(f"Skipping duplicate or error for {item.url}: {e}")
                    continue

        logger.info(f"Saved {saved_count} new mentions to database")

    async def _fetch_existing_items(
        self, urls: list[str], company_name: str, workspace_id: Optional[str] = None
    ) -> list[ScrapedItem]:
        """
        Fetch existing items from database that match the company search.

        Args:
            urls: List of URLs that exist in database.
            company_name: Company name to filter by (only return relevant items).
            workspace_id: Optional workspace ID to scope the fetch.

        Returns:
            List of ScrapedItem objects from database.
        """
        if not urls:
            return []

        async with async_session_maker() as session:
            # Fetch mentions from database
            statement = (
                select(Mention)
                .where(Mention.url.in_(urls))
                .where(Mention.keyword == company_name)
                .where(Mention.is_relevant == True)  # noqa: E712
            )
            if workspace_id:
                statement = statement.where(Mention.workspace_id == workspace_id)
            result = await session.execute(statement)
            mentions = result.scalars().all()

        # Convert Mention models back to ScrapedItem
        return [mention.to_scraped_item() for mention in mentions]


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
