"""Analytics API endpoints for dashboard stats."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from mentions.db.session import async_session_maker
from mentions.services.analytics import (
    InvalidDaysError,
    KeywordNotFoundError,
    WorkspaceNotFoundError,
    ensure_workspace,
    get_platform_stats,
    get_sentiment_stats,
    get_timeline_counts,
    get_top_emotions,
    get_total_mentions,
    resolve_keyword,
)

analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class EmotionCount(BaseModel):
    """Top emotion entry."""

    emotion: str = Field(..., description="Emotion label")
    count: int = Field(..., description="Number of mentions with this emotion")


class SummaryResponse(BaseModel):
    """Summary analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    total_mentions: int = Field(..., description="Total mentions")
    sentiment_breakdown: dict[str, float] = Field(..., description="Sentiment percentages")
    top_emotions: list[EmotionCount] = Field(..., description="Top 3 emotions by count")
    platform_stats: dict[str, int] = Field(..., description="Counts by platform")


class TrendPoint(BaseModel):
    """Timeline point for trend chart."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    count: int = Field(..., description="Mention count for the date")


class TrendsResponse(BaseModel):
    """Timeline analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    days: int = Field(..., description="Window size in days (7 or 30)")
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
            sentiment_counts = await get_sentiment_stats(session, workspace_id, keyword)
            platform_stats = await get_platform_stats(session, workspace_id, keyword)
            top_emotions = await get_top_emotions(session, workspace_id, keyword, limit=3)

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

    # Convert sentiment counts to percentages
    sentiment_percentages: dict[str, float] = {}
    if total > 0:
        for key, count in sentiment_counts.items():
            sentiment_percentages[key] = round((count / total) * 100.0, 2)
    else:
        sentiment_percentages = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}

    return SummaryResponse(
        workspace_id=workspace_id,
        total_mentions=total,
        sentiment_breakdown=sentiment_percentages,
        top_emotions=[EmotionCount(emotion=e, count=c) for e, c in top_emotions],
        platform_stats=platform_stats,
    )


@analytics_router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
    days: int = Query(7, description="Time window in days (7 or 30)"),
    keyword_id: int | None = Query(None, description="Optional keyword ID filter"),
) -> TrendsResponse:
    """Return timeline counts for the last 7 or 30 days."""
    async with async_session_maker() as session:
        try:
            await ensure_workspace(session, workspace_id)
            keyword = await resolve_keyword(session, workspace_id, keyword_id)
            points = await get_timeline_counts(session, workspace_id, days, keyword)
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
        except InvalidDaysError as exc:
            raise HTTPException(status_code=400, detail="days must be 7 or 30") from exc

    return TrendsResponse(
        workspace_id=workspace_id,
        days=days,
        points=[TrendPoint(**p) for p in points],
    )
