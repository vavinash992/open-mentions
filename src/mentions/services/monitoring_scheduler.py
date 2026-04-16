"""Monitoring scheduler service for periodic keyword monitoring (FastAPI background task)."""

from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from mentions.scripts.periodic_monitor import monitor_keywords


class MonitoringScheduler:
    """Scheduler for running periodic keyword monitoring jobs."""

    def __init__(self, interval_hours: int = 6, filter_by: str = "week", max_results_per_platform: int = 50):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.interval_hours = interval_hours
        self.filter_by = filter_by
        self.max_results_per_platform = max_results_per_platform

    def start(self) -> None:
        """Start the scheduler and schedule periodic monitoring."""
        if self.scheduler and self.scheduler.running:
            logger.warning("Scheduler is already running")
            return

        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self._run_monitoring,
            trigger="interval",
            hours=self.interval_hours,
            id="periodic_monitoring",
            name="Periodic Keyword Monitoring",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(f"Monitoring scheduler started - will run every {self.interval_hours} hours")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Monitoring scheduler stopped")
            return

        logger.warning("Scheduler is not running")

    async def _run_monitoring(self) -> None:
        """Run the monitoring task across all workspaces."""
        try:
            logger.info("=" * 60)
            logger.info("Starting scheduled keyword monitoring")
            logger.info("=" * 60)

            summary = await monitor_keywords(
                filter_by=self.filter_by,
                max_results_per_platform=self.max_results_per_platform,
            )

            logger.info("=" * 60)
            logger.info("Scheduled monitoring completed successfully")
            logger.info(
                f"Summary: {summary.get('total_new_mentions', 0)} new mentions across {summary.get('total_keywords', 0)} keyword(s)"
            )
            logger.info("=" * 60)
        except Exception as e:
            logger.exception(f"Error during scheduled monitoring: {e}")

    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        return self.scheduler is not None and self.scheduler.running


_monitoring_scheduler: Optional[MonitoringScheduler] = None


def get_scheduler() -> MonitoringScheduler:
    """Get or create the global scheduler instance."""
    global _monitoring_scheduler
    if _monitoring_scheduler is None:
        _monitoring_scheduler = MonitoringScheduler()
    return _monitoring_scheduler
