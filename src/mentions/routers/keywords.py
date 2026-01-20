"""Keywords Router for managing tracked keywords per workspace."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from mentions.db.session import async_session_maker
from mentions.models.database import TrackedKeyword, Workspace

keywords_router = APIRouter(prefix="/api/v1", tags=["keywords"])

# Maximum number of active keywords per workspace
MAX_KEYWORDS_PER_WORKSPACE = 5


class KeywordCreateRequest(BaseModel):
    """Request model for creating a new tracked keyword."""

    keyword: str = Field(..., min_length=1, max_length=100, description="The keyword to track")
    category: str = Field(
        default="brand",
        description="Keyword category (e.g., brand or competitor)",
    )
    importance_score: int = Field(
        default=1,
        ge=1,
        description="Priority weight for this keyword",
    )


class KeywordResponse(BaseModel):
    """Response model for a single keyword."""

    id: int = Field(..., description="Unique identifier")
    keyword: str = Field(..., description="The tracked keyword")
    category: str = Field(..., description="Keyword category")
    importance_score: int = Field(..., description="Priority weight for this keyword")
    is_active: bool = Field(..., description="Whether the keyword is active")
    last_searched_at: Optional[str] = Field(None, description="Last search timestamp")
    created_at: str = Field(..., description="Creation timestamp")


class KeywordListResponse(BaseModel):
    """Response model for listing keywords."""

    workspace_id: str = Field(..., description="The workspace ID")
    total_keywords: int = Field(..., description="Total number of keywords")
    active_keywords: int = Field(..., description="Number of active keywords")
    max_allowed: int = Field(..., description="Maximum keywords allowed per workspace")
    keywords: list[KeywordResponse] = Field(..., description="List of keywords")


class KeywordDeleteResponse(BaseModel):
    """Response model for deleting a keyword."""

    message: str = Field(..., description="Status message")
    keyword_id: int = Field(..., description="Deleted keyword ID")


@keywords_router.post("/keywords", response_model=KeywordResponse)
async def create_keyword(
    request: KeywordCreateRequest,
    workspace_id: str = Header(..., alias="X-Workspace-ID", description="Workspace ID"),
) -> KeywordResponse:
    """
    Create a new tracked keyword for a workspace.

    A workspace can have a maximum of 5 active keywords to protect API costs.

    Args:
        request: Keyword creation request with the keyword to track.
        workspace_id: Workspace ID from header.

    Returns:
        KeywordResponse with the created keyword details.

    Raises:
        HTTPException: If limit exceeded or keyword already exists.
    """
    async with async_session_maker() as session:
        # Ensure workspace exists
        ws_stmt = select(Workspace).where(Workspace.workspace_id == workspace_id)
        ws_result = await session.execute(ws_stmt)
        if ws_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found. Create one via GET /api/v1/workspace/new.",
            )

        # Check current active keyword count for this workspace
        count_statement = (
            select(func.count())
            .select_from(TrackedKeyword)
            .where(TrackedKeyword.workspace_id == workspace_id)
            .where(TrackedKeyword.is_active == True)  # noqa: E712
        )
        result = await session.execute(count_statement)
        active_count = result.scalar() or 0

    if active_count >= MAX_KEYWORDS_PER_WORKSPACE:
        raise HTTPException(
            status_code=403,
            detail=f"Keyword limit reached: Maximum {MAX_KEYWORDS_PER_WORKSPACE} active keywords allowed per workspace.",
        )

    async with async_session_maker() as session:
        # Check if keyword already exists for this workspace
        existing_statement = (
            select(TrackedKeyword)
            .where(TrackedKeyword.workspace_id == workspace_id)
            .where(TrackedKeyword.keyword == request.keyword)
        )
        existing_result = await session.execute(existing_statement)
        existing_keyword = existing_result.scalar_one_or_none()

        if existing_keyword:
            if existing_keyword.is_active:
                raise HTTPException(
                    status_code=409,
                    detail=f"Keyword '{request.keyword}' already exists and is active for this workspace.",
                )
            # Reactivate existing keyword
            existing_keyword.is_active = True
            existing_keyword.category = request.category
            existing_keyword.importance_score = request.importance_score
            session.add(existing_keyword)
            await session.commit()
            await session.refresh(existing_keyword)

            return KeywordResponse(
                id=existing_keyword.id,
                keyword=existing_keyword.keyword,
                category=existing_keyword.category,
                importance_score=existing_keyword.importance_score,
                is_active=existing_keyword.is_active,
                last_searched_at=existing_keyword.last_searched_at.isoformat()
                if existing_keyword.last_searched_at
                else None,
                created_at=existing_keyword.created_at.isoformat(),
            )

        # Create new keyword
        new_keyword = TrackedKeyword(
            workspace_id=workspace_id,
            keyword=request.keyword,
            category=request.category,
            importance_score=request.importance_score,
            is_active=True,
        )
        session.add(new_keyword)
        await session.commit()
        await session.refresh(new_keyword)

        logger.info(f"Created keyword '{request.keyword}' for workspace '{workspace_id}'")

        return KeywordResponse(
            id=new_keyword.id,
            keyword=new_keyword.keyword,
            category=new_keyword.category,
            importance_score=new_keyword.importance_score,
            is_active=new_keyword.is_active,
            last_searched_at=None,
            created_at=new_keyword.created_at.isoformat(),
        )


@keywords_router.get("/keywords", response_model=KeywordListResponse)
async def list_keywords(
    workspace_id: str = Header(..., alias="X-Workspace-ID", description="Workspace ID"),
    include_inactive: bool = Query(False, description="Include inactive keywords"),
) -> KeywordListResponse:
    """
    List all tracked keywords for a workspace.

    Args:
        workspace_id: Workspace ID from header.
        include_inactive: Whether to include inactive keywords.

    Returns:
        KeywordListResponse with all keywords for the workspace.
    """
    async with async_session_maker() as session:
        # Build query
        statement = select(TrackedKeyword).where(TrackedKeyword.workspace_id == workspace_id)

        if not include_inactive:
            statement = statement.where(TrackedKeyword.is_active == True)  # noqa: E712

        result = await session.execute(statement)
        keywords = result.scalars().all()

        # Count active keywords
        active_count = sum(1 for k in keywords if k.is_active)
        total_count = len(keywords) if include_inactive else active_count

        return KeywordListResponse(
            workspace_id=workspace_id,
            total_keywords=total_count,
            active_keywords=active_count,
            max_allowed=MAX_KEYWORDS_PER_WORKSPACE,
            keywords=[
                KeywordResponse(
                    id=k.id,
                    keyword=k.keyword,
                    category=k.category,
                    importance_score=k.importance_score,
                    is_active=k.is_active,
                    last_searched_at=k.last_searched_at.isoformat() if k.last_searched_at else None,
                    created_at=k.created_at.isoformat(),
                )
                for k in keywords
            ],
        )


@keywords_router.delete("/keywords/{keyword_id}", response_model=KeywordDeleteResponse)
async def delete_keyword(
    keyword_id: int,
    workspace_id: str = Header(..., alias="X-Workspace-ID", description="Workspace ID"),
) -> KeywordDeleteResponse:
    """
    Deactivate a tracked keyword (soft delete).

    Args:
        keyword_id: The keyword ID to delete.
        workspace_id: Workspace ID from header.

    Returns:
        KeywordDeleteResponse with deletion confirmation.

    Raises:
        HTTPException: If keyword not found or doesn't belong to workspace.
    """
    async with async_session_maker() as session:
        # Find keyword
        statement = (
            select(TrackedKeyword)
            .where(TrackedKeyword.id == keyword_id)
            .where(TrackedKeyword.workspace_id == workspace_id)
        )
        result = await session.execute(statement)
        keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(
            status_code=404,
            detail=f"Keyword with ID {keyword_id} not found in this workspace.",
        )

    async with async_session_maker() as session:
        # Re-fetch to avoid detached instance
        statement = select(TrackedKeyword).where(TrackedKeyword.id == keyword_id)
        result = await session.execute(statement)
        kw = result.scalar_one_or_none()
        if kw:
            # Soft delete (deactivate)
            kw.is_active = False
            session.add(kw)
            await session.commit()

            logger.info(f"Deactivated keyword '{kw.keyword}' (ID: {keyword_id}) for workspace '{workspace_id}'")

            return KeywordDeleteResponse(
                message=f"Keyword '{kw.keyword}' has been deactivated.",
                keyword_id=keyword_id,
            )

    raise HTTPException(
        status_code=404,
        detail=f"Keyword with ID {keyword_id} not found.",
    )
