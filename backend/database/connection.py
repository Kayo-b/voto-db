"""
Database connection and session management for Voto-DB.
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import os
from pathlib import Path
from .model import Base

# Database configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'sqlite:///./tmp/local_run.db'
)

url = make_url(DATABASE_URL)
engine_kwargs = {"echo": False}  # Set to True for SQL debugging

if url.drivername.startswith("sqlite"):
    # Ensure SQLite file directory exists and allow multi-thread access from FastAPI workers.
    if url.database and url.database not in (":memory:", ""):
        db_path = Path(url.database)
        if not db_path.is_absolute():
            db_path = (Path.cwd() / db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Keep explicit pooling for client/server databases such as PostgreSQL.
    engine_kwargs.update(
        {
            "poolclass": QueuePool,
            "pool_size": 20,
            "max_overflow": 0,
        }
    )

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_database():
    """
    Dependency to get database session.
    Use with FastAPI's Depends() for automatic session management.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables.
    Call this function to initialize the database schema.
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables.
    Use with caution - this will delete all data!
    """
    Base.metadata.drop_all(bind=engine)


# Database health check
def check_database_connection() -> bool:
    """
    Check if database connection is healthy.
    Returns True if connection is successful, False otherwise.
    """
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
