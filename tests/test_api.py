"""Offline smoke test for API endpoints using FastAPI TestClient.

This test avoids network/LLM calls by stubbing orchestrator calls.
Do NOT load `.env` here (it's gitignored and may be inaccessible in CI/sandbox).
"""

import sys
from pathlib import Path

# Add src to path before other imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient

from mentions.main import app


def test_api_endpoint(monkeypatch):
    """Test the /api/v1/search endpoint (offline)."""
    with TestClient(app) as client:
        # Create a workspace (lifespan runs, DB tables initialized)
        ws = client.get("/api/v1/workspace/new").json()["workspace_id"]

        from mentions.routers import search as search_router_module
        from mentions.scrapers.base import ScrapedItem

        async def fake_search_all_platforms(
            company_name, filter_by="week", max_results_per_platform=50, workspace_id=None
        ):
            return [
                ScrapedItem(
                    keyword=company_name,
                    platform="reddit",
                    content="hello",
                    url="https://example.com/1",
                    relevance_score=0.9,
                    is_relevant=True,
                    sentiment="neutral",
                    emotion="neutral",
                    summary="summary",
                )
            ]

        monkeypatch.setattr(search_router_module, "search_all_platforms", fake_search_all_platforms)

        response = client.post(
            "/api/v1/search",
            params={"workspace_id": ws},
            json={"company_name": "OpenAI", "filter_by": "week", "max_results_per_platform": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_mentions" in data
        assert "mentions" in data
        assert data["total_mentions"] == 1


def test_health_endpoint():
    """Test the health check endpoint."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json().get("status") == "healthy"


if __name__ == "__main__":
    test_health_endpoint()
    test_api_endpoint()
