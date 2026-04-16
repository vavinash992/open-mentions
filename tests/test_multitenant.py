"""Offline tests for anonymous workspaces + global URL dedup.

These tests avoid network/LLM calls by monkeypatching scrapers + LLM processor.
"""

import asyncio

# Ensure src is on path (mirrors existing tests)
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mentions.main import app
from mentions.scrapers.base import ScrapedItem


def test_workspace_new_persists_and_keywords_limit_and_history_and_cooldown(monkeypatch):
    with TestClient(app) as client:
        # Create workspace
        r = client.get("/api/v1/workspace/new")
        assert r.status_code == 200
        workspace_id = r.json()["workspace_id"]
        assert isinstance(workspace_id, str) and len(workspace_id) == 12

        # Add up to 5 keywords
        for i in range(5):
            rr = client.post(
                "/api/v1/keywords",
                headers={"X-Workspace-ID": workspace_id},
                json={"keyword": f"kw{i}"},
            )
            assert rr.status_code == 200

        # 6th keyword should be forbidden (403)
        rr = client.post(
            "/api/v1/keywords",
            headers={"X-Workspace-ID": workspace_id},
            json={"keyword": "kw5"},
        )
        assert rr.status_code == 403

        # Patch SearchOrchestrator.search_all_platforms to avoid scraping/LLM and return empty list.
        from mentions.routers import monitor as monitor_router_module

        class FakeOrchestrator:
            async def search_all_platforms(self, *args, **kwargs):
                return []

        monkeypatch.setattr(monitor_router_module, "SearchOrchestrator", FakeOrchestrator)

        # First trigger should succeed
        rr = client.post("/api/v1/monitor/trigger", params={"workspace_id": workspace_id})
        assert rr.status_code == 200

        # Second trigger should be rate-limited
        rr2 = client.post("/api/v1/monitor/trigger", params={"workspace_id": workspace_id})
        assert rr2.status_code == 429

        # History should be empty and require query param workspace_id
        rh = client.get("/api/v1/history", params={"workspace_id": workspace_id})
        assert rh.status_code == 200
        assert rh.json()["workspace_id"] == workspace_id
        assert rh.json()["total_mentions"] == 0


def test_global_url_dedup_llm_called_once_across_workspaces(monkeypatch):
    with TestClient(app) as client:
        # Create two workspaces
        ws1 = client.get("/api/v1/workspace/new").json()["workspace_id"]
        ws2 = client.get("/api/v1/workspace/new").json()["workspace_id"]

        # Patch scrapers to return the same URL for every platform
        from mentions.services import orchestrator as orchestrator_module

        async def fake_scrape(self, platform_name, scraper, company_name, filter_by, max_results):
            return [
                ScrapedItem(
                    keyword=company_name,
                    platform=platform_name,
                    content="hello",
                    url="https://example.com/post/1",
                )
            ]

        monkeypatch.setattr(orchestrator_module.SearchOrchestrator, "_scrape_platform", fake_scrape)

        # Patch LLM processor to count calls; mark relevant
        calls = {"n": 0}

        class FakeLLMProcessor:
            async def process_mentions(self, items, company_name):
                calls["n"] += 1
                for it in items:
                    it.is_relevant = True
                    it.relevance_score = 0.9
                    it.sentiment = "neutral"
                    it.emotion = "neutral"
                    it.summary = "summary"
                return items

        monkeypatch.setattr(orchestrator_module, "LLMProcessor", FakeLLMProcessor)

        orch = orchestrator_module.SearchOrchestrator()

        # First workspace: should classify once (1 URL)
        res1 = asyncio.run(
            orch.search_all_platforms(
                company_name="OpenAI",
                filter_by="week",
                max_results_per_platform=5,
                workspace_id=ws1,
            )
        )
        assert len(res1) == 1
        assert calls["n"] == 1

        # Second workspace: same URL should NOT call LLM again (global dedup)
        orch2 = orchestrator_module.SearchOrchestrator()
        res2 = asyncio.run(
            orch2.search_all_platforms(
                company_name="OpenAI",
                filter_by="week",
                max_results_per_platform=5,
                workspace_id=ws2,
            )
        )
        assert len(res2) == 1
        assert calls["n"] == 1

        # Search endpoint should require workspace_id; patch router function to avoid network and just return res1
        from mentions.routers import search as search_router_module

        async def fake_search_all_platforms(
            company_name, filter_by="week", max_results_per_platform=50, workspace_id=None
        ):
            return res1

        monkeypatch.setattr(search_router_module, "search_all_platforms", fake_search_all_platforms)

        rr = client.post(
            "/api/v1/search",
            params={"workspace_id": ws1},
            json={"company_name": "OpenAI", "filter_by": "week", "max_results_per_platform": 5},
        )
        assert rr.status_code == 200
        assert rr.json()["total_mentions"] == 1
