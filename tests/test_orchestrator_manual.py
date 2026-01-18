"""Manual integration test for Orchestrator with real-world search."""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mentions.services.orchestrator import search_all_platforms

# Load environment variables
load_dotenv()


async def test_orchestrator():
    """Test orchestrator with real-world keyword search."""
    print("=" * 80)
    print("Orchestrator Integration Test")
    print("=" * 80)
    print()

    # Test with a real-world company
    company_name = "Nvidia"
    filter_by = "week"
    max_results_per_platform = 10  # Limit for faster testing

    print(f"Searching for company: {company_name}")
    print(f"Time filter: {filter_by}")
    print(f"Max results per platform: {max_results_per_platform}")
    print()
    print("This may take a few minutes as we scrape multiple platforms...")
    print("=" * 80)
    print()

    try:
        # Run the search
        mentions = await search_all_platforms(
            company_name=company_name,
            filter_by=filter_by,
            max_results_per_platform=max_results_per_platform,
        )

        print()
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()

        # Print summary
        total_mentions = len(mentions)
        print(f"Total Relevant Mentions Found: {total_mentions}")
        print()

        if total_mentions == 0:
            print("No relevant mentions found. Try a different company or time filter.")
            return

        # Count by platform
        platform_counts = {}
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        avg_relevance = 0.0

        for mention in mentions:
            platform_counts[mention.platform] = platform_counts.get(mention.platform, 0) + 1
            if mention.sentiment:
                sentiment_counts[mention.sentiment.lower()] = sentiment_counts.get(mention.sentiment.lower(), 0) + 1
            if mention.relevance_score:
                avg_relevance += mention.relevance_score

        avg_relevance = avg_relevance / total_mentions if total_mentions > 0 else 0.0

        print("Summary Statistics:")
        print("-" * 80)
        print(f"  Total Mentions:      {total_mentions}")
        print(f"  Average Relevance:   {avg_relevance:.3f}")
        print()
        print("  Platform Breakdown:")
        for platform, count in sorted(platform_counts.items()):
            print(f"    {platform:20s}: {count}")
        print()
        print("  Sentiment Breakdown:")
        for sentiment, count in sentiment_counts.items():
            print(f"    {sentiment:20s}: {count}")
        print()

        # Display first 3 results
        print("=" * 80)
        print("First 3 Classified Results:")
        print("=" * 80)
        print()

        for i, mention in enumerate(mentions[:3], 1):
            print(f"Result #{i}")
            print("-" * 80)
            print(f"Platform:        {mention.platform}")
            print(f"URL:             {mention.url}")
            print(f"Relevance Score: {mention.relevance_score:.3f}")
            print(f"Is Relevant:     {mention.is_relevant}")
            print(f"Sentiment:       {mention.sentiment}")
            print(f"Emotion:         {mention.emotion}")
            print(f"Content:         {mention.content[:200]}...")
            print(f"Summary:         {mention.summary}")
            print(f"Upvotes:         {mention.upvotes}")
            print()

        if total_mentions > 3:
            print(f"... and {total_mentions - 3} more results")
            print()

        print("=" * 80)
        print("Test completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"✗ Error during search: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_orchestrator())
