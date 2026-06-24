import React from 'react'
import TransactionForm from './components/TransactionForm'
import SummaryPanel from './components/SummaryPanel'
import RankingTable from './components/RankingTable'

/**
 * App — Root component.
 *
 * Layout: sticky header + three side-by-side (responsive) sections.
 * No routing required for this single-page application.
 */
export default function App() {
  return (
    <div className="app">
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                               */}
      {/* ------------------------------------------------------------------ */}
      <header className="app-header" id="app-header">
        <div className="header-inner">
          <div className="header-brand">
            <span className="header-logo">🏆</span>
            <div>
              <h1 className="header-title">Transaction Leaderboard</h1>
              <p className="header-subtitle">Fair ranking · Duplicate-safe · Concurrent-ready</p>
            </div>
          </div>
          <nav className="header-nav">
            <a href="#transaction-section">Transact</a>
            <a href="#summary-section">Summary</a>
            <a href="#ranking-section">Ranking</a>
          </nav>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Main content                                                         */}
      {/* ------------------------------------------------------------------ */}
      <main className="app-main" id="app-main">
        <TransactionForm />
        <SummaryPanel />
        <RankingTable />
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* Footer                                                               */}
      {/* ------------------------------------------------------------------ */}
      <footer className="app-footer" id="app-footer">
        <p>
          Transaction Leaderboard System &mdash; FastAPI + SQLite + React
        </p>
        <p className="footer-formula">
          Score = (Amount × 0.5) + (Transactions × 10) + (Active Days × 5)
        </p>
      </footer>
    </div>
  )
}
