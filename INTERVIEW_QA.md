# Interview Q&A Guide — Transaction Leaderboard System

Study these questions and answers. They represent the most likely follow-up questions
for a system design / backend engineering interview based on this project.

---

## 1. Why FastAPI?

> **Answer:**
> FastAPI gives me automatic request validation via Pydantic, async-ready request handling with Uvicorn,
> and auto-generated OpenAPI docs out of the box. Compared to Flask, it's much faster (benchmarks show
> 2–5x throughput) and the Pydantic integration means I get type-checked request/response models for free.
> The dependency injection system is also clean for things like database sessions and auth.

---

## 2. Why does transactionId need to be unique?

> **Answer:**
> `transactionId` is my idempotency key. It uniquely identifies a business-level operation.
> If a client retries a request (due to network timeout, etc.), I need to ensure the transaction
> is only processed once. The UNIQUE constraint at the database level guarantees this even under
> concurrent load — if two identical requests race, only one INSERT succeeds, the other gets an
> IntegrityError which I convert to HTTP 409. Without this constraint, a retry could double-charge
> a user or double-count a balance.

---

## 3. What is idempotency?

> **Answer:**
> Idempotency means that calling the same operation multiple times produces the same result as
> calling it once. In HTTP terms, `GET` is naturally idempotent. `POST` is not by default — but you
> can make it idempotent by using an idempotency key (like `transactionId`). The server uses the key
> to detect and short-circuit duplicate requests. This is critical in payment systems where network
> failures can cause clients to retry, and you must ensure you never process a payment twice.

---

## 4. What is a race condition?

> **Answer:**
> A race condition happens when two concurrent operations read the same shared state, compute a
> new value independently, and then both write — with one overwriting the other's result.
> In my system, two concurrent requests for the same user could both read `total_amount = 100`,
> both compute `100 + 100 = 200`, and both write 200 — resulting in a total of 200 when it should be 300.
> This is called a "lost update." I prevent it by using an atomic SQL UPDATE expression that the
> database evaluates under a row lock, eliminating the read-modify-write cycle entirely.

---

## 5. How does your ranking work?

> **Answer:**
> I fetch all user rows from the database ordered by `score DESC`. Score is stored pre-computed
> on each user row and updated atomically after every transaction. I attach sequential rank numbers
> in Python using `enumerate`. The score is a composite of three factors: total amount (×0.5),
> total transactions (×10), and active days (×5). This means ranking reflects volume, frequency,
> and consistency — not just raw dollar amount.

---

## 6. Why is your ranking fair?

> **Answer:**
> A pure amount-based ranking can be gamed by one large deposit. My composite score makes it
> harder to dominate by any single dimension:
> - `total_amount × 0.5` rewards volume but at reduced weight.
> - `total_transactions × 10` rewards users who transact often, even in small amounts.
> - `active_days × 5` rewards consistency over time — daily engagement beats a one-day burst.
> A user who makes consistent daily transactions over 30 days earns +150 points just from active_days,
> making them competitive against a single-transaction whale. It's multi-dimensional and harder to game.

---

## 7. How would you scale this?

> **Answer:**
> Several dimensions:
> 1. **Database** — Migrate to PostgreSQL. Add read replicas for GET /ranking and GET /summary.
> 2. **Rate limiting** — Replace in-memory limiter with Redis ZADD sliding window, which works across replicas.
> 3. **Ranking cache** — Cache GET /ranking in Redis with a 30-second TTL. Rankings don't need real-time accuracy.
> 4. **Horizontal scaling** — The stateless FastAPI app can run behind a load balancer with any number of replicas.
> 5. **Queue** — For very high write volume, put transactions in a message queue (Kafka/SQS) and process asynchronously.
> 6. **Sharding** — Shard the transactions table by user_id range if single-table size becomes a bottleneck.

---

## 8. Why SQLite?

> **Answer:**
> SQLite is zero-configuration, file-based, and built into Python. For local development and demos,
> it lets you get up and running instantly without a database server. It handles our concurrency needs
> because SQLAlchemy manages transactions and row-level locking works for our use case. The codebase is
> already structured to swap it out — the `DATABASE_URL` environment variable is the only change needed
> to point to PostgreSQL in production.

---

## 9. What would you use in production?

> **Answer:**
> - **Database**: PostgreSQL — better concurrent write performance, native JSON columns, and RANK() window functions.
> - **Rate limiting**: Redis with ZADD sliding window — works across all server replicas.
> - **Session management**: PgBouncer for connection pooling.
> - **Migrations**: Alembic — versioned schema migrations instead of `create_all()`.
> - **Auth**: JWT tokens validated per request via FastAPI's dependency injection.
> - **Observability**: Prometheus for metrics, Sentry for error tracking, structured JSON logging.
> - **Caching**: Redis for the /ranking endpoint with a 30-second TTL.
> - **Testing**: pytest + FastAPI's TestClient for full integration tests.

---

## 10. How does your rate limiting work?

> **Answer:**
> I use a sliding window algorithm. For each user, I maintain a deque of timestamps of recent requests.
> On each incoming request, I:
> 1. Remove timestamps older than 60 seconds from the front of the deque.
> 2. Check if the remaining count is >= 20 (the limit). If so, raise HTTP 429.
> 3. If allowed, append the current timestamp and proceed.
>
> This is O(1) amortised. The window "slides" with real time, so it's more accurate than a fixed window
> that could allow 40 requests at a window boundary (20 at the end of one window + 20 at the start of the next).
>
> **Limitation**: It's in-memory and process-local. With multiple server instances, each has its own counter.
> **Production fix**: Redis ZADD — store timestamps as a sorted set, use ZREMRANGEBYSCORE to evict old entries,
> ZCARD to count, all in an atomic Lua script or pipeline.

---
