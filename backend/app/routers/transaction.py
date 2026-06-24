"""
routers/transaction.py — HTTP router for POST /transaction.

Responsibilities:
- Parse and validate the request body (Pydantic does this automatically).
- Delegate business logic to transaction_service.process_transaction().
- Map service-layer exceptions to correct HTTP status codes.
- Return a structured JSON response.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ErrorResponse, TransactionRequest, TransactionResponse
from app.services.transaction_service import (
    DuplicateTransactionError,
    InvalidAmountError,
    process_transaction,
)

router = APIRouter(tags=["Transactions"])


@router.post(
    "/transaction",
    response_model=TransactionResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Duplicate transaction"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
    summary="Submit a new transaction",
    description=(
        "Idempotent transaction submission. "
        "Submitting the same transactionId twice returns HTTP 409 Conflict "
        "without double-processing."
    ),
)
def create_transaction(
    payload: TransactionRequest,
    db: Session = Depends(get_db),
):
    """
    POST /transaction

    Accepts a transaction payload, validates it, prevents duplicates,
    and atomically updates the user's aggregated statistics.
    """
    try:
        result = process_transaction(
            transaction_id=payload.transactionId,
            user_id=payload.userId,
            amount=payload.amount,
            db=db,
        )
        return result

    except DuplicateTransactionError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": "Duplicate transaction"},
        ) from exc

    except InvalidAmountError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": exc.message},
        ) from exc
