"""Test script for API endpoint using FastAPI TestClient."""

import sys
from pathlib import Path

# Add src to path before other imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from fastapi.testclient import TestClient

# Load environment variables
load_dotenv()

from mentions.main import app  # noqa: E402

# Create test client
client = TestClient(app)


def test_api_endpoint():  # noqa: C901
    """Test the /api/v1/search endpoint."""
    print("=" * 80)
    print("API Endpoint Test")
    print("=" * 80)
    print()

    # Test data
    request_data = {
        "company_name": "OpenAI",
        "filter_by": "week",
        "max_results_per_platform": 5,  # Small number for faster testing
    }

    print("Request Details:")
    print("-" * 80)
    print("  Endpoint: POST /api/v1/search")
    print(f"  Company:  {request_data['company_name']}")
    print(f"  Filter:   {request_data['filter_by']}")
    print(f"  Max per platform: {request_data['max_results_per_platform']}")
    print()

    print("Sending request to API...")
    print("(This may take a few minutes as it scrapes and classifies mentions)")
    print()

    try:
        # Send POST request
        response = client.post("/api/v1/search", json=request_data)

        print("=" * 80)
        print("RESPONSE")
        print("=" * 80)
        print()

        # Check status code
        print(f"Status Code: {response.status_code}")
        print()

        if response.status_code != 200:
            print(f"✗ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return

        print("✓ Request succeeded (200 OK)")
        print()

        # Parse JSON response
        try:
            data = response.json()
        except Exception as e:
            print(f"✗ Failed to parse JSON response: {e}")
            print(f"Response text: {response.text[:500]}")
            return

        # Expected keys in SearchResponse
        expected_keys = [
            "total_mentions",
            "sentiment_breakdown",
            "platform_breakdown",
            "average_confidence",
            "mentions",
        ]

        print("Response Validation:")
        print("-" * 80)

        checks_passed = 0
        total_checks = len(expected_keys)

        # Check for expected keys
        for key in expected_keys:
            if key in data:
                print(f"  ✓ '{key}' is present")
                checks_passed += 1
            else:
                print(f"  ✗ '{key}' is missing")

        print()

        # Display response structure
        print("Response Structure:")
        print("-" * 80)
        print(f"  total_mentions:      {data.get('total_mentions', 'N/A')}")
        print(f"  average_confidence:  {data.get('average_confidence', 'N/A')}")
        print()

        # Sentiment breakdown
        sentiment_breakdown = data.get("sentiment_breakdown", {})
        print("  Sentiment Breakdown:")
        for sentiment, count in sentiment_breakdown.items():
            print(f"    {sentiment}: {count}")
        print()

        # Platform breakdown
        platform_breakdown = data.get("platform_breakdown", {})
        print("  Platform Breakdown:")
        for platform, count in platform_breakdown.items():
            print(f"    {platform}: {count}")
        print()

        # Mentions
        mentions = data.get("mentions", [])
        print(f"  Mentions: {len(mentions)} items")
        print()

        # Display first mention if available
        if mentions:
            print("  First Mention Preview:")
            first = mentions[0]
            print(f"    Platform:        {first.get('platform', 'N/A')}")
            print(f"    Relevance Score: {first.get('relevance_score', 'N/A')}")
            print(f"    Is Relevant:     {first.get('is_relevant', 'N/A')}")
            print(f"    Sentiment:       {first.get('sentiment', 'N/A')}")
            print(f"    Emotion:         {first.get('emotion', 'N/A')}")
            print(f"    Summary:         {first.get('summary', 'N/A')[:100]}...")
            print()

        # Check if mentions list contains ScrapedItem structure
        if mentions:
            first_mention = mentions[0]
            mention_keys = [
                "keyword",
                "platform",
                "content",
                "url",
                "relevance_score",
                "is_relevant",
                "sentiment",
                "emotion",
                "summary",
            ]

            print("  Mention Structure Validation:")
            for key in mention_keys:
                if key in first_mention:
                    print(f"    ✓ '{key}' is present")
                else:
                    print(f"    ✗ '{key}' is missing")

        print()
        print("=" * 80)
        print(f"Test Summary: {checks_passed}/{total_checks} checks passed")
        if mentions:
            print("✓ Response contains mentions with all required fields")
        print("=" * 80)

    except Exception as e:
        print(f"✗ Error testing API endpoint: {e}")
        import traceback

        traceback.print_exc()


def test_health_endpoint():
    """Test the health check endpoint."""
    print()
    print("=" * 80)
    print("Health Endpoint Test")
    print("=" * 80)
    print()

    try:
        response = client.get("/health")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("✓ Health endpoint working")
            print(f"Response: {response.json()}")
        else:
            print(f"✗ Health endpoint failed with status {response.status_code}")

    except Exception as e:
        print(f"✗ Error testing health endpoint: {e}")


if __name__ == "__main__":
    test_health_endpoint()
    test_api_endpoint()
