"""
routers/summary.py — HTTP router for GET /summary/{userId}.

Returns aggregated statistics for a single user.
Returns HTTP 404 if the user has never made a transaction.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import ErrorResponse, SummaryResponse

router = APIRouter(tags=["Summary"])


@router.get(
    "/summary/{userId}",
    response_model=SummaryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
    },
    summary="Get user transaction summary",
    description="Returns total transactions, total amount, and composite score for a user.",
)
def get_summary(
    userId: str,
    db: Session = Depends(get_db),
):
    """
    GET /summary/{userId}

    Looks up the User aggregate row by user_id and returns the summary.
    The score is stored pre-computed; no recalculation is needed at read time.
    """
    user: User | None = (
        db.query(User).filter(User.user_id == userId).first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail={"message": f"User '{userId}' not found"},
        )

    return SummaryResponse(
        userId=user.user_id,
        totalTransactions=user.total_transactions,
        totalAmount=user.total_amount,
        score=user.score,
    )
