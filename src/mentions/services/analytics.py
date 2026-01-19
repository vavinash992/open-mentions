"""Analytics service for dashboard statistics."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

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


async def get_total_mentions(session: AsyncSession, workspace_id: str, keyword: str | None = None) -> int:
    """Return total mentions for workspace (optionally filtered by keyword)."""
    stmt = select(func.count()).select_from(WorkspaceMention).where(WorkspaceMention.workspace_id == workspace_id)
    if keyword:
        stmt = stmt.where(WorkspaceMention.keyword == keyword)
    result = await session.execute(stmt)
    return int(result.scalar() or 0)


async def get_sentiment_stats(session: AsyncSession, workspace_id: str, keyword: str | None = None) -> dict[str, int]:
    """Return sentiment counts for a workspace."""
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
    stats: dict[str, int] = {}
    for sentiment, count in rows:
        key = sentiment or "unknown"
        stats[key] = int(count or 0)
    return stats


async def get_platform_stats(session: AsyncSession, workspace_id: str, keyword: str | None = None) -> dict[str, int]:
    """Return platform counts for a workspace."""
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
    session: AsyncSession, workspace_id: str, keyword: str | None = None, limit: int = 3
) -> list[tuple[str, int]]:
    """Return top emotions by count."""
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
    return emotions[:limit]


async def get_timeline_counts(
    session: AsyncSession, workspace_id: str, days: int, keyword: str | None = None
) -> list[dict[str, int | str]]:
    """Return mention counts per day for the last N days."""
    if days not in {7, 30}:
        raise InvalidDaysError

    start_date = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date()

    stmt = (
        select(func.date(WorkspaceMention.created_at), func.count())
        .select_from(WorkspaceMention)
        .where(WorkspaceMention.workspace_id == workspace_id)
        .where(WorkspaceMention.created_at >= start_date)
        .group_by(func.date(WorkspaceMention.created_at))
        .order_by(func.date(WorkspaceMention.created_at))
    )
    if keyword:
        stmt = stmt.where(WorkspaceMention.keyword == keyword)

    result = await session.execute(stmt)
    rows = result.all()

    counts_by_date: dict[date, int] = {}
    for dt, count in rows:
        if isinstance(dt, str):
            dt = date.fromisoformat(dt)
        counts_by_date[dt] = int(count or 0)

    timeline: list[dict[str, int | str]] = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        timeline.append({"date": day.isoformat(), "count": counts_by_date.get(day, 0)})

    return timeline
