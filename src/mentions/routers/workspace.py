"""Workspace Router for workspace ID generation."""

import secrets
import string

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from mentions.db.session import async_session_maker
from mentions.models.database import Workspace

workspace_router = APIRouter(prefix="/api/v1", tags=["workspace"])


class WorkspaceResponse(BaseModel):
    """Response model for new workspace creation."""

    workspace_id: str = Field(..., description="Unique 12-character workspace ID")
    message: str = Field(..., description="Status message")


def generate_workspace_id(length: int = 12) -> str:
    """
    Generate a random workspace ID.

    Args:
        length: Length of the workspace ID (default: 12).

    Returns:
        Random alphanumeric string of specified length.
    """
    # Use only lowercase letters and digits for readability
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@workspace_router.get("/workspace/new", response_model=WorkspaceResponse)
async def create_workspace() -> WorkspaceResponse:
    """
    Generate a new unique workspace ID.

    This endpoint returns a random 12-character string that can be used
    as a workspace identifier. No authentication required.

    Returns:
        WorkspaceResponse with the new workspace ID.
    """
    # Generate and persist a unique workspace_id
    async with async_session_maker() as session:
        while True:
            workspace_id = generate_workspace_id()
            exists_stmt = select(Workspace).where(Workspace.workspace_id == workspace_id)
            result = await session.execute(exists_stmt)
            if result.scalar_one_or_none() is None:
                break

        session.add(Workspace(workspace_id=workspace_id))
        await session.commit()

    return WorkspaceResponse(
        workspace_id=workspace_id,
        message="New workspace created. Save this ID - it's required for all API calls.",
    )
