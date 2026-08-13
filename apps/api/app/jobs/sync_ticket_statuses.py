import asyncio
import logging

from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.modules.support.service import sync_ticket_statuses

configure_logging()
logger = logging.getLogger("app.jobs.sync_ticket_statuses")


async def main() -> None:
    async with SessionLocal() as db:
        resolved_count = await sync_ticket_statuses(db)
    logger.info("sync_ticket_statuses_completed", extra={"resolved_count": resolved_count})


if __name__ == "__main__":
    asyncio.run(main())