"""Monitor Router for manual monitoring triggers and scheduler status."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select

from mentions.db.session import async_session_maker
from mentions.models.database import (
    TrackedKeyword,
    Workspace,
    WorkspaceRateLimit,
    WorkspaceTriggerJob,
)
from mentions.services.monitoring_scheduler import get_scheduler
from mentions.services.orchestrator import SearchOrchestrator

monitor_router = APIRouter(prefix="/api/v1", tags=["monitor"])

# Rate limit: one manual trigger per 30 minutes per workspace
RATE_LIMIT_MINUTES = 30


class MonitoringResponse(BaseModel):
    """Response model for monitoring trigger."""

    message: str = Field(..., description="Status message")
    workspace_id: str = Field(..., description="The workspace ID")
    summary: dict = Field(..., description="Monitoring summary statistics")
    next_allowed_trigger: str | None = Field(None, description="When next trigger is allowed (if rate limited)")


class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status."""

    is_running: bool = Field(..., description="Whether the scheduler is running")
    interval_hours: int = Field(..., description="Interval between monitoring runs in hours")


class WorkspaceMonitoringResponse(BaseModel):
    """Response model for workspace-specific monitoring trigger."""

    message: str = Field(..., description="Status message")
    workspace_id: str = Field(..., description="The workspace ID")
    keywords_processed: int = Field(..., description="Number of keywords processed")
    total_new_mentions: int = Field(..., description="Total new mentions found")
    keyword_results: list[dict] = Field(..., description="Results per keyword")


class TriggerJobResponse(BaseModel):
    """Response model for async monitoring trigger."""

    message: str = Field(..., description="Status message")
    workspace_id: str = Field(..., description="The workspace ID")
    job_id: str = Field(..., description="Background job ID")
    status: str = Field(..., description="Job status")


class MonitorJobStatusResponse(BaseModel):
    """Response model for monitoring job status."""

    job_id: str = Field(..., description="Job ID")
    workspace_id: str = Field(..., description="Workspace ID")
    status: str = Field(..., description="Job status")
    created_at: str = Field(..., description="Creation timestamp")
    started_at: str | None = Field(None, description="Start timestamp")
    completed_at: str | None = Field(None, description="Completion timestamp")
    keywords_processed: int | None = Field(None, description="Number of keywords processed")
    total_new_mentions: int | None = Field(None, description="Total new mentions found")
    keyword_results: list[dict] | None = Field(None, description="Results per keyword")
    error: str | None = Field(None, description="Error message if failed")


async def check_rate_limit(workspace_id: str) -> tuple[bool, datetime | None]:
    """
    Check if a workspace is rate limited.

    Args:
        workspace_id: The workspace ID to check.

    Returns:
        Tuple of (is_allowed, next_allowed_time).
        If is_allowed is True, next_allowed_time is None.
    """
    async with async_session_maker() as session:
        statement = select(WorkspaceRateLimit).where(WorkspaceRateLimit.workspace_id == workspace_id)
        result = await session.execute(statement)
        rate_limit = result.scalar_one_or_none()

        if not rate_limit or not rate_limit.last_trigger_at:
            return True, None

        # Check if enough time has passed
        last_trigger_at = rate_limit.last_trigger_at
        # SQLite may return naive datetimes; treat them as UTC
        if last_trigger_at.tzinfo is None:
            last_trigger_at = last_trigger_at.replace(tzinfo=timezone.utc)

        min_next_trigger = last_trigger_at + timedelta(minutes=RATE_LIMIT_MINUTES)
        now = datetime.now(timezone.utc)

        if now >= min_next_trigger:
            return True, None

        return False, min_next_trigger


async def update_rate_limit(workspace_id: str) -> None:
    """
    Update the rate limit timestamp for a workspace.

    Args:
        workspace_id: The workspace ID to update.
    """
    async with async_session_maker() as session:
        statement = select(WorkspaceRateLimit).where(WorkspaceRateLimit.workspace_id == workspace_id)
        result = await session.execute(statement)
        rate_limit = result.scalar_one_or_none()

        if rate_limit:
            rate_limit.last_trigger_at = datetime.now(timezone.utc)
        else:
            rate_limit = WorkspaceRateLimit(
                workspace_id=workspace_id,
                last_trigger_at=datetime.now(timezone.utc),
            )

        session.add(rate_limit)
        await session.commit()


async def _run_monitor_job(job_id: str, workspace_id: str, keywords: list[dict]) -> None:
    orchestrator = SearchOrchestrator()
    total_new_mentions = 0
    keyword_results: list[dict] = []
    started_at = datetime.now(timezone.utc)

    async with async_session_maker() as session:
        stmt = select(WorkspaceTriggerJob).where(WorkspaceTriggerJob.job_id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
        if job:
            job.status = "running"
            job.started_at = started_at
            session.add(job)
            await session.commit()

    for tracked_keyword in keywords:
        try:
            mentions = await orchestrator.search_all_platforms(
                company_name=tracked_keyword["keyword"],
                filter_by="week",
                max_results_per_platform=50,
                workspace_id=workspace_id,
                include_existing=False,
            )

            async with async_session_maker() as session:
                stmt = select(TrackedKeyword).where(TrackedKeyword.id == tracked_keyword["id"])
                res = await session.execute(stmt)
                kw = res.scalar_one_or_none()
                if kw:
                    kw.last_searched_at = datetime.now(timezone.utc)
                    session.add(kw)
                    await session.commit()

            mentions_count = len(mentions)
            total_new_mentions += mentions_count
            keyword_results.append(
                {
                    "keyword": tracked_keyword["keyword"],
                    "new_mentions": mentions_count,
                    "status": "success",
                }
            )
        except Exception as e:
            logger.error(f"Error processing keyword '{tracked_keyword['keyword']}': {e}")
            keyword_results.append(
                {
                    "keyword": tracked_keyword["keyword"],
                    "new_mentions": 0,
                    "status": "error",
                    "error": str(e),
                }
            )

    completed_at = datetime.now(timezone.utc)
    async with async_session_maker() as session:
        stmt = select(WorkspaceTriggerJob).where(WorkspaceTriggerJob.job_id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
        if job:
            job.status = "completed"
            job.completed_at = completed_at
            job.keywords_processed = len(keywords)
            job.total_new_mentions = total_new_mentions
            job.keyword_results = json.dumps(keyword_results)
            session.add(job)
            await session.commit()


def _serialize_job(job: WorkspaceTriggerJob) -> MonitorJobStatusResponse:
    keyword_results = json.loads(job.keyword_results) if job.keyword_results else None
    return MonitorJobStatusResponse(
        job_id=job.job_id,
        workspace_id=job.workspace_id,
        status=job.status,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        keywords_processed=job.keywords_processed,
        total_new_mentions=job.total_new_mentions,
        keyword_results=keyword_results,
        error=job.error,
    )


@monitor_router.post("/monitor/trigger", response_model=TriggerJobResponse, status_code=202)
async def trigger_monitoring(
    workspace_id: str | None = Query(None, description="Workspace ID"),
    workspace_id_header: str | None = Header(None, alias="X-Workspace-ID", description="Workspace ID (legacy)"),
) -> TriggerJobResponse:
    """
    Manually trigger a monitoring run for a workspace's active keywords.

    Rate limited to once every 30 minutes per workspace.

    Args:
        workspace_id: Workspace ID from header.

    Returns:
        WorkspaceMonitoringResponse with monitoring results.

    Raises:
        HTTPException: If rate limited or no keywords found.
    """
    # Resolve workspace_id (prefer query param)
    workspace_id = workspace_id or workspace_id_header
    if not workspace_id:
        raise HTTPException(
            status_code=400,
            detail="workspace_id is required (pass as query param ?workspace_id=... or header X-Workspace-ID).",
        )

    # Ensure workspace exists
    async with async_session_maker() as session:
        ws_stmt = select(Workspace).where(Workspace.workspace_id == workspace_id)
        ws_result = await session.execute(ws_stmt)
        if ws_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=404,
                detail="Workspace not found. Create one via GET /api/v1/workspace/new.",
            )

    # Check rate limit
    is_allowed, next_allowed = await check_rate_limit(workspace_id)

    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": f"Rate limit exceeded. Please wait {RATE_LIMIT_MINUTES} minutes between triggers.",
                "next_allowed_trigger": next_allowed.isoformat() if next_allowed else None,
            },
        )

    logger.info(f"Manual monitoring trigger requested for workspace '{workspace_id}'")

    # Fetch active keywords for this workspace
    async with async_session_maker() as session:
        statement = (
            select(TrackedKeyword)
            .where(TrackedKeyword.workspace_id == workspace_id)
            .where(TrackedKeyword.is_active == True)  # noqa: E712
        )
        result = await session.execute(statement)
        keywords = result.scalars().all()

    if not keywords:
        raise HTTPException(
            status_code=404,
            detail="No active keywords found for this workspace. Add keywords first.",
        )

    # Update rate limit and create job
    await update_rate_limit(workspace_id)
    job_id = uuid4().hex

    async with async_session_maker() as session:
        job = WorkspaceTriggerJob(
            job_id=job_id,
            workspace_id=workspace_id,
            status="pending",
        )
        session.add(job)
        await session.commit()

    keyword_payload = [{"id": kw.id, "keyword": kw.keyword} for kw in keywords]
    task = asyncio.create_task(_run_monitor_job(job_id, workspace_id, keyword_payload))
    logger.debug("Started monitoring job task %s for workspace %s", task.get_name(), workspace_id)

    return TriggerJobResponse(
        message="Monitoring job queued",
        workspace_id=workspace_id,
        job_id=job_id,
        status="pending",
    )


@monitor_router.get("/monitor/jobs/{job_id}", response_model=MonitorJobStatusResponse)
async def get_job_status(job_id: str) -> MonitorJobStatusResponse:
    """Return background monitoring job status."""
    async with async_session_maker() as session:
        stmt = select(WorkspaceTriggerJob).where(WorkspaceTriggerJob.job_id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
    return _serialize_job(job)


@monitor_router.get("/monitor/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status() -> SchedulerStatusResponse:
    """
    Get the current status of the monitoring scheduler.

    Returns:
        SchedulerStatusResponse with scheduler status information.
    """
    scheduler = get_scheduler()
    return SchedulerStatusResponse(
        is_running=scheduler.is_running(),
        interval_hours=scheduler.interval_hours,
    )
