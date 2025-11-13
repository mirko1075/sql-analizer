"""
Collector Health Monitoring Service.

Background task that monitors collector heartbeats and updates their status.
Marks collectors as OFFLINE if they haven't sent a heartbeat in the last 2 minutes.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

from sqlalchemy.orm import Session
from db.models_multitenant import Collector, CollectorStatus
from db.session import get_db_context

logger = logging.getLogger(__name__)


class CollectorHealthMonitor:
    """
    Background service that monitors collector health.

    Checks all collectors periodically and marks them as OFFLINE
    if they haven't sent a heartbeat in the last 2 minutes.
    """

    def __init__(self, check_interval_seconds: int = 30):
        """
        Initialize health monitor.

        Args:
            check_interval_seconds: How often to check collector health (default: 30s)
        """
        self.check_interval_seconds = check_interval_seconds
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the health monitor background task."""
        if self.is_running:
            logger.warning("CollectorHealthMonitor is already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"🩺 CollectorHealthMonitor started (check interval: {self.check_interval_seconds}s)")

    async def stop(self):
        """Stop the health monitor background task."""
        if not self.is_running:
            return

        self.is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("🩺 CollectorHealthMonitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            try:
                await self._check_collector_health()
            except Exception as e:
                logger.error(f"Error in collector health check: {e}", exc_info=True)

            # Wait before next check
            await asyncio.sleep(self.check_interval_seconds)

    async def _check_collector_health(self):
        """
        Check health of all collectors.

        Marks collectors as OFFLINE if last heartbeat is older than 2 minutes.
        Also cleans up expired commands.
        """
        try:
            with get_db_context() as db:
                # Get all collectors that are not already offline/stopped
                collectors = db.query(Collector).filter(
                    Collector.status.in_([CollectorStatus.ONLINE, CollectorStatus.ERROR, CollectorStatus.STARTING])
                ).all()

                offline_count = 0
                timeout_threshold = datetime.utcnow() - timedelta(minutes=2)

                for collector in collectors:
                    # Check if last heartbeat is too old
                    if not collector.last_heartbeat or collector.last_heartbeat < timeout_threshold:
                        # Mark as offline
                        old_status = collector.status
                        collector.status = CollectorStatus.OFFLINE

                        if old_status != CollectorStatus.OFFLINE:
                            logger.warning(
                                f"Collector {collector.id} ({collector.name}) marked as OFFLINE "
                                f"(last heartbeat: {collector.last_heartbeat})"
                            )
                            offline_count += 1

                # Clean up expired commands
                from db.models_multitenant import CollectorCommand
                expired_commands = db.query(CollectorCommand).filter(
                    CollectorCommand.executed == False,
                    CollectorCommand.expires_at < datetime.utcnow()
                ).delete()

                if offline_count > 0 or expired_commands > 0:
                    if offline_count > 0:
                        logger.info(f"Marked {offline_count} collectors as OFFLINE")
                    if expired_commands > 0:
                        logger.info(f"Cleaned up {expired_commands} expired commands")

        except Exception as e:
            logger.error(f"Error checking collector health: {e}", exc_info=True)

    def get_status(self) -> dict:
        """Get monitor status."""
        return {
            "is_running": self.is_running,
            "check_interval_seconds": self.check_interval_seconds
        }


# Global monitor instance
_health_monitor: Optional[CollectorHealthMonitor] = None


def get_health_monitor() -> CollectorHealthMonitor:
    """Get the global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = CollectorHealthMonitor()
    return _health_monitor


async def start_health_monitor():
    """Start the global health monitor."""
    monitor = get_health_monitor()
    await monitor.start()


async def stop_health_monitor():
    """Stop the global health monitor."""
    monitor = get_health_monitor()
    await monitor.stop()
