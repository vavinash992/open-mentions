"""Analytics service for dashboard statistics."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
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
