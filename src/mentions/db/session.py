"""Database session management for SQLite."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

# Import models to register them with SQLModel metadata
from mentions.models.database import Mention, TrackedKeyword  # noqa: F401

# Database file path - stored in project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATABASE_URL = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'open_mentions.db'}"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

# Create async session maker
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    """
    Get an async database session.

    Yields:
        AsyncSession: Database session.
    """
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    """
    Initialize the database by creating all tables.

    This should be called on application startup.
    """
    from loguru import logger

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database tables initialized successfully")
