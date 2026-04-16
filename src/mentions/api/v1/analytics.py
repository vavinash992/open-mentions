"""Analytics API endpoints for dashboard stats."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query
from openai import AsyncOpenAI
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


class BrandBenchmarkStat(BaseModel):
    """Keyword-level benchmark stats."""

    name: str = Field(..., description="Keyword name")
    count: int = Field(..., description="Mention count for this keyword")
    sentiment_avg: float = Field(..., description="Average sentiment score")


class ComparisonResponse(BaseModel):
    """Comparison analytics response."""

    workspace_id: str = Field(..., description="Workspace ID")
    share_of_voice: list[BrandBenchmarkStat] = Field(..., description="Share of voice metrics")
    sentiment_benchmark: list[BrandBenchmarkStat] = Field(..., description="Sentiment benchmarking metrics")
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

    sentiment_by_keyword = {item["keyword"]: item["average_sentiment"] for item in sentiment_avgs}
    keywords = {item["keyword"] for item in sov_counts} | set(sentiment_by_keyword.keys())
    benchmark_items = [
        BrandBenchmarkStat(
            name=keyword,
            count=next((item["count"] for item in sov_counts if item["keyword"] == keyword), 0),
            sentiment_avg=round(sentiment_by_keyword.get(keyword, 0.0), 3),
        )
        for keyword in sorted(keywords)
    ]

    return ComparisonResponse(
        workspace_id=workspace_id,
        share_of_voice=benchmark_items,
        sentiment_benchmark=benchmark_items,
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


# ---------------------------------------------------------------------------
# AI Summary
# ---------------------------------------------------------------------------


class AISummaryResponse(BaseModel):
    """AI-generated weekly summary response."""

    workspace_id: str = Field(..., description="Workspace ID")
    summary: str = Field(..., description="AI-generated insights summary")


@analytics_router.get("/ai-summary", response_model=AISummaryResponse)
async def get_ai_summary(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
) -> AISummaryResponse:
    """Generate an AI-powered weekly insights summary for a workspace."""
    async with async_session_maker() as session:
        try:
            await ensure_workspace(session, workspace_id)
            total = await get_total_mentions(session, workspace_id, None)
            sentiment_counts = await get_sentiment_counts(session, workspace_id, None)
            platform_counts = await get_platform_counts(session, workspace_id, None)
            top_emotions = await get_top_emotions(session, workspace_id, None)
        except WorkspaceNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found.",
            ) from exc

    if total == 0:
        return AISummaryResponse(
            workspace_id=workspace_id,
            summary="No mentions collected yet. Run a comparison or trigger monitoring to start gathering data.",
        )

    # Build context for the LLM
    emotion_str = ", ".join(f"{e} ({c})" for e, c in top_emotions[:5]) if top_emotions else "none"
    platform_str = ", ".join(f"{p}: {c}" for p, c in platform_counts.items()) if platform_counts else "none"
    sentiment_str = ", ".join(f"{s}: {c}" for s, c in sentiment_counts.items()) if sentiment_counts else "none"

    prompt = (
        "You are an expert brand analyst. Based on the following mention analytics data, "
        "write a concise 3-4 sentence weekly insights summary for a dashboard. "
        "Be specific, highlight trends, and end with one actionable recommendation.\n\n"
        f"Total mentions: {total}\n"
        f"Sentiment breakdown: {sentiment_str}\n"
        f"Platform distribution: {platform_str}\n"
        f"Top emotions: {emotion_str}\n"
    )

    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if not api_key:
        return AISummaryResponse(
            workspace_id=workspace_id,
            summary="AI summary unavailable — GROQ_API_KEY not configured.",
        )

    try:
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
        )
        ai_text = response.choices[0].message.content or "Unable to generate summary."
    except Exception:
        ai_text = "AI summary temporarily unavailable. Please try again later."

    return AISummaryResponse(workspace_id=workspace_id, summary=ai_text)


# ---------------------------------------------------------------------------
# Sentiment Over Time
# ---------------------------------------------------------------------------


class SentimentTrendPoint(BaseModel):
    """A single day's sentiment breakdown."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    positive: int = Field(0, description="Positive mention count")
    negative: int = Field(0, description="Negative mention count")
    neutral: int = Field(0, description="Neutral mention count")


class SentimentTrendsResponse(BaseModel):
    """Sentiment breakdown over time."""

    workspace_id: str = Field(..., description="Workspace ID")
    points: list[SentimentTrendPoint] = Field(..., description="Daily sentiment breakdown")


@analytics_router.get("/sentiment-trends", response_model=SentimentTrendsResponse)
async def get_sentiment_trends_endpoint(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
    days: int = Query(14, ge=1, le=90, description="Number of days to look back"),
) -> SentimentTrendsResponse:
    """Return daily sentiment breakdown for the last N days."""
    from datetime import date as date_type
    from datetime import timedelta

    from sqlalchemy import case, func, select

    from mentions.models.database import Mention, WorkspaceMention

    async with async_session_maker() as session:
        try:
            await ensure_workspace(session, workspace_id)
        except WorkspaceNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Workspace not found.") from exc

        start_date = date_type.today() - timedelta(days=days)

        stmt = (
            select(
                func.date(WorkspaceMention.created_at).label("day"),
                func.sum(case((Mention.sentiment == "positive", 1), else_=0)).label("positive"),
                func.sum(case((Mention.sentiment == "negative", 1), else_=0)).label("negative"),
                func.sum(case((Mention.sentiment == "neutral", 1), else_=0)).label("neutral"),
            )
            .join(Mention, WorkspaceMention.mention_url == Mention.url)
            .where(
                WorkspaceMention.workspace_id == workspace_id,
                func.date(WorkspaceMention.created_at) >= start_date.isoformat(),
            )
            .group_by(func.date(WorkspaceMention.created_at))
            .order_by(func.date(WorkspaceMention.created_at))
        )
        result = await session.execute(stmt)
        rows = result.all()

    # Fill missing days with zeros
    points: list[SentimentTrendPoint] = []
    row_map = {str(row.day): row for row in rows}
    current = start_date
    today = date_type.today()
    while current <= today:
        day_str = current.isoformat()
        row = row_map.get(day_str)
        points.append(
            SentimentTrendPoint(
                date=day_str,
                positive=int(row.positive) if row else 0,
                negative=int(row.negative) if row else 0,
                neutral=int(row.neutral) if row else 0,
            )
        )
        current += timedelta(days=1)

    return SentimentTrendsResponse(workspace_id=workspace_id, points=points)
