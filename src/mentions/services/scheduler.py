"""Scheduler service for periodic keyword monitoring."""

from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from mentions.scripts.periodic_monitor import monitor_keywords


class MonitoringScheduler:
    """Scheduler for running periodic keyword monitoring jobs."""

    def __init__(self, interval_hours: int = 6, filter_by: str = "week", max_results_per_platform: int = 50):
        """
        Initialize the monitoring scheduler.

        Args:
            interval_hours: Number of hours between monitoring runs (default: 6).
            filter_by: Time filter for scraping (e.g., 'day', 'week', 'month').
            max_results_per_platform: Maximum results to fetch per platform.
        """
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.interval_hours = interval_hours
        self.filter_by = filter_by
        self.max_results_per_platform = max_results_per_platform

    def start(self) -> None:
        """Start the scheduler and schedule periodic monitoring."""
        if self.scheduler and self.scheduler.running:
            logger.warning("Scheduler is already running")
            return

        # Create async scheduler
        self.scheduler = AsyncIOScheduler()

        # Schedule periodic monitoring job
        # Run every N hours
        self.scheduler.add_job(
            self._run_monitoring,
            trigger="interval",
            hours=self.interval_hours,
            id="periodic_monitoring",
            name="Periodic Keyword Monitoring",
            replace_existing=True,
        )

        # Start the scheduler
        self.scheduler.start()
        logger.info(f"Monitoring scheduler started - will run every {self.interval_hours} hours")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Monitoring scheduler stopped")
        else:
            logger.warning("Scheduler is not running")

    async def _run_monitoring(self) -> None:
        """
        Run the monitoring task (wrapper for monitor_keywords).

        This method is called by the scheduler at the specified intervals.
        """
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
                f"Summary: {summary['total_new_mentions']} new mentions found across {summary['total_keywords']} keyword(s)"
            )
            logger.info("=" * 60)

        except Exception as e:
            logger.exception(f"Error during scheduled monitoring: {e}")

    async def trigger_manual(self) -> dict:
        """
        Manually trigger a monitoring run (for API endpoints).

        Returns:
            Dictionary with monitoring summary.
        """
        return await monitor_keywords(
            filter_by=self.filter_by,
            max_results_per_platform=self.max_results_per_platform,
        )

    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        return self.scheduler is not None and self.scheduler.running


# Global scheduler instance
_monitoring_scheduler: Optional[MonitoringScheduler] = None


def get_scheduler() -> MonitoringScheduler:
    """
    Get or create the global scheduler instance.

    Returns:
        MonitoringScheduler instance.
    """
    global _monitoring_scheduler

    if _monitoring_scheduler is None:
        _monitoring_scheduler = MonitoringScheduler()

    return _monitoring_scheduler
