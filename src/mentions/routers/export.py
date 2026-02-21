"""Export Router for downloading mentions as CSV."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select

from mentions.db.session import async_session_maker
from mentions.models.database import Mention, Workspace, WorkspaceMention

export_router = APIRouter(prefix="/api/v1", tags=["export"])


@export_router.get("/export/csv")
async def export_csv(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
    keyword: str | None = Query(None, description="Filter by keyword"),
    platform: str | None = Query(None, description="Filter by platform"),
    sentiment: str | None = Query(None, description="Filter by sentiment"),
) -> StreamingResponse:
    """
    Export all workspace mentions as a downloadable CSV file.
    """
    # Verify workspace exists
    async with async_session_maker() as session:
        ws_result = await session.execute(select(Workspace).where(Workspace.workspace_id == workspace_id))
        if ws_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Workspace not found.")

    try:
        async with async_session_maker() as session:
            query = (
                select(WorkspaceMention, Mention)
                .join(Mention, WorkspaceMention.mention_url == Mention.url)
                .where(WorkspaceMention.workspace_id == workspace_id)
            )

            if keyword:
                query = query.where(WorkspaceMention.keyword == keyword)
            if platform:
                query = query.where(Mention.platform == platform)
            if sentiment:
                query = query.where(Mention.sentiment == sentiment)

            query = query.order_by(desc(WorkspaceMention.created_at))
            result = await session.execute(query)
            rows = result.all()

        # Build CSV in memory
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "Keyword",
            "Platform",
            "Content",
            "URL",
            "Sentiment",
            "Emotion",
            "Summary",
            "Themes",
            "Relevance Score",
            "Upvotes",
            "Comments",
            "User",
            "Timestamp",
            "Mention Type",
        ])

        for wm, mention in rows:
            writer.writerow([
                wm.keyword,
                mention.platform,
                mention.content,
                mention.url,
                mention.sentiment or "",
                mention.emotion or "",
                mention.summary or "",
                mention.themes or "",
                mention.relevance_score or "",
                mention.upvotes or "",
                mention.comments or "",
                mention.user_id or "",
                mention.timestamp or "",
                mention.mention_type or "",
            ])

        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=mentions_{workspace_id}.csv"},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e!s}") from e
