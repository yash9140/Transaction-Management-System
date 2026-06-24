# Transaction Leaderboard System

A production-quality full-stack application demonstrating **idempotent transaction processing**, **concurrent-safe atomic database updates**, **composite fair ranking**, and **per-user rate limiting**.

---

## 1. Project Overview

This system exposes three REST APIs:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/transaction` | Submit a financial transaction |
| `GET` | `/summary/{userId}` | Fetch aggregate stats for a user |
| `GET` | `/ranking` | Fetch the full leaderboard |

**Key engineering properties demonstrated:**
- **Idempotency** — submitting the same `transactionId` twice is safe and returns HTTP 409
- **Atomicity** — user totals are updated via a single SQL `UPDATE` expression, not a Python read-modify-write
- **Fair ranking** — multi-factor composite score instead of raw amount totals
- **Abuse prevention** — in-memory sliding-window rate limiter (20 req/min/user)

---

## 2. Architecture

```
Client (React + Axios)
        │  HTTP JSON
        ▼
FastAPI Application (main.py)
├── CORS Middleware
├── Exception Handlers (400 / 404 / 409 / 429 / 500)
├── Routers
│   ├── POST /transaction  →  transaction_service.process_transaction()
│   ├── GET  /summary/:id  →  DB query on users table
│   └── GET  /ranking      →  ranking_service.get_ranking()
├── Services
│   ├── transaction_service.py  (core business logic + concurrency comments)
│   └── ranking_service.py      (ordered query + rank numbering)
└── Utils
    ├── scoring.py      (composite score formula)
    ├── validators.py   (amount + blank-field guards)
    └── rate_limiter.py (in-memory sliding window)
        │
        ▼
SQLAlchemy ORM
        │
        ▼
SQLite (dev) / PostgreSQL (prod)
```

---

## 3. Setup Instructions

### Prerequisites
- Python 3.11+
- Node.js 18+

### Clone
```bash
git clone <repo-url>
cd Transaction-Leaderboard-System
```

---

## 4. Running the Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at **http://localhost:8000**

Interactive docs: **http://localhost:8000/docs**

---

## 5. Running the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend is now available at **http://localhost:5173**

> **Environment variable:** Create `frontend/.env` and set:
> ```
> VITE_BACKEND_URL=http://localhost:8000
> ```
> On Vercel, set this as an environment variable pointing to your deployed backend.

---

## 6. API Documentation

### POST /transaction

Submit a new financial transaction. Idempotent — safe to retry with the same `transactionId`.

**Request Body:**
```json
{
  "transactionId": "txn_abc_001",
  "userId": "user123",
  "amount": 150.00
}
```

**Responses:**

| Status | Meaning | Body |
|--------|---------|------|
| `201` | Created | `{ "message": "...", "transactionId": "...", "userId": "...", "amount": 150.0 }` |
| `400` | Validation error | `{ "message": "Amount must be greater than zero" }` |
| `409` | Duplicate transaction | `{ "message": "Duplicate transaction" }` |
| `429` | Rate limit exceeded | `{ "message": "Rate limit exceeded..." }` |

---

### GET /summary/{userId}

**Response (200):**
```json
{
  "userId": "user123",
  "totalTransactions": 12,
  "totalAmount": 5000.0,
  "score": 88.4
}
```

**Response (404):**
```json
{ "message": "User 'user123' not found" }
```

---

### GET /ranking

**Response (200):**
```json
[
  { "rank": 1, "userId": "userA", "score": 150.0 },
  { "rank": 2, "userId": "userB", "score": 95.5 }
]
```

---

## 7. Database Design

### `users` table

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | INTEGER | PK, auto | Internal surrogate key |
| `user_id` | VARCHAR | UNIQUE, NOT NULL | Business identifier |
| `total_amount` | FLOAT | NOT NULL | Running sum of amounts |
| `total_transactions` | INTEGER | NOT NULL | Running count |
| `score` | FLOAT | NOT NULL | Pre-computed composite score |
| `created_at` | DATETIME | NOT NULL | First-seen timestamp |

### `transactions` table

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | INTEGER | PK, auto | Internal surrogate key |
| `transaction_id` | VARCHAR | **UNIQUE**, NOT NULL | Caller-supplied idempotency key |
| `user_id` | VARCHAR | NOT NULL, INDEX | Reference to business user |
| `amount` | FLOAT | NOT NULL | Transaction value |
| `created_at` | DATETIME | NOT NULL | Transaction timestamp |

> The `UNIQUE` constraint on `transaction_id` is the **database-level idempotency guard** — the last line of defence against duplicates.

---

## 8. Ranking Formula

```
score = (total_amount × 0.5)
      + (total_transactions × 10)
      + (active_days × 5)

active_days = COUNT(DISTINCT DATE(created_at)) per user
```

### Why this is fairer

| Factor | Weight | Rationale |
|--------|--------|-----------|
| `total_amount × 0.5` | Economic volume | Rewards high-value users, but at half weight to avoid single-whale domination |
| `total_transactions × 10` | Activity frequency | A user with 10 small transactions (+100) beats a single large deposit (+50 on a $100 txn) |
| `active_days × 5` | Temporal consistency | Rewards sustained daily engagement, not burst activity |

**Example:**
- User A: $1000, 5 txns, 3 days → score = 500 + 50 + 15 = **565**
- User B: $200, 20 txns, 10 days → score = 100 + 200 + 50 = **350**
- User C: $0, 0 txns, 0 days → score = **0**

---

## 9. Duplicate Prevention Strategy

**Two layers:**

1. **Application layer** (`transaction_service.py`, Step 3):
   - `SELECT` from `transactions` where `transaction_id = ?` before any write.
   - Fast rejection for obvious duplicates, avoiding unnecessary DB writes.

2. **Database layer** (`models.py`, `UniqueConstraint`):
   - `UNIQUE` constraint on `transactions.transaction_id`.
   - If two concurrent requests pass the application check simultaneously, only one `INSERT` succeeds — the other raises `IntegrityError` → HTTP 409.

This two-layer approach is battle-tested and handles both normal duplicates and race-condition duplicates.

---

## 10. Concurrency Handling Strategy

**Problem — Lost Update Race Condition:**
```
Thread A reads total_amount = 100
Thread B reads total_amount = 100  ← stale
Thread A writes total_amount = 200 (100+100)
Thread B writes total_amount = 200 (100+100) ← LOST update!
```

**Solution — Atomic SQL UPDATE:**
```sql
UPDATE users
SET total_amount = total_amount + :delta,
    total_transactions = total_transactions + 1
WHERE user_id = :uid
```
The database evaluates the expression under a **row-level lock**, preventing interleaving. No Python read-modify-write cycle is involved.

**ACID Guarantee:**
Both `INSERT INTO transactions` and `UPDATE users` run inside a **single database transaction**. If either fails, the entire unit is rolled back.

---

## 11. Abuse Prevention Strategy

| Mechanism | Implementation | Guards Against |
|-----------|---------------|----------------|
| Negative amounts | Pydantic validator + service validator | Balance manipulation, score gaming |
| Zero amounts | Same validators | No-op spam |
| Duplicate prevention | UNIQUE constraint + app-layer check | Double processing, duplicate billing |
| Rate limiting | In-memory sliding window (20 req/60s per user) | Brute-force spam |

---

## 12. Production Improvements

| Area | Current | Production |
|------|---------|-----------|
| Database | SQLite | PostgreSQL with connection pooling (PgBouncer) |
| Rate limiting | In-memory (single process) | Redis ZADD sliding window (cluster-safe) |
| Score calculation | On write | Same (denormalised storage) or background job |
| Migrations | `create_all()` | Alembic versioned migrations |
| Auth | None | JWT / OAuth2 |
| Observability | None | Prometheus metrics + Sentry error tracking |
| Caching | None | Redis for `/ranking` (TTL 30s) |
| Tests | None | pytest + httpx TestClient |

---

## 13. Deployment Instructions

### Backend — Render

1. Push code to GitHub.
2. Create a new **Web Service** on [render.com](https://render.com).
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Set environment variable `DATABASE_URL` if using PostgreSQL.

### Frontend — Vercel

1. Push code to GitHub.
2. Import the `frontend/` directory on [vercel.com](https://vercel.com).
3. Set framework preset to **Vite**.
4. Set environment variable:
   ```
   VITE_BACKEND_URL=https://your-backend.onrender.com
   ```
5. Deploy.
