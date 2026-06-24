"""
ranking_service.py — Fetch and rank all users by composite score.

Query strategy:
- Pull all User rows ordered by score DESC from the database.
- Attach sequential rank numbers in Python (1-based).
- Return a list of dicts ready for the RankEntry response schema.

Why not rank in SQL?
- SQLite < 3.25 does not support the RANK() window function.  For
  portability (SQLite local + PostgreSQL prod) we rank in Python.
- With PostgreSQL in production, prefer:
    SELECT user_id, score,
           RANK() OVER (ORDER BY score DESC) AS rank
    FROM users;
  This pushes the work into the DB and is efficient at scale.

Scalability note:
- For millions of users, paginate: GET /ranking?limit=100&offset=0
  and use a cursor-based approach for stable pages.
- Alternatively, pre-compute rankings in a background job and cache in Redis.
"""

from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.models import User


def get_ranking(db: Session) -> List[Dict[str, Any]]:
    """
    Return all users ranked by score descending.

    Parameters
    ----------
    db : Active SQLAlchemy session.

    Returns
    -------
    List of dicts: [{"rank": int, "userId": str, "score": float}, ...]
    Sorted descending by score; ties share the same position in list order
    (sequential ranks — no gap/dense handling needed at this scale).
    """
    users: List[User] = (
        db.query(User)
        .order_by(User.score.desc())
        .all()
    )

    ranking = []
    for position, user in enumerate(users, start=1):
        ranking.append({
            "rank": position,
            "userId": user.user_id,
            "score": user.score,
        })

    return ranking

# Refactored: ranking logic fully isolated from router layer.
