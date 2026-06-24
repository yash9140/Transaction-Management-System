"""
routers/ranking.py — HTTP router for GET /ranking.

Returns all users sorted by composite score descending.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RankEntry
from app.services.ranking_service import get_ranking

router = APIRouter(tags=["Ranking"])


@router.get(
    "/ranking",
    response_model=List[RankEntry],
    summary="Get leaderboard",
    description=(
        "Returns all users ranked by composite score (descending). "
        "Score = (total_amount × 0.5) + (total_transactions × 10) + (active_days × 5)."
    ),
)
def ranking(
    db: Session = Depends(get_db),
):
    """
    GET /ranking

    Delegates to ranking_service.get_ranking() which queries users ordered
    by score DESC and attaches sequential rank numbers.
    """
    return get_ranking(db)
