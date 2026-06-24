"""
scoring.py — Composite score formula for the fair ranking system.

WHY A COMPOSITE SCORE?
----------------------
Ranking purely by total_amount is easy to game:
  - A single whale deposit tops the leaderboard regardless of engagement.
  - A user with consistent daily activity gets no credit for reliability.

Our formula rewards three orthogonal dimensions of behaviour:

  score = (total_amount * 0.5)        ← volume / economic weight
        + (total_transactions * 10)   ← activity frequency
        + (active_days * 5)           ← temporal consistency / engagement

  active_days = number of unique calendar dates on which the user transacted.

FACTOR BREAKDOWN
----------------
1. total_amount * 0.5
   Rewards high-value users but at half-weight so a single large transaction
   doesn't completely dominate the score.

2. total_transactions * 10
   Rewards repeated engagement. A user who submits 10 small transactions
   earns +100 points — more than a 50-unit single deposit (+25).
   This makes it harder to game with one big transaction.

3. active_days * 5
   Rewards consistency over time. A user active 30 days earns +150 points,
   favouring sustained engagement over burst activity.

EXAMPLE
-------
User A: total_amount=1000, total_transactions=5,  active_days=3
        score = 500 + 50 + 15 = 565

User B: total_amount=200,  total_transactions=20, active_days=10
        score = 100 + 200 + 50 = 350

User C: total_amount=500,  total_transactions=15, active_days=7
        score = 250 + 150 + 35 = 435

User A wins on volume, but B and C get significant credit for engagement.

FUTURE IMPROVEMENTS
-------------------
- Recency weighting: transactions in the last 7 days count double.
- Normalisation: min-max scale each factor to prevent unit-scale dominance.
- Configurable weights: expose via environment variables or admin API.
"""


def compute_score(
    total_amount: float,
    total_transactions: int,
    active_days: int,
) -> float:
    """
    Calculate the composite ranking score for a user.

    Parameters
    ----------
    total_amount:        Sum of all transaction amounts (float).
    total_transactions:  Count of all accepted transactions (int).
    active_days:         Number of unique calendar days with at least one
                         transaction (int).

    Returns
    -------
    float — composite score, rounded to 2 decimal places.
    """
    score = (
        (total_amount * 0.5)
        + (total_transactions * 10)
        + (active_days * 5)
    )
    return round(score, 2)
