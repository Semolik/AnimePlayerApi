import contextlib
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator
from src.core.config import settings
from src.db.base import Base
from src.models.users import *
from src.models.parsers import *

uri = settings.SQLALCHEMY_DATABASE_URI
engine = create_async_engine("postgresql+asyncpg://postgres:postgres@database/async_sqlalchemy")
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

get_async_session_context = contextlib.asynccontextmanager(get_async_session)
