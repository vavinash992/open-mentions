"""Analytics service for dashboard statistics."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mentions.models.database import Mention, TrackedKeyword, Workspace, WorkspaceMention


class WorkspaceNotFoundError(Exception):
    """Raised when a workspace_id is not found."""


class KeywordNotFoundError(Exception):
    """Raised when a keyword_id is not found for a workspace."""


class InvalidDaysError(Exception):
    """Raised when an invalid days window is provided."""


async def ensure_workspace(session: AsyncSession, workspace_id: str) -> None:
    """Ensure the workspace exists."""
    stmt = select(Workspace).where(Workspace.workspace_id == workspace_id)
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is None:
        raise WorkspaceNotFoundError


async def resolve_keyword(session: AsyncSession, workspace_id: str, keyword_id: int | None) -> str | None:
    """Resolve keyword text for a keyword_id in a workspace."""
    if keyword_id is None:
        return None
    stmt = select(TrackedKeyword).where(
        TrackedKeyword.id == keyword_id,
        TrackedKeyword.workspace_id == workspace_id,
    )
    result = await session.execute(stmt)
    keyword = result.scalar_one_or_none()
    if keyword is None:
        raise KeywordNotFoundError
    return keyword.keyword


def _base_joined_query(workspace_id: str, keyword: str | None):
    stmt = (
        select(Mention, WorkspaceMention)
        .join(WorkspaceMention, WorkspaceMention.mention_url == Mention.url)
        .where(WorkspaceMention.workspace_id == workspace_id)
    )
    if keyword:
        stmt = stmt.where(WorkspaceMention.keyword == keyword)
    return stmt


async def get_total_mentions(session: AsyncSession, workspace_id: str, keyword: str | None = None) -> int:
    stmt = select(func.count()).select_from(WorkspaceMention).where(WorkspaceMention.workspace_id == workspace_id)
    if keyword:
        stmt = stmt.where(WorkspaceMention.keyword == keyword)
    result = await session.execute(stmt)
    return int(result.scalar() or 0)


async def get_average_relevance(session: AsyncSession, workspace_id: str, keyword: str | None = None) -> float:
    stmt = (
        select(func.avg(Mention.relevance_score))
        .select_from(WorkspaceMention)
        .join(Mention, WorkspaceMention.mention_url == Mention.url)
        .where(WorkspaceMention.workspace_id == workspace_id)
    )
    if keyword:
        stmt = stmt.where(WorkspaceMention.keyword == keyword)
    result = await session.execute(stmt)
    value = result.scalar()
    return float(value or 0.0)


async def get_sentiment_counts(session: AsyncSession, workspace_id: str, keyword: str | None = None) -> dict[str, int]:
    stmt = (
        select(Mention.sentiment, func.count())
        .select_from(WorkspaceMention)
        .join(Mention, WorkspaceMention.mention_url == Mention.url)
        .where(WorkspaceMention.workspace_id == workspace_id)
        .group_by(Mention.sentiment)
    )
    if keyword:
        stmt = stmt.where(WorkspaceMention.keyword == keyword)
    result = await session.execute(stmt)
    rows = result.all()
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for sentiment, count in rows:
        key = (sentiment or "neutral").lower()
        if key not in counts:
            continue
        counts[key] += int(count or 0)
    return counts


async def get_platform_counts(session: AsyncSession, workspace_id: str, keyword: str | None = None) -> dict[str, int]:
    stmt = (
        select(Mention.platform, func.count())
        .select_from(WorkspaceMention)
        .join(Mention, WorkspaceMention.mention_url == Mention.url)
        .where(WorkspaceMention.workspace_id == workspace_id)
        .group_by(Mention.platform)
    )
    if keyword:
        stmt = stmt.where(WorkspaceMention.keyword == keyword)
    result = await session.execute(stmt)
    rows = result.all()
    return {platform or "unknown": int(count or 0) for platform, count in rows}


async def get_top_platform(session: AsyncSession, workspace_id: str, keyword: str | None = None) -> str:
    counts = await get_platform_counts(session, workspace_id, keyword)
    if not counts:
        return "unknown"
    return max(counts.items(), key=lambda item: item[1])[0]


async def get_top_emotions(
    session: AsyncSession, workspace_id: str, keyword: str | None = None
) -> list[tuple[str, int]]:
    stmt = (
        select(Mention.emotion, func.count())
        .select_from(WorkspaceMention)
        .join(Mention, WorkspaceMention.mention_url == Mention.url)
        .where(WorkspaceMention.workspace_id == workspace_id)
        .group_by(Mention.emotion)
        .order_by(func.count().desc())
    )
    if keyword:
        stmt = stmt.where(WorkspaceMention.keyword == keyword)
    result = await session.execute(stmt)
    rows = result.all()
    emotions = [(emotion or "unknown", int(count or 0)) for emotion, count in rows]
    return emotions[:5]


async def get_timeline_14_days(
    session: AsyncSession, workspace_id: str, keyword: str | None = None
) -> list[dict[str, int | str]]:
    days = 14
    start_date = (datetime.utcnow() - timedelta(days=days - 1)).date()
    start_dt = datetime.combine(start_date, datetime.min.time())

    stmt = (
        select(func.strftime("%Y-%m-%d", Mention.created_at), func.count())
        .select_from(WorkspaceMention)
        .join(Mention, WorkspaceMention.mention_url == Mention.url)
        .where(WorkspaceMention.workspace_id == workspace_id)
        .where(Mention.created_at >= start_dt)
        .group_by(func.strftime("%Y-%m-%d", Mention.created_at))
        .order_by(func.strftime("%Y-%m-%d", Mention.created_at))
    )
    if keyword:
        stmt = stmt.where(WorkspaceMention.keyword == keyword)

    result = await session.execute(stmt)
    rows = result.all()

    counts_by_date: dict[date, int] = {}
    for dt_str, count in rows:
        dt = date.fromisoformat(dt_str)
        counts_by_date[dt] = int(count or 0)

    timeline: list[dict[str, int | str]] = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        timeline.append({"date": day.isoformat(), "count": counts_by_date.get(day, 0)})

    return timeline


def dominant_sentiment(sentiment_counts: dict[str, int]) -> str:
    if not sentiment_counts:
        return "neutral"
    return max(sentiment_counts.items(), key=lambda x: x[1])[0]


async def get_share_of_voice(
    session: AsyncSession,
    workspace_id: str,
) -> list[dict[str, int | str]]:
    """
    Count mentions grouped by keyword for share-of-voice.
    """
    stmt = (
        select(TrackedKeyword.keyword, TrackedKeyword.category, func.count())
        .select_from(WorkspaceMention)
        .join(
            TrackedKeyword,
            (TrackedKeyword.workspace_id == WorkspaceMention.workspace_id)
            & (TrackedKeyword.keyword == WorkspaceMention.keyword),
        )
        .where(WorkspaceMention.workspace_id == workspace_id)
        .where(TrackedKeyword.is_active == True)  # noqa: E712
        .group_by(TrackedKeyword.keyword, TrackedKeyword.category)
        .order_by(func.count().desc())
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        {"keyword": keyword, "category": category or "brand", "count": int(count or 0)}
        for keyword, category, count in rows
    ]


async def get_sentiment_benchmark(
    session: AsyncSession,
    workspace_id: str,
) -> list[dict[str, float | str]]:
    """
    Average sentiment score by keyword.
    Scores: positive=1, neutral=0, negative=-1.
    """
    sentiment_score = case(
        (func.lower(Mention.sentiment) == "positive", 1),
        (func.lower(Mention.sentiment) == "negative", -1),
        else_=0,
    )
    stmt = (
        select(TrackedKeyword.keyword, TrackedKeyword.category, func.avg(sentiment_score))
        .select_from(WorkspaceMention)
        .join(Mention, WorkspaceMention.mention_url == Mention.url)
        .join(
            TrackedKeyword,
            (TrackedKeyword.workspace_id == WorkspaceMention.workspace_id)
            & (TrackedKeyword.keyword == WorkspaceMention.keyword),
        )
        .where(WorkspaceMention.workspace_id == workspace_id)
        .where(TrackedKeyword.is_active == True)  # noqa: E712
        .group_by(TrackedKeyword.keyword, TrackedKeyword.category)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        {
            "keyword": keyword,
            "category": category or "brand",
            "average_sentiment": float(avg or 0.0),
        }
        for keyword, category, avg in rows
    ]


async def get_comparison_trends(
    session: AsyncSession,
    workspace_id: str,
) -> list[dict[str, int | str]]:
    """
    Return last 14 days of mention counts split by keyword.
    """
    days = 14
    start_date = (datetime.utcnow() - timedelta(days=days - 1)).date()
    start_dt = datetime.combine(start_date, datetime.min.time())

    keywords_stmt = (
        select(TrackedKeyword.keyword)
        .where(TrackedKeyword.workspace_id == workspace_id)
        .where(TrackedKeyword.is_active == True)  # noqa: E712
    )
    keyword_result = await session.execute(keywords_stmt)
    keywords = [row[0] for row in keyword_result.all()]

    stmt = (
        select(
            func.strftime("%Y-%m-%d", Mention.created_at),
            WorkspaceMention.keyword,
            func.count(),
        )
        .select_from(WorkspaceMention)
        .join(Mention, WorkspaceMention.mention_url == Mention.url)
        .join(
            TrackedKeyword,
            (TrackedKeyword.workspace_id == WorkspaceMention.workspace_id)
            & (TrackedKeyword.keyword == WorkspaceMention.keyword),
        )
        .where(WorkspaceMention.workspace_id == workspace_id)
        .where(Mention.created_at >= start_dt)
        .where(TrackedKeyword.is_active == True)  # noqa: E712
        .group_by(func.strftime("%Y-%m-%d", Mention.created_at), WorkspaceMention.keyword)
        .order_by(func.strftime("%Y-%m-%d", Mention.created_at))
    )
    result = await session.execute(stmt)
    rows = result.all()

    counts_by_date: dict[date, dict[str, int]] = {
        start_date + timedelta(days=i): dict.fromkeys(keywords, 0)
        for i in range(days)
    }

    for dt_str, keyword, count in rows:
        dt = date.fromisoformat(dt_str)
        if dt not in counts_by_date:
            counts_by_date[dt] = dict.fromkeys(keywords, 0)
        counts_by_date[dt][keyword] = int(count or 0)

    timeline: list[dict[str, int | str]] = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        row: dict[str, int | str] = {"date": day.isoformat()}
        for keyword in keywords:
            row[keyword] = counts_by_date[day].get(keyword, 0)
        timeline.append(row)

    return timeline


async def get_reach_analytics(
    session: AsyncSession,
    workspace_id: str,
) -> tuple[int, list[dict[str, int | str]]]:
    """
    Compute total estimated reach and top 5 impactful mentions for a workspace.
    Impact score = (upvotes * 2) + (comments * 5) + 10.
    """
    impact_score = func.coalesce(Mention.upvotes, 0) * 2 + func.coalesce(Mention.comments, 0) * 5 + 10

    total_stmt = (
        select(func.sum(impact_score))
        .select_from(WorkspaceMention)
        .join(Mention, WorkspaceMention.mention_url == Mention.url)
        .where(WorkspaceMention.workspace_id == workspace_id)
    )
    total_result = await session.execute(total_stmt)
    total_reach = int(total_result.scalar() or 0)

    top_stmt = (
        select(
            Mention.url,
            Mention.platform,
            Mention.summary,
            WorkspaceMention.keyword,
            impact_score.label("impact_score"),
        )
        .select_from(WorkspaceMention)
        .join(Mention, WorkspaceMention.mention_url == Mention.url)
        .where(WorkspaceMention.workspace_id == workspace_id)
        .order_by(impact_score.desc())
        .limit(5)
    )
    top_result = await session.execute(top_stmt)
    rows = top_result.all()

    top_mentions = [
        {
            "url": url,
            "platform": platform or "unknown",
            "summary": summary or "",
            "keyword": keyword or "",
            "impact_score": int(score or 0),
        }
        for url, platform, summary, keyword, score in rows
    ]
    return total_reach, top_mentions
