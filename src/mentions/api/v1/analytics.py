"""Analytics API endpoints for dashboard stats."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mentions.db.session import async_session_maker
from mentions.services.analytics import (
    KeywordNotFoundError,
    WorkspaceNotFoundError,
    dominant_sentiment,
    ensure_workspace,
    get_sentiment_counts,
    get_timeline_14_days,
    get_top_platform,
    get_total_mentions,
    resolve_keyword,
)

analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class SummaryResponse(BaseModel):
    """Summary analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    total_mentions: int = Field(..., description="Total mentions")
    dominant_sentiment: str = Field(..., description="Most frequent sentiment label")
    top_platform: str = Field(..., description="Most frequent platform")


class TrendPoint(BaseModel):
    """Timeline point for trend chart."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    count: int = Field(..., description="Mention count for the date")


class TrendsResponse(BaseModel):
    """Timeline analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    points: list[TrendPoint] = Field(..., description="Timeline points")


@analytics_router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
    keyword_id: int | None = Query(None, description="Optional keyword ID filter"),
) -> SummaryResponse:
    """Return summary analytics for a workspace (optional keyword filter)."""
    async with async_session_maker() as session:
        try:
            await ensure_workspace(session, workspace_id)
            keyword = await resolve_keyword(session, workspace_id, keyword_id)

            total = await get_total_mentions(session, workspace_id, keyword)
            sentiment_counts = await get_sentiment_counts(session, workspace_id, keyword)
            top_platform = await get_top_platform(session, workspace_id, keyword)

        except WorkspaceNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found. Create one via GET /api/v1/workspace/new.",
            ) from exc
        except KeywordNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="keyword_id not found for this workspace.",
            ) from exc

    return SummaryResponse(
        workspace_id=workspace_id,
        total_mentions=total,
        dominant_sentiment=dominant_sentiment(sentiment_counts),
        top_platform=top_platform,
    )


@analytics_router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
    keyword_id: int | None = Query(None, description="Optional keyword ID filter"),
) -> TrendsResponse:
    """Return timeline counts for the last 14 days."""
    async with async_session_maker() as session:
        try:
            await ensure_workspace(session, workspace_id)
            keyword = await resolve_keyword(session, workspace_id, keyword_id)
            timeline = await get_timeline_14_days(session, workspace_id, keyword)
        except WorkspaceNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found. Create one via GET /api/v1/workspace/new.",
            ) from exc
        except KeywordNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="keyword_id not found for this workspace.",
            ) from exc

    return TrendsResponse(
        workspace_id=workspace_id,
        points=[TrendPoint(**p) for p in timeline],
    )
