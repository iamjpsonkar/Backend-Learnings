"""
api/app/db.py — SQLite database connection and session management
"""

import os
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.settings import settings

log = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    pass


def get_db_path() -> str:
    return settings.db_path


def get_engine():
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db_url = f"sqlite+aiosqlite:///{db_path}"
    log.debug("creating_db_engine", db_url=db_url)
    return create_async_engine(
        db_url,
        echo=settings.log_level.upper() == "DEBUG",
        connect_args={"check_same_thread": False},
    )


engine = get_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Create all tables if they don't exist."""
    log.info("initializing_database", db_path=get_db_path())
    # Import models to register them with Base
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database_tables_created")


async def get_db():
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
