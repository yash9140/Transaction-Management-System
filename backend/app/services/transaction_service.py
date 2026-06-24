"""
transaction_service.py — Core business logic for processing transactions.

CONCURRENCY SAFETY DESIGN
==========================

PROBLEM — Race Condition
------------------------
Imagine two simultaneous requests for the same user arrive at nearly the
same time:

  Thread A reads user.total_amount = 100
  Thread B reads user.total_amount = 100   ← same stale value
  Thread A writes user.total_amount = 200  (100 + 100)
  Thread B writes user.total_amount = 200  (100 + 100)  ← LOST UPDATE

Both threads committed 100 each but the final total is 200, not 300.
This is the classic "read-modify-write" race condition (also called a
"lost update" or "phantom write").

SOLUTION — Atomic SQL UPDATE
-----------------------------
Instead of:
  1. SELECT total_amount
  2. Python: total_amount + new_amount
  3. UPDATE total_amount = <python result>

We issue a single SQL statement:
  UPDATE users SET total_amount = total_amount + :delta WHERE user_id = :uid

The database evaluates `total_amount + :delta` atomically under row-level
locking, so no two transactions can interleave their reads and writes.

DUPLICATE PREVENTION — Two layers
----------------------------------
Layer 1 (application): SELECT transaction WHERE id = txn_id BEFORE insert.
  Fast path that avoids unnecessary DB writes.

Layer 2 (database): UNIQUE constraint on transactions.transaction_id.
  Even if two concurrent requests both pass Layer 1 simultaneously, only
  one INSERT will succeed; the other raises IntegrityError → HTTP 409.

CONSISTENCY GUARANTEE
---------------------
Both the Transaction INSERT and the User UPDATE happen inside a single
database transaction (`db.begin()` / `db.commit()`).  If either operation
fails the entire unit is rolled back, leaving the database in a consistent
state.  This satisfies the ACID Atomicity and Consistency properties.
"""

from datetime import datetime, timezone

from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Transaction, User
from app.utils.rate_limiter import check_rate_limit
from app.utils.scoring import compute_score
from app.utils.validators import AmountValidationError, validate_amount


# ---------------------------------------------------------------------------
# Custom exceptions (caught by the router and mapped to HTTP status codes)
# ---------------------------------------------------------------------------

class DuplicateTransactionError(Exception):
    """Raised when transaction_id already exists in the database."""

    def __init__(self, transaction_id: str):
        self.transaction_id = transaction_id
        super().__init__(f"Duplicate transaction: {transaction_id}")


class InvalidAmountError(Exception):
    """Raised when the amount fails business-rule validation."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# Helper — count unique active days for a user
# ---------------------------------------------------------------------------

def _get_active_days(db: Session, user_id: str) -> int:
    """
    Count the number of unique calendar dates on which this user has made
    at least one transaction.

    Uses SQLite's DATE() function to truncate timestamps to day granularity.
    On PostgreSQL, use DATE_TRUNC('day', created_at) instead.

    This query is efficient because transactions.user_id is indexed.
    In very high-volume systems, materialise active_days in the users table
    and increment it only when the date changes (compare MAX(date) vs today).
    """
    result = db.execute(
        text(
            "SELECT COUNT(DISTINCT DATE(created_at)) "
            "FROM transactions "
            "WHERE user_id = :uid"
        ),
        {"uid": user_id},
    ).scalar()
    return result or 0


# ---------------------------------------------------------------------------
# Main service function
# ---------------------------------------------------------------------------

def process_transaction(
    *,
    transaction_id: str,
    user_id: str,
    amount: float,
    db: Session,
) -> dict:
    """
    Process a single financial transaction atomically.

    Steps
    -----
    1. Rate-limit check  (in-memory sliding window, per user)
    2. Amount validation  (business rules; Pydantic already ran schema rules)
    3. Duplicate check — Layer 1  (fast SELECT before any write)
    4. Open a database transaction
    5. Insert Transaction row
    6. Upsert User row with atomic SQL increments
    7. Recalculate and persist composite score
    8. Commit
    9. Return summary dict for the response

    Parameters
    ----------
    transaction_id : Caller-supplied idempotency key.
    user_id        : Identifier of the transacting user.
    amount         : Positive monetary amount.
    db             : Active SQLAlchemy session (injected by FastAPI).

    Returns
    -------
    dict with keys: transactionId, userId, amount, message.

    Raises
    ------
    HTTPException(429)        — rate limit exceeded (from rate_limiter).
    DuplicateTransactionError — transaction_id already exists.
    InvalidAmountError        — amount <= 0 or non-finite.
    """

    # ------------------------------------------------------------------
    # STEP 1: Rate limiting
    # ------------------------------------------------------------------
    # check_rate_limit raises HTTPException(429) if the user has exceeded
    # the allowed request rate.  We do this before any DB I/O to minimise
    # load under an abuse scenario.
    check_rate_limit(user_id)

    # ------------------------------------------------------------------
    # STEP 2: Amount validation (service layer guard)
    # ------------------------------------------------------------------
    try:
        validate_amount(amount)
    except AmountValidationError as exc:
        raise InvalidAmountError(str(exc)) from exc

    # ------------------------------------------------------------------
    # STEP 3: Duplicate check — Layer 1 (application level)
    # ------------------------------------------------------------------
    # A quick SELECT avoids wasting a write transaction on obvious duplicates.
    # Note: this check alone is NOT sufficient under concurrent load; the
    # UNIQUE constraint (Layer 2) handles the concurrent case.
    existing = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id)
        .first()
    )
    if existing:
        raise DuplicateTransactionError(transaction_id)

    # ------------------------------------------------------------------
    # STEP 4–8: Atomic write inside a single DB transaction
    # ------------------------------------------------------------------
    try:
        # --- Insert the immutable transaction record -------------------
        txn = Transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            amount=amount,
            created_at=datetime.now(timezone.utc),
        )
        db.add(txn)
        db.flush()  # sends INSERT to DB; raises IntegrityError on duplicate
                    # without committing yet — so we can roll back cleanly

        # --- Upsert the User row with atomic increments ---------------
        # ATOMIC UPDATE: the entire expression `total_amount + :delta` is
        # evaluated by the database engine under a row lock.  No Python
        # read-modify-write cycle is involved, eliminating the race.
        user = db.query(User).filter(User.user_id == user_id).first()

        if user is None:
            # First transaction for this user — create the aggregate row
            user = User(
                user_id=user_id,
                total_amount=amount,
                total_transactions=1,
                score=0.0,
                created_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.flush()
        else:
            # ATOMIC SQL UPDATE — avoids read-modify-write race
            db.execute(
                text(
                    "UPDATE users "
                    "SET total_amount = total_amount + :delta, "
                    "    total_transactions = total_transactions + 1 "
                    "WHERE user_id = :uid"
                ),
                {"delta": amount, "uid": user_id},
            )
            # Refresh the ORM object so we have current totals for scoring
            db.refresh(user)

        # --- Recalculate composite score ------------------------------
        # active_days is derived from the transactions table (already updated
        # by the flush above, so today's transaction counts).
        active_days = _get_active_days(db, user_id)
        new_score = compute_score(
            total_amount=user.total_amount,
            total_transactions=user.total_transactions,
            active_days=active_days,
        )
        db.execute(
            text("UPDATE users SET score = :score WHERE user_id = :uid"),
            {"score": new_score, "uid": user_id},
        )

        # --- Commit — makes all changes visible atomically ------------
        db.commit()

    except IntegrityError:
        # Duplicate prevention — Layer 2:
        # Two concurrent requests passed the application-level check (Step 3)
        # at the same instant.  The DB UNIQUE constraint rejected one of them.
        db.rollback()
        raise DuplicateTransactionError(transaction_id)

    except Exception:
        # Any other unexpected error → rollback to keep DB consistent
        db.rollback()
        raise

    return {
        "message": "Transaction processed successfully",
        "transactionId": transaction_id,
        "userId": user_id,
        "amount": amount,
    }
