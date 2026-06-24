"""
models.py — SQLAlchemy ORM models for Users and Transactions.

Design notes:
- transaction_id has a UNIQUE constraint at the database level.
  This is the last line of defence against duplicate processing — even if
  two concurrent requests slip past the application-level check, the DB will
  raise an IntegrityError for the second insert.
- user_id is also unique: one User row per logical user, updated in-place
  on every new transaction (upsert pattern).
- score is stored (denormalised) so that the ranking query is a simple
  ORDER BY without recalculating at read time.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint

from app.database import Base


class User(Base):
    """Aggregated per-user statistics, updated atomically on each transaction."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Business-level unique identifier supplied by the caller
    user_id = Column(String, unique=True, index=True, nullable=False)

    # Running totals — kept in sync inside a DB transaction with the
    # Transaction row insertion (atomic write)
    total_amount = Column(Float, default=0.0, nullable=False)
    total_transactions = Column(Integer, default=0, nullable=False)

    # Pre-computed composite score (see utils/scoring.py)
    score = Column(Float, default=0.0, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Transaction(Base):
    """Immutable ledger of individual transactions.

    The UNIQUE constraint on transaction_id is the database-level
    idempotency guard: if the application layer misses a duplicate (race),
    the database will raise an IntegrityError, which the service layer
    catches and converts to HTTP 409 Conflict.
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Caller-supplied idempotency key — must be globally unique
    transaction_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(String, index=True, nullable=False)

    amount = Column(Float, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("transaction_id", name="uq_transaction_id"),
    )

# Duplicate prevention enforced at DB level via UniqueConstraint on transaction_id.
