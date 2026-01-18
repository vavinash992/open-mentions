"""Search Orchestrator Service for coordinating multi-platform scraping and classification."""

import asyncio
from typing import Optional

from loguru import logger

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
    ) -> list[ScrapedItem]:
        """
        Search all available platforms concurrently and classify results.

        Args:
            company_name: The company name to search for.
            filter_by: Time filter (e.g., 'day', 'week', 'month', 'year').
            max_results_per_platform: Maximum results to fetch per platform.

        Returns:
            List of classified ScrapedItem objects (only relevant ones).
        """
        logger.info(f"Starting search for '{company_name}' across all platforms with filter '{filter_by}'")

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

        # Process all raw results through LLM processor for classification and summarization
        # This enriches items with: relevance_score, is_relevant, sentiment, emotion, summary
        if items:
            logger.info(f"Processing {len(items)} raw mentions through LLM classifier...")
            classified_items = await self.llm_processor.process_mentions(items, company_name)
        else:
            logger.info("No items to classify")
            classified_items = []

        # Filter to only relevant items
        relevant_items = [item for item in classified_items if item.is_relevant]

        logger.info(f"After classification: {len(relevant_items)} relevant items out of {len(classified_items)} total")

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


async def search_all_platforms(
    company_name: str,
    filter_by: str = "week",
    max_results_per_platform: int = 50,
) -> list[ScrapedItem]:
    """
    Convenience function to search all platforms and classify results.

    Args:
        company_name: The company name to search for.
        filter_by: Time filter (e.g., 'day', 'week', 'month', 'year').
        max_results_per_platform: Maximum results to fetch per platform.

    Returns:
        List of classified ScrapedItem objects (only relevant ones).
    """
    orchestrator = SearchOrchestrator()
    return await orchestrator.search_all_platforms(company_name, filter_by, max_results_per_platform)
