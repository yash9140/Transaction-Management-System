"""
schemas.py — Pydantic request/response models.

Pydantic provides:
- Automatic type coercion and validation on request bodies
- Serialisation of ORM objects for responses
- Clear, self-documenting API contracts
"""

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class TransactionRequest(BaseModel):
    """Body accepted by POST /transaction."""

    transactionId: str = Field(..., description="Globally unique transaction identifier (idempotency key)")
    userId: str = Field(..., description="Identifier of the user performing the transaction")
    amount: float = Field(..., description="Monetary amount; must be strictly positive")

    @field_validator("transactionId", "userId")
    @classmethod
    def not_blank(cls, v: str) -> str:
        """Reject empty or whitespace-only strings."""
        if not v or not v.strip():
            raise ValueError("Field must not be blank")
        return v.strip()

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v: float) -> float:
        """
        Abuse prevention:
        - Negative amounts could be used to drain totals or game the score.
        - Zero amounts carry no economic meaning.
        Both are rejected here (first validation layer; services layer echoes this).
        """
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TransactionResponse(BaseModel):
    """Successful creation response for POST /transaction."""

    message: str
    transactionId: str
    userId: str
    amount: float


class SummaryResponse(BaseModel):
    """Response shape for GET /summary/{userId}."""

    userId: str
    totalTransactions: int
    totalAmount: float
    score: float


class RankEntry(BaseModel):
    """Single row in the ranking leaderboard."""

    rank: int
    userId: str
    score: float


class ErrorResponse(BaseModel):
    """Uniform error envelope returned for all 4xx / 5xx responses."""

    message: str
