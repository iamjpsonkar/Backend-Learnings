import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { fetchProgress, fetchLabs, resetProgress } from '../api/client.js'

export default function ProgressPage() {
  const [progress, setProgress] = useState([])
  const [labs, setLabs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const reload = () => {
    setLoading(true)
    Promise.all([fetchProgress(), fetchLabs()])
      .then(([prog, labsData]) => {
        setProgress(prog || [])
        setLabs(labsData || [])
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { reload() }, [])

  const labMap = Object.fromEntries(labs.map(l => [l.id, l]))

  const completed = progress.filter(p => p.status === 'completed').length
  const inProgress = progress.filter(p => p.status === 'in_progress').length
  const failed = progress.filter(p => p.status === 'failed').length
  const totalScore = progress.reduce((sum, p) => sum + (p.score || 0), 0)
  const totalMaxScore = progress.reduce((sum, p) => sum + (p.max_score || 0), 0)

  async function handleReset(labId) {
    if (!confirm(`Reset progress for "${labMap[labId]?.title || labId}"?`)) return
    try {
      await resetProgress(labId)
      reload()
    } catch (err) {
      alert('Failed to reset: ' + err.message)
    }
  }

  if (loading) return <div style={{ color: 'var(--text-muted)', padding: 40 }}>Loading...</div>
  if (error) return <div style={{ color: 'var(--red)', padding: 40 }}>Error: {error}</div>

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>Progress</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: 24 }}>
        Your lab completion history
      </p>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap' }}>
        {[
          { label: 'Completed', value: completed, color: 'var(--green)' },
          { label: 'In Progress', value: inProgress, color: 'var(--accent)' },
          { label: 'Failed', value: failed, color: 'var(--red)' },
          { label: 'Total Score', value: `${totalScore}/${totalMaxScore}`, color: 'var(--text-primary)' },
        ].map(stat => (
          <div key={stat.label} style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '12px 20px',
            minWidth: 120,
          }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: stat.color }}>{stat.value}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{stat.label}</div>
          </div>
        ))}
      </div>

      {progress.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 60 }}>
          No labs started yet. <Link to="/">Browse the lab catalog</Link> to get started.
        </div>
      ) : (
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
                {['Lab', 'Status', 'Score', 'Attempts', 'Actions'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left',
                    padding: '10px 16px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {progress.map(p => {
                const lab = labMap[p.lab_id]
                return (
                  <tr key={p.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px 16px' }}>
                      <Link to={`/labs/${p.lab_id}`} style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                        {lab?.title || p.lab_id}
                      </Link>
                      {lab && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{lab.category}</div>
                      )}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span className={`badge badge-${p.status}`}>
                        {p.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                      {p.max_score > 0 ? `${p.score}/${p.max_score}` : '—'}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                      {p.attempts || 0}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <button
                        onClick={() => handleReset(p.lab_id)}
                        style={{
                          background: 'none',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--radius)',
                          color: 'var(--text-muted)',
                          padding: '4px 10px',
                          fontSize: '0.75rem',
                          cursor: 'pointer',
                        }}
                      >
                        Reset
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
