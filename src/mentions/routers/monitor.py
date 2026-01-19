"""Monitor Router for manual monitoring triggers and scheduler status."""

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from mentions.services.scheduler import get_scheduler

monitor_router = APIRouter(prefix="/api/v1", tags=["monitor"])


class MonitoringResponse(BaseModel):
    """Response model for monitoring trigger."""

    message: str = Field(..., description="Status message")
    summary: dict = Field(..., description="Monitoring summary statistics")
    scheduler_status: str = Field(..., description="Current scheduler status")


class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status."""

    is_running: bool = Field(..., description="Whether the scheduler is running")
    interval_hours: int = Field(..., description="Interval between monitoring runs in hours")


@monitor_router.post("/monitor/trigger", response_model=MonitoringResponse)
async def trigger_monitoring() -> MonitoringResponse:
    """
    Manually trigger a monitoring run for all active keywords.

    This endpoint runs the monitoring immediately, regardless of the scheduled interval.

    Returns:
        MonitoringResponse with monitoring results and scheduler status.
    """
    try:
        scheduler = get_scheduler()
        logger.info("Manual monitoring trigger requested")

        # Trigger monitoring
        summary = await scheduler.trigger_manual()

        return MonitoringResponse(
            message="Monitoring completed successfully",
            summary=summary,
            scheduler_status="running" if scheduler.is_running() else "stopped",
        )

    except Exception as e:
        logger.exception(f"Error triggering manual monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Monitoring failed: {e!s}") from e


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
