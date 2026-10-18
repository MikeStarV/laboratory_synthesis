from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .laboratory_syntheses_config import laboratory_syntheses_settings


class LaboratorySynthesesDatabaseModel(DeclarativeBase):
    pass


laboratory_syntheses_engine = create_async_engine(
    laboratory_syntheses_settings.database_url,
    echo=False,
)

laboratory_syntheses_session_maker = async_sessionmaker(
    bind=laboratory_syntheses_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_laboratory_syntheses_database_session(
) -> AsyncGenerator[AsyncSession, None]:
    async with laboratory_syntheses_session_maker() as session:
        yield session
