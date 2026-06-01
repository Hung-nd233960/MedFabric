"""APScheduler setup — 12-hour Telegram report jobs."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_12h_report() -> None:
    from app.core.database import SessionLocal
    from app.services.telegram import send_12h_report

    db = SessionLocal()
    try:
        await send_12h_report(db)
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    tz = get_settings().scheduler_timezone or "UTC"
    _scheduler = AsyncIOScheduler(timezone=tz)
    _scheduler.add_job(
        _run_12h_report,
        CronTrigger(hour="9,21", minute=0, timezone=tz),
        id="12h_report",
        name="12h Telegram report",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started (timezone=%s)", tz)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
