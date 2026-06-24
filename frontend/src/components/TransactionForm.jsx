import React, { useState } from 'react'
import { submitTransaction } from '../services/api'

/**
 * TransactionForm — Section 1
 * Allows the user to submit a transaction via POST /transaction.
 * Handles loading state, success, and error feedback.
 */
export default function TransactionForm() {
  const [form, setForm] = useState({ userId: '', transactionId: '', amount: '' })
  const [status, setStatus] = useState(null) // { type: 'success'|'error', message: string }
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
    setStatus(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setStatus(null)
    setLoading(true)

    try {
      const response = await submitTransaction(
        form.transactionId.trim(),
        form.userId.trim(),
        form.amount
      )
      setStatus({
        type: 'success',
        message: `✅ ${response.data.message} — TxnID: ${response.data.transactionId}`,
      })
      setForm({ userId: '', transactionId: '', amount: '' })
    } catch (err) {
      const detail = err.response?.data?.detail
      const msg =
        (typeof detail === 'object' ? detail?.message : detail) ||
        err.response?.data?.message ||
        err.message ||
        'Something went wrong'
      const code = err.response?.status
      const prefix =
        code === 409 ? '⚠️ Duplicate:' :
        code === 429 ? '🚫 Rate limit:' :
        code === 400 ? '❌ Validation:' :
        '❌ Error:'
      setStatus({ type: 'error', message: `${prefix} ${msg}` })
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="card" id="transaction-section">
      <div className="card-header">
        <span className="card-icon">💳</span>
        <h2>Create Transaction</h2>
      </div>

      <form onSubmit={handleSubmit} className="form" id="transaction-form">
        <div className="form-group">
          <label htmlFor="txn-userId">User ID</label>
          <input
            id="txn-userId"
            name="userId"
            type="text"
            placeholder="e.g. user123"
            value={form.userId}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="txn-transactionId">Transaction ID</label>
          <input
            id="txn-transactionId"
            name="transactionId"
            type="text"
            placeholder="e.g. txn_abc_001"
            value={form.transactionId}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="txn-amount">Amount</label>
          <input
            id="txn-amount"
            name="amount"
            type="number"
            placeholder="e.g. 150.00"
            min="0.01"
            step="0.01"
            value={form.amount}
            onChange={handleChange}
            required
            disabled={loading}
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          id="submit-transaction-btn"
          disabled={loading}
        >
          {loading ? <span className="spinner" /> : 'Submit Transaction'}
        </button>
      </form>

      {status && (
        <div className={`alert alert-${status.type}`} id="txn-status">
          {status.message}
        </div>
      )}
    </section>
  )
}
