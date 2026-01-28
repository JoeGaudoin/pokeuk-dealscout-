from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import Optional

_engine = None
_session_maker = None


class Base(DeclarativeBase):
    pass


def get_engine():
    """Lazily create database engine."""
    global _engine
    if _engine is None:
        from .config import get_settings
        settings = get_settings()
        _engine = create_async_engine(
            settings.async_database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_session_maker():
    """Lazily create session maker."""
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_maker


# For backwards compatibility
def AsyncSessionLocal():
    return get_session_maker()


async def get_db() -> AsyncSession:
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
