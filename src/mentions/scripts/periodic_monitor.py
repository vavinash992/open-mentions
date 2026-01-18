"""Periodic monitoring script for tracked keywords.

This script fetches all active keywords from the database and runs
the orchestrator to search for new mentions across all platforms.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mentions.db.session import async_session_maker, init_db  # noqa: E402
from mentions.models.database import TrackedKeyword  # noqa: E402
from mentions.services.orchestrator import SearchOrchestrator  # noqa: E402

# Load environment variables
load_dotenv()

# Configure logger
logger.add(
    PROJECT_ROOT / "monitor.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
)


async def monitor_keywords(filter_by: str = "week", max_results_per_platform: int = 50) -> dict:
    """
    Monitor all active keywords and search for new mentions.

    Args:
        filter_by: Time filter for scraping (e.g., 'day', 'week', 'month').
        max_results_per_platform: Maximum results to fetch per platform.

    Returns:
        Dictionary with summary statistics.
    """
    # Initialize database
    await init_db()

    # Initialize orchestrator
    orchestrator = SearchOrchestrator()

    async with async_session_maker() as session:
        # Fetch all active keywords
        statement = select(TrackedKeyword).where(TrackedKeyword.is_active == True)  # noqa: E712
        result = await session.execute(statement)
        tracked_keywords = result.scalars().all()

    if not tracked_keywords:
        logger.warning("No active keywords found in database. Add keywords to TrackedKeyword table.")
        return {
            "total_keywords": 0,
            "total_new_mentions": 0,
            "keyword_results": [],
        }

    logger.info(f"Found {len(tracked_keywords)} active keyword(s) to monitor")

    total_new_mentions = 0
    keyword_results = []

    # Process each keyword
    for tracked_keyword in tracked_keywords:
        keyword = tracked_keyword.keyword
        logger.info(f"Processing keyword: '{keyword}'")

        try:
            # Search for mentions using orchestrator
            # The orchestrator already handles:
            # - Checking for existing URLs (deduplication)
            # - LLM classification
            # - Saving new mentions to database
            mentions = await orchestrator.search_all_platforms(
                company_name=keyword,
                filter_by=filter_by,
                max_results_per_platform=max_results_per_platform,
            )

            # Count new mentions (mentions that were just added)
            # Note: The orchestrator filters for is_relevant=True
            new_mentions_count = len(mentions)

            # Update last_searched_at timestamp
            async with async_session_maker() as session:
                tracked_keyword.last_searched_at = datetime.now(timezone.utc)
                session.add(tracked_keyword)
                await session.commit()

            logger.info(f"Keyword '{keyword}': Found {new_mentions_count} relevant new mentions")
            total_new_mentions += new_mentions_count

            keyword_results.append({
                "keyword": keyword,
                "new_mentions": new_mentions_count,
                "status": "success",
            })

        except Exception as e:
            logger.error(f"Error processing keyword '{keyword}': {e}")
            keyword_results.append({
                "keyword": keyword,
                "new_mentions": 0,
                "status": "error",
                "error": str(e),
            })

    summary = {
        "total_keywords": len(tracked_keywords),
        "total_new_mentions": total_new_mentions,
        "keyword_results": keyword_results,
    }

    logger.info(
        f"Monitoring complete: {total_new_mentions} new mentions found across {len(tracked_keywords)} keyword(s)"
    )
    return summary


async def main() -> None:
    """Main entry point for the periodic monitoring script."""
    logger.info("=" * 60)
    logger.info("Starting periodic keyword monitoring")
    logger.info("=" * 60)

    try:
        summary = await monitor_keywords()

        logger.info("=" * 60)
        logger.info("Monitoring Summary:")
        logger.info(f"  Total Keywords Processed: {summary['total_keywords']}")
        logger.info(f"  Total New Mentions Found: {summary['total_new_mentions']}")
        logger.info("=" * 60)

        # Log detailed results for each keyword
        for result in summary["keyword_results"]:
            if result["status"] == "success":
                logger.info(f"  - {result['keyword']}: {result['new_mentions']} new mentions")
            else:
                logger.error(f"  - {result['keyword']}: ERROR - {result.get('error', 'Unknown error')}")

        logger.info("=" * 60)
        logger.info("Periodic monitoring completed successfully")
        logger.info("=" * 60)

    except Exception as e:
        logger.exception(f"Fatal error during monitoring: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
