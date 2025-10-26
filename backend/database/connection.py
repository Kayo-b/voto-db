"""
Database connection and configuration for VotoDB
"""
import os
from typing import Optional
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging

from .models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration management"""
    
    def __init__(self):
        self.database_url = self._get_database_url()
        self.engine = None
        self.session_factory = None
        
    def _get_database_url(self) -> str:
        """Build database URL from environment variables"""
        # Try to get from DATABASE_URL first (common in deployment)
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # Handle postgres:// vs postgresql:// (some services use postgres://)
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            return database_url
        
        # Build from individual components
        user = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', 'postgres')
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'votodb')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def create_engine(self) -> Engine:
        """Create SQLAlchemy engine with optimized settings"""
        if self.engine is None:
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=os.getenv('DB_ECHO', 'false').lower() == 'true'
            )
            
            # Add connection event listeners
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                if 'postgresql' in str(self.engine.url):
                    with dbapi_connection.cursor() as cursor:
                        cursor.execute("SET timezone='UTC'")
        
        return self.engine
    
    def create_session_factory(self) -> sessionmaker:
        """Create session factory"""
        if self.session_factory is None:
            engine = self.create_engine()
            self.session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False
            )
        return self.session_factory
    
    def create_all_tables(self):
        """Create all database tables"""
        engine = self.create_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    
    def drop_all_tables(self):
        """Drop all database tables (use with caution!)"""
        engine = self.create_engine()
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")

# Global database configuration instance
db_config = DatabaseConfig()

def get_session() -> Session:
    """Get a new database session"""
    session_factory = db_config.create_session_factory()
    return session_factory()

@contextmanager
def get_db_session():
    """Context manager for database sessions with automatic cleanup"""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()

def init_database():
    """Initialize database - create tables and setup"""
    try:
        db_config.create_all_tables()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def test_connection() -> bool:
    """Test database connection"""
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

class DatabaseService:
    """Service class for common database operations"""
    
    @staticmethod
    def get_or_create(session: Session, model_class, **kwargs):
        """Get existing record or create new one"""
        instance = session.query(model_class).filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            instance = model_class(**kwargs)
            session.add(instance)
            return instance, True
    
    @staticmethod
    def bulk_insert_or_update(session: Session, model_class, records: list, update_fields: list = None):
        """Bulk insert or update records efficiently"""
        if not records:
            return
            
        try:
            # Use PostgreSQL's ON CONFLICT for upserts when possible
            for record in records:
                existing = session.query(model_class).filter_by(id=record.get('id')).first()
                if existing:
                    # Update existing record
                    if update_fields:
                        for field in update_fields:
                            if field in record:
                                setattr(existing, field, record[field])
                    else:
                        # Update all fields except id
                        for key, value in record.items():
                            if key != 'id':
                                setattr(existing, key, value)
                else:
                    # Create new record
                    new_record = model_class(**record)
                    session.add(new_record)
            
            session.commit()
            logger.info(f"Bulk operation completed for {len(records)} {model_class.__name__} records")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Bulk operation failed for {model_class.__name__}: {e}")
            raise
    
    @staticmethod
    def cleanup_old_records(session: Session, model_class, days_old: int = 30):
        """Clean up old records based on created_at field"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        try:
            deleted_count = session.query(model_class).filter(
                model_class.criado_em < cutoff_date
            ).delete()
            session.commit()
            logger.info(f"Cleaned up {deleted_count} old {model_class.__name__} records")
            return deleted_count
        except Exception as e:
            session.rollback()
            logger.error(f"Cleanup failed for {model_class.__name__}: {e}")
            raise