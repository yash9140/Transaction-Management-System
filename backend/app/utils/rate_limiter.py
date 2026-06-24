"""
rate_limiter.py — In-memory sliding-window rate limiter.

CURRENT IMPLEMENTATION
----------------------
Uses a per-user deque of timestamps.  On each request:
  1. Remove timestamps older than the window (60 seconds).
  2. If remaining count >= limit → reject with HTTP 429.
  3. Otherwise → append current timestamp and allow the request.

This is O(1) amortised per request (deque popleft is O(1)).

THREAD SAFETY
-------------
Python's GIL ensures that deque operations are atomic at the CPython level,
making this safe for multi-threaded WSGI/ASGI servers with a single process.

LIMITATIONS
-----------
- State is process-local: does NOT work across multiple server processes or
  container replicas.  Each process has its own counter, so a user can exceed
  the limit by hitting different replicas.
- State is lost on server restart.

PRODUCTION ALTERNATIVE — Redis
-------------------------------
Replace this module with a Redis-backed sliding window:

    import redis, time

    r = redis.Redis(...)

    def check_rate_limit(user_id: str, limit: int = 20, window: int = 60):
        key = f"rl:{user_id}"
        now = time.time()
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)  # evict old entries
        pipe.zadd(key, {str(now): now})              # add this request
        pipe.zcard(key)                              # count in window
        pipe.expire(key, window)                     # auto-cleanup TTL
        _, _, count, _ = pipe.execute()
        if count > limit:
            raise RateLimitExceeded(user_id, limit, window)

Benefits of Redis approach:
  ✓ Works across multiple processes/replicas
  ✓ Persisted across restarts (if Redis AOF/RDB enabled)
  ✓ Can be extended to IP-level or global limits
  ✓ Lua scripting makes the pipeline fully atomic
"""

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_LIMIT: int = 20        # maximum requests allowed in the window
_WINDOW: int = 60       # sliding window size in seconds


# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------
# Maps user_id → deque of Unix timestamps of recent requests
_request_log: Dict[str, Deque[float]] = defaultdict(deque)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_rate_limit(user_id: str) -> None:
    """
    Enforce the per-user sliding-window rate limit.

    Parameters
    ----------
    user_id : str
        The user identifier to throttle.

    Raises
    ------
    HTTPException(429)  if the user has exceeded _LIMIT requests in _WINDOW seconds.
    """
    now = time.monotonic()
    window_start = now - _WINDOW

    log = _request_log[user_id]

    # Evict timestamps outside the current window (oldest are at the left)
    while log and log[0] < window_start:
        log.popleft()

    if len(log) >= _LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "message": (
                    f"Rate limit exceeded. Maximum {_LIMIT} transaction requests "
                    f"per {_WINDOW} seconds per user."
                )
            },
        )

    # Record this request
    log.append(now)


def get_current_count(user_id: str) -> int:
    """Return the number of requests in the current window (for diagnostics)."""
    now = time.monotonic()
    window_start = now - _WINDOW
    log = _request_log[user_id]
    return sum(1 for ts in log if ts >= window_start)
