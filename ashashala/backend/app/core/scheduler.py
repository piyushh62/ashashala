"""APScheduler wrapper — process-local, in-memory job store.

Fine at pilot/single-worker scale; revisit (e.g. move to Celery beat) if this
ever needs to run correctly across multiple workers/processes.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.db.session import async_session_factory
from app.services.notification_dispatch import dispatch_pending_notifications

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_dispatch_job() -> None:
    async with async_session_factory() as db:
        count = await dispatch_pending_notifications(db)
        if count:
            logger.info("Dispatched %d pending notification(s)", count)


def start_scheduler() -> AsyncIOScheduler | None:
    """Start the background scheduler; no-ops under test/mocked settings.

    This guard is defense-in-depth: today's test harness never runs
    `lifespan()` at all (its ASGI transport has no lifespan support), so this
    is never actually exercised by pytest — but that's incidental to how the
    fixture happens to be built, not a guarantee.
    """
    global _scheduler
    if settings.ENVIRONMENT == "test" or settings.MOCK_EXTERNAL_SERVICES:
        return None
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_dispatch_job, "interval",
        seconds=settings.NOTIFICATION_DISPATCH_INTERVAL_SECONDS,
        max_instances=1, coalesce=True, id="notification_dispatch",
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
