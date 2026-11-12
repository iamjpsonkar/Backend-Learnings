import React, { useState, useEffect } from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import LabList from './pages/LabList.jsx'
import LabDetail from './pages/LabDetail.jsx'
import ProgressPage from './pages/ProgressPage.jsx'
import ServicesPage from './pages/ServicesPage.jsx'
import { fetchHealth } from './api/client.js'

function NavLink({ to, children }) {
  const location = useLocation()
  const active = location.pathname === to || (to !== '/' && location.pathname.startsWith(to))
  return (
    <Link
      to={to}
      style={{
        color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
        fontWeight: active ? 600 : 400,
        padding: '6px 12px',
        borderRadius: 'var(--radius)',
        background: active ? 'var(--bg-hover)' : 'transparent',
        transition: 'all 0.15s',
        textDecoration: 'none',
      }}
    >
      {children}
    </Link>
  )
}

function APIStatusDot({ status }) {
  const color = status === 'ok' ? 'var(--green)' : status === 'loading' ? 'var(--yellow)' : 'var(--red)'
  return (
    <span
      style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: color,
        marginRight: 6,
      }}
      title={`API ${status}`}
    />
  )
}

export default function App() {
  const [apiStatus, setApiStatus] = useState('loading')

  useEffect(() => {
    fetchHealth()
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))

    // Re-check every 30s
    const interval = setInterval(() => {
      fetchHealth()
        .then(() => setApiStatus('ok'))
        .catch(() => setApiStatus('error'))
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header
        style={{
          background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border)',
          padding: '0 24px',
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: '1.1rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Cloud Lab
          </span>
          <span
            style={{
              fontSize: '0.7rem',
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              padding: '1px 6px',
              color: 'var(--text-muted)',
            }}
          >
            v1.0
          </span>
        </div>

        <nav style={{ display: 'flex', gap: 4 }}>
          <NavLink to="/">Labs</NavLink>
          <NavLink to="/progress">Progress</NavLink>
          <NavLink to="/services">Services</NavLink>
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <APIStatusDot status={apiStatus} />
          API {apiStatus}
        </div>
      </header>

      {/* Main content */}
      <main style={{ flex: 1, padding: '24px', maxWidth: 1200, margin: '0 auto', width: '100%' }}>
        {apiStatus === 'error' && (
          <div
            style={{
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 'var(--radius)',
              padding: '12px 16px',
              marginBottom: 16,
              fontSize: '0.875rem',
              color: 'var(--red)',
            }}
          >
            Cannot reach the Lab API at{' '}
            <code>{import.meta.env.VITE_API_URL || 'http://localhost:4567'}</code>.
            {' '}Make sure the API is running: <code>make start-core</code>
          </div>
        )}

        <Routes>
          <Route path="/" element={<LabList />} />
          <Route path="/labs/:labId/*" element={<LabDetail />} />
          <Route path="/progress" element={<ProgressPage />} />
          <Route path="/services" element={<ServicesPage />} />
        </Routes>
      </main>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border)',
          padding: '12px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
        }}
      >
        <span>Local Cloud Lab Platform — all labs run locally, no cloud accounts needed</span>
        <span>
          <a href="http://localhost:4567/docs" target="_blank" rel="noreferrer">API Docs</a>
          {' · '}
          <a href="https://github.com/iamjpsonkar/Cloud-Learnings" target="_blank" rel="noreferrer">GitHub</a>
        </span>
      </footer>
    </div>
  )
}
