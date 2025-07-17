import logging
import time
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Import logging configuration
from tripbot.config.logging_config import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///tripbot.db"

# Configure SQLAlchemy logging
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # We'll handle logging ourselves
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    pool_recycle=3600
)

SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# Configure SQL query logging
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, params, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    logger.debug("Query: %s", statement)
    if params:
        logger.debug("Parameters: %s", params)

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, params, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    logger.debug("Query complete in %fms", total * 1000)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with SessionLocal() as db:
        yield db
