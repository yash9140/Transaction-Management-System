import React, { useState } from 'react'
import { getRanking } from '../services/api'

/**
 * RankingTable — Section 3
 * Fetches and displays the leaderboard via GET /ranking.
 * Shows rank, userId, and score in a table.
 */
export default function RankingTable() {
  const [ranking, setRanking] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [loaded, setLoaded] = useState(false)

  const handleLoad = async () => {
    setError(null)
    setLoading(true)

    try {
      const response = await getRanking()
      setRanking(response.data)
      setLoaded(true)
    } catch (err) {
      setError('Failed to load ranking. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const medalEmoji = (rank) => {
    if (rank === 1) return '🥇'
    if (rank === 2) return '🥈'
    if (rank === 3) return '🥉'
    return rank
  }

  return (
    <section className="card" id="ranking-section">
      <div className="card-header">
        <span className="card-icon">🏆</span>
        <h2>Ranking Leaderboard</h2>
      </div>

      <button
        onClick={handleLoad}
        className="btn btn-accent"
        id="load-ranking-btn"
        disabled={loading}
      >
        {loading ? <span className="spinner" /> : 'Load Ranking'}
      </button>

      {error && (
        <div className="alert alert-error" id="ranking-error">{error}</div>
      )}

      {loaded && !loading && ranking.length === 0 && (
        <div className="alert alert-info" id="ranking-empty">
          No users found. Submit some transactions first!
        </div>
      )}

      {ranking.length > 0 && (
        <div className="table-wrapper" id="ranking-table-wrapper">
          <table className="ranking-table" id="ranking-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>User</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {ranking.map((entry) => (
                <tr
                  key={entry.userId}
                  className={entry.rank <= 3 ? `rank-top-${entry.rank}` : ''}
                >
                  <td className="rank-cell">{medalEmoji(entry.rank)}</td>
                  <td className="user-cell">{entry.userId}</td>
                  <td className="score-cell">{entry.score.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {ranking.length > 0 && (
        <p className="ranking-formula">
          Score = (Amount × 0.5) + (Transactions × 10) + (Active Days × 5)
        </p>
      )}
    </section>
  )
}
