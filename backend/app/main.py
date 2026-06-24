"""
main.py — FastAPI application factory.

Responsibilities:
- Create the FastAPI app with metadata.
- Configure CORS (allow all origins for dev; restrict in production).
- Register global exception handlers for common error types.
- Include all API routers.
- Create database tables on startup (simple alternative to Alembic migrations
  for development; use Alembic for production schema management).
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.database import Base, engine
from app.routers import ranking, summary, transaction

# ---------------------------------------------------------------------------
# Create all tables
# ---------------------------------------------------------------------------
# In production, replace this with Alembic migrations:
#   alembic upgrade head
# create_all() is idempotent — safe to call on every startup during dev.
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Transaction Leaderboard System",
    description=(
        "A production-quality API demonstrating: idempotent transaction "
        "processing, concurrent-safe atomic DB updates, composite fair ranking, "
        "and per-user rate limiting."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# Allow all origins during development.
# In production, replace ["*"] with your specific frontend domain(s):
#   allow_origins=["https://your-app.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    """Convert Pydantic validation errors to HTTP 400 with a clean message."""
    errors = exc.errors()
    messages = [f"{e['loc'][-1]}: {e['msg']}" for e in errors]
    return JSONResponse(
        status_code=400,
        content={"message": "; ".join(messages)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected server errors — returns HTTP 500."""
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(transaction.router)
app.include_router(summary.router)
app.include_router(ranking.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"], summary="Health check endpoint")
def health():
    """Returns 200 OK — used by load balancers and deployment platforms."""
    return {"status": "ok", "service": "transaction-leaderboard"}
