import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from app.core.config import settings
from app.core.database import Base
from app.modules.analytics.models import UsageEvent  # noqa: F401 — registers metadata
from app.modules.auth.models import Org, User  # noqa: F401 — registers metadata
from app.modules.cloud_configs.models import CloudConfig  # noqa: F401 — registers metadata
from app.modules.datasets.models import Dataset  # noqa: F401 — registers metadata
from app.modules.enterprise.models import AuditLog, Invite  # noqa: F401 — registers metadata
from app.modules.job_drives.models import JobDrive  # noqa: F401 — registers metadata
from app.modules.knowledge.models import Chunk, Document  # noqa: F401 — registers metadata
from app.modules.memory.models import Conversation, Message  # noqa: F401 — registers metadata
from app.modules.video.models import Video  # noqa: F401 — registers metadata

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, include_schemas=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
