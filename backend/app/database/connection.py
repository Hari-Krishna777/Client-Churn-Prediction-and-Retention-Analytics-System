import os
import logging
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# PostgreSQL is the production target.  SQLite is deliberately the local
# development default so a missing local PostgreSQL service never causes the
# API to start against an unexpected database or silently lose writes.
backend_dir = Path(__file__).resolve().parents[2]
default_db_file = (backend_dir / "churniq.db").as_posix()
raw_db_url = os.getenv("DATABASE_URL", f"sqlite:///{default_db_file}")

# Normalize postgresql:// to postgresql+psycopg2://
if raw_db_url.startswith("postgresql://"):
    DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    DATABASE_URL = raw_db_url


def create_app_engine(db_url: str):
    """Create the configured SQLAlchemy engine without changing its database.

    A connection failure must be visible to the application rather than being
    redirected to SQLite: doing the latter is a data-isolation and data-loss
    risk in a deployed service.  SQLite remains supported when selected
    explicitly (and is useful for local development and tests).
    """
    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False})
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800")),
    )


engine = create_app_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables in the database if they do not exist."""
    import app.database.models  # Ensure models are imported
    Base.metadata.create_all(bind=engine)
    if str(engine.url).startswith("sqlite"):
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE recommendations ADD COLUMN status VARCHAR(50) DEFAULT 'Pending'"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE recommendations ADD COLUMN notes TEXT"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255)"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE datasets ADD COLUMN deleted_at DATETIME"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE customers ADD COLUMN user_id VARCHAR(36)"))
                conn.commit()
            except Exception:
                pass
    logger.info("Database tables initialized successfully.")
