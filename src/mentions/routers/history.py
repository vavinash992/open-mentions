"""History Router for retrieving stored mentions from database."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from mentions.db.session import async_session_maker
from mentions.models.database import Mention
from mentions.scrapers.base import ScrapedItem

history_router = APIRouter(prefix="/api/v1", tags=["history"])


class HistoryResponse(BaseModel):
    """Response model for history endpoint."""

    total_mentions: int = Field(..., description="Total number of mentions in database")
    mentions: list[ScrapedItem] = Field(..., description="List of stored mentions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


@history_router.get("/history", response_model=HistoryResponse)
async def get_history(
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
    try:
        async with async_session_maker() as session:
            # Build base query with filters
            base_query = select(Mention)

            if platform:
                base_query = base_query.where(Mention.platform == platform)
            if sentiment:
                base_query = base_query.where(Mention.sentiment == sentiment)
            if is_relevant is not None:
                base_query = base_query.where(Mention.is_relevant == is_relevant)
            if keyword:
                base_query = base_query.where(Mention.keyword == keyword)

            # Get total count before pagination
            count_result = await session.execute(base_query)
            all_mentions = count_result.scalars().all()
            total_count = len(all_mentions)

            # Order by created_at descending (newest first) and apply pagination
            offset = (page - 1) * page_size
            paginated_query = base_query.order_by(desc(Mention.created_at)).offset(offset).limit(page_size)

            # Execute paginated query
            result = await session.execute(paginated_query)
            mentions = result.scalars().all()

            # Convert to ScrapedItem
            scraped_items = [mention.to_scraped_item() for mention in mentions]

            # Calculate total pages
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

            return HistoryResponse(
                total_mentions=total_count,
                mentions=scraped_items,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {e!s}") from e
