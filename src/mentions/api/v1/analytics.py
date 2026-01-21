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
    get_comparison_trends,
    get_platform_counts,
    get_reach_analytics,
    get_sentiment_benchmark,
    get_sentiment_counts,
    get_share_of_voice,
    get_timeline_14_days,
    get_top_emotions,
    get_top_platform,
    get_total_mentions,
    resolve_keyword,
)

analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class SummaryResponse(BaseModel):
    """Summary analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    total_mentions: int = Field(..., description="Total mentions")
    average_relevance_score: float = Field(..., description="Average relevance score (0.0-1.0)")
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


class ChartData(BaseModel):
    """Chart-friendly data format."""

    labels: list[str] = Field(..., description="Labels for the chart")
    data: list[int | float] = Field(..., description="Data points for the chart")


class ChartsResponse(BaseModel):
    """Chart-ready analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    sentiment: ChartData = Field(..., description="Sentiment breakdown")
    timeline: ChartData = Field(..., description="Mentions per day (last 14 days)")
    platforms: ChartData = Field(..., description="Platform distribution")
    emotions: ChartData = Field(..., description="Top emotions")


class ShareOfVoiceStat(BaseModel):
    """Share of voice per keyword."""

    keyword: str = Field(..., description="Tracked keyword")
    category: str = Field(..., description="Keyword category")
    count: int = Field(..., description="Mention count for this keyword")
    percent: float = Field(..., description="Share of voice percentage")


class SentimentBenchmarkStat(BaseModel):
    """Average sentiment score per keyword."""

    keyword: str = Field(..., description="Tracked keyword")
    category: str = Field(..., description="Keyword category")
    average_sentiment: float = Field(..., description="Average sentiment score")


class ComparisonResponse(BaseModel):
    """Comparison analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    share_of_voice: list[ShareOfVoiceStat] = Field(..., description="Share of voice metrics")
    sentiment_benchmark: list[SentimentBenchmarkStat] = Field(..., description="Sentiment benchmarking metrics")
    trends: list[dict[str, int | str]] = Field(..., description="Daily counts by keyword")


class ImpactMention(BaseModel):
    """Most impactful mention summary."""

    url: str = Field(..., description="Mention URL")
    platform: str = Field(..., description="Platform name")
    summary: str = Field(..., description="Summary text")
    keyword: str = Field(..., description="Keyword that found the mention")
    impact_score: int = Field(..., description="Computed impact score")


class ReachResponse(BaseModel):
    """Reach & impact analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    estimated_reach: int = Field(..., description="Total estimated reach score")
    most_impactful: list[ImpactMention] = Field(..., description="Top 5 impactful mentions")


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
            average_relevance = await get_average_relevance(session, workspace_id, keyword)
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
        average_relevance_score=round(average_relevance, 3),
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


@analytics_router.get("/charts", response_model=ChartsResponse)
async def get_charts(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
    keyword_id: int | None = Query(None, description="Optional keyword ID filter"),
) -> ChartsResponse:
    """Return chart-ready analytics for a workspace (optional keyword filter)."""
    async with async_session_maker() as session:
        try:
            await ensure_workspace(session, workspace_id)
            keyword = await resolve_keyword(session, workspace_id, keyword_id)

            sentiment_counts = await get_sentiment_counts(session, workspace_id, keyword)
            timeline = await get_timeline_14_days(session, workspace_id, keyword)
            platform_counts = await get_platform_counts(session, workspace_id, keyword)
            top_emotions = await get_top_emotions(session, workspace_id, keyword)
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

    return ChartsResponse(
        workspace_id=workspace_id,
        sentiment=ChartData(labels=list(sentiment_counts.keys()), data=list(sentiment_counts.values())),
        timeline=ChartData(
            labels=[point["date"] for point in timeline],
            data=[int(point["count"]) for point in timeline],
        ),
        platforms=ChartData(labels=list(platform_counts.keys()), data=list(platform_counts.values())),
        emotions=ChartData(
            labels=[emotion for emotion, _ in top_emotions],
            data=[count for _, count in top_emotions],
        ),
    )


@analytics_router.get("/comparison", response_model=ComparisonResponse)
async def get_comparison(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
) -> ComparisonResponse:
    """Return share-of-voice and sentiment benchmarking for brand vs competitor keywords."""
    async with async_session_maker() as session:
        try:
            await ensure_workspace(session, workspace_id)
            sov_counts = await get_share_of_voice(session, workspace_id)
            sentiment_avgs = await get_sentiment_benchmark(session, workspace_id)
            trends = await get_comparison_trends(session, workspace_id)
        except WorkspaceNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found. Create one via GET /api/v1/workspace/new.",
            ) from exc

    total = sum(item["count"] for item in sov_counts) if sov_counts else 0
    if total > 0:
        sov_items = [
            ShareOfVoiceStat(
                keyword=item["keyword"],
                category=item["category"],
                count=item["count"],
                percent=round((item["count"] / total) * 100, 2),
            )
            for item in sov_counts
        ]
    else:
        sov_items = [
            ShareOfVoiceStat(
                keyword=item["keyword"],
                category=item["category"],
                count=item["count"],
                percent=0.0,
            )
            for item in sov_counts
        ]

    return ComparisonResponse(
        workspace_id=workspace_id,
        share_of_voice=sov_items,
        sentiment_benchmark=[
            SentimentBenchmarkStat(
                keyword=item["keyword"],
                category=item["category"],
                average_sentiment=round(item["average_sentiment"], 3),
            )
            for item in sentiment_avgs
        ],
        trends=trends,
    )


@analytics_router.get("/reach", response_model=ReachResponse)
async def get_reach(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
) -> ReachResponse:
    """Return reach and impact analytics for a workspace."""
    async with async_session_maker() as session:
        try:
            await ensure_workspace(session, workspace_id)
            total_reach, top_mentions = await get_reach_analytics(session, workspace_id)
        except WorkspaceNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found. Create one via GET /api/v1/workspace/new.",
            ) from exc

    return ReachResponse(
        workspace_id=workspace_id,
        estimated_reach=total_reach,
        most_impactful=[ImpactMention(**mention) for mention in top_mentions],
    )
