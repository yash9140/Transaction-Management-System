"""
database.py — SQLAlchemy engine, session factory, and Base declaration.

Uses SQLite for local development.
- check_same_thread=False is safe here because FastAPI uses async workers and
  SQLAlchemy sessions are scoped per-request via the dependency injector.
- In production, swap the DATABASE_URL for PostgreSQL and remove
  connect_args entirely.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# Connection URL
# ---------------------------------------------------------------------------
# Default: local SQLite file next to this package.
# Override in production via the DATABASE_URL environment variable.
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./leaderboard.db")

# SQLite-specific: allow the same connection to be shared across threads
# because FastAPI may hand the same connection to different coroutines within
# the same thread pool worker.  This flag is ONLY needed for SQLite.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    # Pool settings — fine-grained for production PostgreSQL; harmless for SQLite
    pool_pre_ping=True,       # verify connection health before using from pool
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # we manage commits explicitly for transactional safety
    autoflush=False,    # prevent premature flushes inside a transaction
)

# ---------------------------------------------------------------------------
# Declarative base (shared by all ORM models)
# ---------------------------------------------------------------------------
Base = declarative_base()


# ---------------------------------------------------------------------------
# FastAPI dependency — one session per HTTP request
# ---------------------------------------------------------------------------
def get_db():
    """
    Yields a SQLAlchemy session and ensures it is closed after the request,
    even if an exception is raised.  Use as:

        @router.get("/endpoint")
        def handler(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
