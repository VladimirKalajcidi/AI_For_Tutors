from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .models import Base
import config

# Create async engine and session
engine = create_async_engine(config.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    """Create all tables (if not exist)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
