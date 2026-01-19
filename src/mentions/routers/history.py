"""History Router for retrieving stored mentions from database."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from mentions.db.session import async_session_maker
from mentions.models.database import Mention, Workspace, WorkspaceMention
from mentions.scrapers.base import ScrapedItem

history_router = APIRouter(prefix="/api/v1", tags=["history"])


class HistoryResponse(BaseModel):
    """Response model for history endpoint."""

    workspace_id: str = Field(..., description="The workspace ID")
    total_mentions: int = Field(..., description="Total number of mentions in database")
    mentions: list[ScrapedItem] = Field(..., description="List of stored mentions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


@history_router.get("/history", response_model=HistoryResponse)
async def get_history(
    workspace_id: str = Query(..., min_length=1, description="Workspace ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Number of items per page"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (positive, negative, neutral)"),
    is_relevant: Optional[bool] = Query(None, description="Filter by relevance"),
    keyword: Optional[str] = Query(None, description="Filter by keyword/search term"),
) -> HistoryResponse:
    """
    Retrieve all stored mentions from the SQLite database.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page (1-200).
        platform: Optional platform filter.
        sentiment: Optional sentiment filter.
        is_relevant: Optional relevance filter.
        keyword: Optional keyword filter.

    Returns:
        HistoryResponse with paginated mentions and metadata.

    Raises:
        HTTPException: If query fails.
    """
    # Ensure workspace exists (outside try to satisfy ruff TRY301)
    async with async_session_maker() as session:
        ws_stmt = select(Workspace).where(Workspace.workspace_id == workspace_id)
        ws_result = await session.execute(ws_stmt)
        if ws_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found. Create one via GET /api/v1/workspace/new.",
            )

    try:
        async with async_session_maker() as session:
            # Base query: workspace_mentions join mentions
            base_query = (
                select(WorkspaceMention, Mention)
                .join(Mention, WorkspaceMention.mention_url == Mention.url)
                .where(WorkspaceMention.workspace_id == workspace_id)
            )

            if keyword:
                base_query = base_query.where(WorkspaceMention.keyword == keyword)
            if platform:
                base_query = base_query.where(Mention.platform == platform)
            if sentiment:
                base_query = base_query.where(Mention.sentiment == sentiment)
            if is_relevant is not None:
                base_query = base_query.where(Mention.is_relevant == is_relevant)

            # Count (simple count via fetch; acceptable for now, can optimize with COUNT(*) later)
            count_result = await session.execute(base_query)
            total_count = len(count_result.all())

            # Pagination
            offset = (page - 1) * page_size
            paginated_query = base_query.order_by(desc(WorkspaceMention.created_at)).offset(offset).limit(page_size)
            result = await session.execute(paginated_query)

            rows = result.all()
            scraped_items = [mention.to_scraped_item(keyword=wm.keyword) for wm, mention in rows]

            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

            return HistoryResponse(
                workspace_id=workspace_id,
                total_mentions=total_count,
                mentions=scraped_items,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {e!s}") from e
