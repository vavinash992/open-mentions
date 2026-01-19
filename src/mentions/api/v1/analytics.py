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
    get_average_relevance,
    get_platform_counts,
    get_sentiment_counts,
    get_timeline_14_days,
    get_top_emotions,
    get_total_mentions,
    resolve_keyword,
)

analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class SummaryResponse(BaseModel):
    """Summary analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    total_mentions: int = Field(..., description="Total mentions")
    average_relevance_score: float = Field(..., description="Average relevance score across mentions")
    dominant_sentiment: str = Field(..., description="Most frequent sentiment label")


class ChartSeries(BaseModel):
    """Chart series formatted for frontend libraries."""

    labels: list[str] = Field(..., description="Labels for the chart")
    data: list[int] = Field(..., description="Series values aligned with labels")


class ChartsResponse(BaseModel):
    """Charts analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    sentiment: ChartSeries = Field(..., description="Sentiment pie chart data")
    timeline: ChartSeries = Field(..., description="Timeline chart data")
    platforms: ChartSeries = Field(..., description="Platform breakdown data")
    emotions: ChartSeries = Field(..., description="Emotion cloud data")


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
            avg_relevance = await get_average_relevance(session, workspace_id, keyword)
            sentiment_counts = await get_sentiment_counts(session, workspace_id, keyword)

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
        average_relevance_score=round(avg_relevance, 4),
        dominant_sentiment=dominant_sentiment(sentiment_counts),
    )


@analytics_router.get("/charts", response_model=ChartsResponse)
async def get_charts(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
    keyword_id: int | None = Query(None, description="Optional keyword ID filter"),
) -> ChartsResponse:
    """Return chart-ready data for the dashboard."""
    async with async_session_maker() as session:
        try:
            await ensure_workspace(session, workspace_id)
            keyword = await resolve_keyword(session, workspace_id, keyword_id)
            sentiment_counts = await get_sentiment_counts(session, workspace_id, keyword)
            platform_counts = await get_platform_counts(session, workspace_id, keyword)
            emotion_counts = await get_top_emotions(session, workspace_id, keyword)
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

    sentiment_labels = ["positive", "negative", "neutral"]
    sentiment_data = [sentiment_counts.get(k, 0) for k in sentiment_labels]
    platform_labels = list(platform_counts.keys())
    platform_data = [platform_counts[k] for k in platform_labels]
    emotion_labels = [e for e, _ in emotion_counts]
    emotion_data = [c for _, c in emotion_counts]
    timeline_labels = [p["date"] for p in timeline]
    timeline_data = [int(p["count"]) for p in timeline]

    return ChartsResponse(
        workspace_id=workspace_id,
        sentiment=ChartSeries(labels=sentiment_labels, data=sentiment_data),
        timeline=ChartSeries(labels=timeline_labels, data=timeline_data),
        platforms=ChartSeries(labels=platform_labels, data=platform_data),
        emotions=ChartSeries(labels=emotion_labels, data=emotion_data),
    )
