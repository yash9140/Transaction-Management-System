# VIDEO SCRIPT — Transaction Leaderboard System
## 3–5 Minute Walkthrough

---

**[INTRO — 0:00–0:20]**

"Hey everyone! Today I'm going to walk you through a project I built called the Transaction Leaderboard System.
It's a full-stack application built with FastAPI on the backend and React on the frontend.
The goal was to go beyond just making something that works — I wanted to show real production concerns like
idempotency, concurrency safety, fair ranking, and abuse prevention.
Let me give you a quick tour."

---

**[PROJECT OVERVIEW — 0:20–0:50]**

"So the system has three main APIs.

POST /transaction — you submit a transaction with a user ID, a transaction ID, and an amount.

GET /summary/{userId} — returns that user's total amount, total transactions, and their score.

And GET /ranking — returns the full leaderboard sorted by score.

On the frontend, there are three panels matching exactly these three operations.
I built it with React and Axios, and it communicates with the backend via JSON."

---

**[DATABASE SCHEMA — 0:50–1:25]**

"Let me talk about the database design.

I have two tables.

The transactions table stores every single transaction — it has an id, a transaction_id, user_id, amount, and created_at.
The most important thing here is that transaction_id has a UNIQUE constraint at the database level.
This is my safety net against duplicate transactions.

The users table stores aggregated data — total_amount, total_transactions, and score.
These are kept in sync atomically every time a transaction comes in.
The score is stored pre-computed so the ranking query is just a fast ORDER BY."

---

**[DUPLICATE PREVENTION — 1:25–2:00]**

"Okay so let me explain how duplicates are prevented.

I have two layers.

Layer one is the application layer — when a transaction comes in, before I do any writes,
I check if that transaction_id already exists. If it does, I return a 409 Conflict immediately.

But here's the thing — layer one alone isn't enough. If two identical requests arrive at the exact
same millisecond, both might pass the application check before either has finished writing.
That's where layer two comes in.

Layer two is the database UNIQUE constraint. Even if both requests slip past the app check,
only one INSERT will succeed. The other gets an IntegrityError from the database,
which I catch and convert to a 409 response. Bulletproof."

---

**[CONCURRENCY HANDLING — 2:00–2:45]**

"Now let me talk about concurrency — this is where it gets interesting.

Imagine two concurrent requests for the same user come in at the same time.
If I do this naively — read the total, add the new amount in Python, then write it back —
I get what's called a lost update race condition.

Thread A reads total = 100. Thread B reads total = 100.
Thread A writes 200. Thread B also writes 200.
But we processed two transactions of 100 each, so the correct total should be 300. We've lost data.

My solution is to use an atomic SQL UPDATE:

UPDATE users SET total_amount = total_amount + [delta] WHERE user_id = [id]

The database evaluates that expression under a row lock.
No two transactions can interleave. The increment is atomic.

And both the transaction insert and the user update happen inside a single database transaction —
so if anything fails, both changes are rolled back. ACID atomicity guaranteed."

---

**[RANKING LOGIC — 2:45–3:20]**

"Now the ranking — I'm really proud of this part.

A lot of systems just rank users by total amount, which is easy to game.
One whale deposit and you're at the top, regardless of how engaged you are.

I use a composite score formula:

score = total_amount times 0.5
      plus total_transactions times 10
      plus active_days times 5

Active days is the number of unique calendar dates you've made at least one transaction.

This rewards three different behaviours.
Volume — how much money you move.
Frequency — how often you transact.
Consistency — how many different days you show up.

A user who makes consistent daily small transactions can outrank someone with one huge deposit.
Much harder to game. Much fairer."

---

**[ABUSE PREVENTION — 3:20–3:50]**

"For abuse prevention, I have a few mechanisms.

First, all amounts are validated — negative amounts and zero amounts are rejected with a 400 error.
These are simple but important — negative amounts could be used to manipulate scores.

Second, the duplicate prevention I already covered.

Third, I have rate limiting. Each user is allowed a maximum of 20 transaction requests per minute.
I implemented a sliding window limiter using an in-memory deque.
It's process-local, which is fine for a single server. For production across multiple servers,
I would switch to a Redis-backed implementation using ZADD and a sliding time window."

---

**[TRADEOFFS — 3:50–4:20]**

"Let me quickly mention the tradeoffs I made.

I chose SQLite for simplicity in development — zero configuration, file-based.
In production, I'd swap to PostgreSQL, which handles concurrent writes much better natively
and supports the RANK() window function for server-side ranking.

The rate limiter is in-memory — it won't work across multiple server instances.
Redis is the production answer there.

The score is denormalised — stored in the users table and recalculated on every write.
This is a read-heavy optimisation. For very high write throughput, you could move score
calculation to a background job running every few seconds."

---

**[OUTRO — 4:20–4:30]**

"That's the system! FastAPI backend, SQLite database, React frontend.
Idempotent, concurrent-safe, fair ranking, and abuse-resistant.
Thanks for watching!"

---
