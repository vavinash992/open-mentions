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

        # Classify all items concurrently
        classified_items = await self._classify_items(items, company_name)

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

    async def _classify_items(self, items: list[ScrapedItem], company_name: str) -> list[ScrapedItem]:
        """
        Classify all items concurrently using LLM.

        First pass: Basic relevance check only (saves tokens).
        Second pass: Detailed analysis (emotion, summary) only for relevant items.

        Args:
            items: List of ScrapedItem objects to classify.
            company_name: Company name for relevance checking.

        Returns:
            List of ScrapedItem objects with classification fields populated.
        """
        if not items:
            return []

        logger.info(f"Classifying {len(items)} items using LLM (two-pass: basic then detailed)...")

        # First pass: Basic classification only (without emotion/summary to save tokens)
        basic_tasks = [self._classify_single_item(item, company_name, include_detailed=False) for item in items]

        # Run basic classifications concurrently
        basic_classified = await asyncio.gather(*basic_tasks, return_exceptions=True)

        # Process basic results and identify relevant items
        basic_results: list[ScrapedItem] = []
        relevant_items_to_enrich: list[ScrapedItem] = []

        for item, classified in zip(items, basic_classified):
            if isinstance(classified, Exception):
                logger.error(f"Error in basic classification for item {item.url}: {classified}")
                # Keep item with default (non-relevant) classification
                item.is_relevant = False
                item.sentiment = "neutral"
                item.confidence_score = 0.0
                item.reasoning = f"Classification error: {classified!s}"
                basic_results.append(item)
            elif isinstance(classified, ScrapedItem):
                basic_results.append(classified)
                # Only enrich relevant items with detailed analysis
                if classified.is_relevant:
                    relevant_items_to_enrich.append(classified)
            else:
                # Fallback: keep original item
                item.is_relevant = False
                basic_results.append(item)

        # Second pass: Detailed analysis (emotion, summary) only for relevant items
        if relevant_items_to_enrich:
            logger.info(
                f"Performing detailed analysis (emotion, summary) on {len(relevant_items_to_enrich)} relevant items..."
            )
            detailed_tasks = [
                self._classify_single_item(item, company_name, include_detailed=True)
                for item in relevant_items_to_enrich
            ]

            # Run detailed classifications concurrently
            detailed_classified = await asyncio.gather(*detailed_tasks, return_exceptions=True)

            # Update relevant items with detailed analysis
            for item, detailed in zip(relevant_items_to_enrich, detailed_classified):
                if isinstance(detailed, Exception):
                    logger.error(f"Error in detailed classification for item {item.url}: {detailed}")
                    # Keep basic classification, set emotion/summary to None
                    item.emotion = None
                    item.summary = None
                elif isinstance(detailed, ScrapedItem):
                    # Update with detailed fields
                    item.emotion = detailed.emotion
                    item.summary = detailed.summary

        return basic_results

    async def _classify_single_item(
        self, item: ScrapedItem, company_name: str, include_detailed: bool = True
    ) -> ScrapedItem:
        """
        Classify a single item and update its fields.

        Args:
            item: ScrapedItem to classify.
            company_name: Company name for relevance checking.
            include_detailed: If True, includes emotion and summary analysis.

        Returns:
            ScrapedItem with classification fields populated.
        """
        try:
            classification = await self.llm_processor.classify(item, company_name, include_detailed)

            # Update item with classification results
            item.is_relevant = classification.is_relevant
            item.sentiment = classification.sentiment
            item.confidence_score = classification.confidence_score
            item.reasoning = classification.reasoning

            # Update detailed fields if included
            if include_detailed:
                item.emotion = classification.emotion
                item.summary = classification.summary
        except Exception as e:
            logger.error(f"Error classifying item {item.url}: {e}")
            # Return item with default values
            item.is_relevant = False
            item.sentiment = "neutral"
            item.confidence_score = 0.0
            item.reasoning = f"Classification error: {e!s}"
            if include_detailed:
                item.emotion = None
                item.summary = None
        return item


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
