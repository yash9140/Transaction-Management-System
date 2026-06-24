/**
 * api.js — Axios instance pre-configured for the backend.
 *
 * BACKEND_URL is set via the VITE_BACKEND_URL environment variable.
 * For local development this defaults to http://localhost:8000.
 * On Vercel, set VITE_BACKEND_URL to your Render/Railway backend URL.
 */

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

// ---------------------------------------------------------------------------
// Transactions
// ---------------------------------------------------------------------------

/**
 * Submit a new transaction.
 * @param {string} transactionId - Unique idempotency key
 * @param {string} userId        - User identifier
 * @param {number} amount        - Positive monetary amount
 */
export const submitTransaction = (transactionId, userId, amount) =>
  api.post('/transaction', { transactionId, userId, amount: parseFloat(amount) })

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

/**
 * Get aggregated statistics for a user.
 * @param {string} userId
 */
export const getUserSummary = (userId) => api.get(`/summary/${userId}`)

// ---------------------------------------------------------------------------
// Ranking
// ---------------------------------------------------------------------------

/**
 * Get the full leaderboard sorted by score descending.
 */
export const getRanking = () => api.get('/ranking')

export default api
