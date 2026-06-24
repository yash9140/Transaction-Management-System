import React, { useState } from 'react'
import { getUserSummary } from '../services/api'

/**
 * SummaryPanel — Section 2
 * Fetches and displays aggregate statistics for a given user via GET /summary/{userId}.
 */
export default function SummaryPanel() {
  const [userId, setUserId] = useState('')
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleFetch = async (e) => {
    e.preventDefault()
    if (!userId.trim()) return
    setSummary(null)
    setError(null)
    setLoading(true)

    try {
      const response = await getUserSummary(userId.trim())
      setSummary(response.data)
    } catch (err) {
      const detail = err.response?.data?.detail
      const msg =
        (typeof detail === 'object' ? detail?.message : detail) ||
        err.response?.data?.message ||
        err.message ||
        'Failed to fetch summary'
      setError(err.response?.status === 404 ? `User "${userId}" not found.` : msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="card" id="summary-section">
      <div className="card-header">
        <span className="card-icon">📊</span>
        <h2>User Summary</h2>
      </div>

      <form onSubmit={handleFetch} className="form" id="summary-form">
        <div className="form-group">
          <label htmlFor="summary-userId">User ID</label>
          <input
            id="summary-userId"
            type="text"
            placeholder="e.g. user123"
            value={userId}
            onChange={(e) => { setUserId(e.target.value); setError(null); setSummary(null) }}
            required
            disabled={loading}
          />
        </div>

        <button
          type="submit"
          className="btn btn-secondary"
          id="get-summary-btn"
          disabled={loading}
        >
          {loading ? <span className="spinner" /> : 'Get Summary'}
        </button>
      </form>

      {error && (
        <div className="alert alert-error" id="summary-error">{error}</div>
      )}

      {summary && (
        <div className="summary-result" id="summary-result">
          <div className="stat-grid">
            <div className="stat-card">
              <span className="stat-label">Total Amount</span>
              <span className="stat-value">${summary.totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Total Transactions</span>
              <span className="stat-value">{summary.totalTransactions}</span>
            </div>
            <div className="stat-card stat-card--highlight">
              <span className="stat-label">Score</span>
              <span className="stat-value">{summary.score.toFixed(2)}</span>
            </div>
          </div>
          <p className="summary-user-label">User: <strong>{summary.userId}</strong></p>
        </div>
      )}
    </section>
  )
}
