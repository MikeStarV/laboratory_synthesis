
import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config


PROJECT_DIRECTORY = Path(__file__).resolve().parents[2]

if str(PROJECT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIRECTORY))


from laboratory_syntheses.laboratory_syntheses_config import (
    laboratory_syntheses_settings,
)
from laboratory_syntheses.laboratory_syntheses_database import (
    LaboratorySynthesesDatabaseModel,
)
from laboratory_syntheses import laboratory_syntheses_database_models


alembic_config = context.config

alembic_config.set_main_option(
    "sqlalchemy.url",
    laboratory_syntheses_settings.database_url,
)

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = LaboratorySynthesesDatabaseModel.metadata


def run_migrations_offline() -> None:
    database_url = alembic_config.get_main_option("sqlalchemy.url")

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_with_connection(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        alembic_config.get_section(
            alembic_config.config_ini_section,
            {},
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(run_migrations_with_connection)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
