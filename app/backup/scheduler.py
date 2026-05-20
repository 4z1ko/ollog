from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


def make_scheduler(cron_expr: str, job_func) -> AsyncIOScheduler:
    """Create and configure an AsyncIOScheduler for the given cron expression.

    Returns the scheduler without starting it — the caller (lifespan) is
    responsible for calling scheduler.start().  Pin: apscheduler>=3.10,<4
    (v4 alpha removed AsyncIOScheduler entirely).
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_func, CronTrigger.from_crontab(cron_expr))
    return scheduler
