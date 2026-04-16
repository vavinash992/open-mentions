"""Test script for LLM Processor with mock ScrapedItem."""

import asyncio
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mentions.scrapers.base import ScrapedItem
from mentions.services.llm_processor import LLMProcessor

# Load environment variables
load_dotenv()

pytest.skip(
    "Manual integration script (Azure required). Run directly: uv run python tests/test_llm_processor.py",
    allow_module_level=True,
)


async def test_llm_processor():
    """Test LLM processor with mock ScrapedItem."""
    print("=" * 80)
    print("LLM Processor Test")
    print("=" * 80)
    print()

    # Initialize LLM processor
    print("Initializing LLM Processor with Azure OpenAI...")
    try:
        processor = LLMProcessor()
        print("✓ LLM Processor initialized successfully")
        print()
    except Exception as e:
        print(f"✗ Error initializing LLM Processor: {e}")
        return

    # Create mock ScrapedItem (Reddit post about OpenAI)
    mock_item = ScrapedItem(
        keyword="OpenAI",
        platform="reddit",
        content="Just tried out GPT-4 and I'm blown away by its capabilities! The new features are incredible and it's helping me write code much faster. OpenAI is really pushing the boundaries of AI.",
        url="https://reddit.com/r/MachineLearning/comments/example",
        upvotes=42,
        comments=5,
    )

    print("Mock ScrapedItem created:")
    print(f"  Platform: {mock_item.platform}")
    print(f"  Content: {mock_item.content[:100]}...")
    print(f"  URL: {mock_item.url}")
    print()

    # Process the mock item
    company_name = "OpenAI"
    print(f"Processing mention for company: {company_name}")
    print("Calling llm_processor.process_mentions()...")
    print()

    try:
        items = await processor.process_mentions([mock_item], company_name)
        result = items[0]

        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()

        # Check if fields are populated
        print("Classification Results:")
        print("-" * 80)
        print(f"  Relevance Score: {result.relevance_score}")
        print(f"  Is Relevant:     {result.is_relevant}")
        print(f"  Sentiment:       {result.sentiment}")
        print(f"  Emotion:         {result.emotion}")
        print(f"  Summary:         {result.summary}")
        print()

        # Validation checks
        print("Validation Checks:")
        print("-" * 80)

        checks_passed = 0
        total_checks = 5

        # Check relevance_score
        if result.relevance_score is not None:
            if 0.0 <= result.relevance_score <= 1.0:
                print("  ✓ relevance_score is valid (0.0-1.0)")
                checks_passed += 1
            else:
                print(f"  ✗ relevance_score is out of range: {result.relevance_score}")
        else:
            print("  ✗ relevance_score is None")

        # Check is_relevant
        if result.is_relevant is not None:
            print(f"  ✓ is_relevant is set: {result.is_relevant}")
            checks_passed += 1
        else:
            print("  ✗ is_relevant is None")

        # Check sentiment
        if result.sentiment and result.sentiment.lower() in ["positive", "negative", "neutral"]:
            print(f"  ✓ sentiment is valid: {result.sentiment}")
            checks_passed += 1
        else:
            print(f"  ✗ sentiment is invalid: {result.sentiment}")

        # Check emotion
        valid_emotions = [
            "frustration",
            "joy",
            "curiosity",
            "disappointment",
            "anger",
            "neutral",
            "excitement",
            "concern",
            "satisfaction",
            "confusion",
        ]
        if result.emotion and result.emotion.lower() in valid_emotions:
            print(f"  ✓ emotion is valid: {result.emotion}")
            checks_passed += 1
        else:
            print(f"  ✗ emotion is invalid: {result.emotion}")

        # Check summary
        if result.summary and len(result.summary) > 0:
            if len(result.summary) <= 150:
                print(f"  ✓ summary is valid (length: {len(result.summary)})")
                print(f"    Summary: {result.summary[:100]}...")
                checks_passed += 1
            else:
                print(f"  ✗ summary is too long: {len(result.summary)} characters")
        else:
            print("  ✗ summary is empty or None")

        print()
        print("=" * 80)
        print(f"Test Summary: {checks_passed}/{total_checks} checks passed")
        print("=" * 80)

    except Exception as e:
        print(f"✗ Error processing mention: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_llm_processor())
