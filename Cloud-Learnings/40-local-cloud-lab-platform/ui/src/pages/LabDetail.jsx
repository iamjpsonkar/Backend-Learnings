import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchLab, fetchProgress, recordProgress, runLab } from '../api/client.js'

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h2
        style={{
          fontSize: '0.85rem',
          fontWeight: 700,
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          marginBottom: 10,
        }}
      >
        {title}
      </h2>
      {children}
    </div>
  )
}

function TaskCard({ task, index }) {
  const [showHints, setShowHints] = useState(false)
  return (
    <div
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '12px 16px',
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <span
          style={{
            background: 'var(--bg-hover)',
            borderRadius: 4,
            padding: '2px 8px',
            fontSize: '0.75rem',
            fontWeight: 700,
            color: 'var(--accent)',
            flexShrink: 0,
            fontFamily: 'var(--font-mono)',
          }}
        >
          {index + 1}
        </span>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: '0.9rem', marginBottom: task.hints?.length ? 8 : 0 }}>
            {task.description}
          </p>
          {task.hints?.length > 0 && (
            <>
              <button
                onClick={() => setShowHints(v => !v)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  padding: 0,
                  textDecoration: 'underline',
                }}
              >
                {showHints ? 'Hide hints' : `Show hints (${task.hints.length})`}
              </button>
              {showHints && (
                <ul style={{ marginTop: 8, paddingLeft: 16 }}>
                  {task.hints.map((hint, i) => (
                    <li key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 4 }}>
                      {hint}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default function LabDetail() {
  const { labId, '*': rest } = useParams()
  const fullId = rest ? `${labId}/${rest}` : labId

  const [lab, setLab] = useState(null)
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState(null)
  const [runError, setRunError] = useState(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchLab(fullId), fetchProgress(fullId)])
      .then(([labData, progressData]) => {
        setLab(labData)
        setProgress(progressData?.[0] || null)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [fullId])

  async function handleStartLab() {
    try {
      await recordProgress({ lab_id: fullId, status: 'in_progress', score: 0, max_score: 0 })
      setProgress(prev => ({ ...prev, status: 'in_progress' }))
    } catch (err) {
      console.error('Failed to record start:', err)
    }
  }

  async function handleRunValidation() {
    setRunning(true)
    setRunResult(null)
    setRunError(null)
    try {
      const result = await runLab(fullId)
      setRunResult(result)
      if (result.grade) {
        await recordProgress({
          lab_id: fullId,
          status: result.status,
          score: result.grade.score,
          max_score: result.grade.max_score,
          feedback: JSON.stringify(result.grade.feedback),
        })
        setProgress(prev => ({
          ...prev,
          status: result.status,
          score: result.grade.score,
          max_score: result.grade.max_score,
        }))
      }
    } catch (err) {
      setRunError(err.message)
    } finally {
      setRunning(false)
    }
  }

  if (loading) return <div style={{ color: 'var(--text-muted)', padding: 40 }}>Loading...</div>
  if (error) return (
    <div>
      <Link to="/" style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>← Back to labs</Link>
      <div style={{ color: 'var(--red)', marginTop: 16 }}>Error: {error}</div>
    </div>
  )
  if (!lab) return null

  const status = progress?.status || 'not_started'

  return (
    <div style={{ maxWidth: 800 }}>
      <div style={{ marginBottom: 20 }}>
        <Link to="/" style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>← Lab Catalog</Link>
      </div>

      {/* Lab header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
          <span className={`badge badge-${lab.difficulty}`}>{lab.difficulty}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: '2px 0' }}>
            {lab.category}
          </span>
          {lab.estimated_time && (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: '2px 0' }}>
              {lab.estimated_time}
            </span>
          )}
          {status !== 'not_started' && (
            <span className={`badge badge-${status}`}>{status.replace('_', ' ')}</span>
          )}
        </div>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: 8 }}>{lab.title}</h1>
        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>{lab.description}</p>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 28, flexWrap: 'wrap' }}>
        {status === 'not_started' && (
          <button
            onClick={handleStartLab}
            style={{
              background: 'var(--accent)',
              border: 'none',
              borderRadius: 'var(--radius)',
              color: 'white',
              padding: '8px 20px',
              fontWeight: 600,
              fontSize: '0.875rem',
            }}
          >
            Start Lab
          </button>
        )}
        {status !== 'not_started' && (
          <button
            onClick={handleRunValidation}
            disabled={running}
            style={{
              background: running ? 'var(--bg-hover)' : 'var(--green)',
              border: 'none',
              borderRadius: 'var(--radius)',
              color: running ? 'var(--text-muted)' : 'white',
              padding: '8px 20px',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: running ? 'not-allowed' : 'pointer',
            }}
          >
            {running ? 'Running validation...' : 'Validate & Grade'}
          </button>
        )}
        <a
          href={`http://localhost:4567/api/v1/labs/${fullId}`}
          target="_blank"
          rel="noreferrer"
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            color: 'var(--text-secondary)',
            padding: '8px 16px',
            fontSize: '0.875rem',
            textDecoration: 'none',
            display: 'inline-block',
          }}
        >
          View YAML
        </a>
      </div>

      {/* Validation result */}
      {runError && (
        <div style={{
          background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: 'var(--radius)',
          padding: '12px 16px',
          marginBottom: 20,
          color: 'var(--red)',
          fontSize: '0.875rem',
        }}>
          Validation error: {runError}
        </div>
      )}
      {runResult?.grade && (
        <div style={{
          background: runResult.grade.passed ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
          border: `1px solid ${runResult.grade.passed ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
          borderRadius: 'var(--radius)',
          padding: '16px',
          marginBottom: 20,
        }}>
          <div style={{ fontWeight: 700, marginBottom: 8, color: runResult.grade.passed ? 'var(--green)' : 'var(--red)' }}>
            {runResult.grade.passed ? 'Lab Passed!' : 'Lab Failed'} — Score: {runResult.grade.score}/{runResult.grade.max_score} ({runResult.grade.percentage}%)
          </div>
          {runResult.grade.feedback?.map((fb, i) => (
            <div key={i} style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: 4 }}>{fb}</div>
          ))}
        </div>
      )}

      {/* Lab content */}
      {lab.learning_objectives?.length > 0 && (
        <Section title="Learning Objectives">
          <ul style={{ paddingLeft: 20 }}>
            {lab.learning_objectives.map((obj, i) => (
              <li key={i} style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: 4 }}>{obj}</li>
            ))}
          </ul>
        </Section>
      )}

      {lab.prerequisites?.length > 0 && (
        <Section title="Prerequisites">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {lab.prerequisites.map((p, i) => (
              <span key={i} style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                padding: '4px 10px',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)',
              }}>{p}</span>
            ))}
          </div>
        </Section>
      )}

      {lab.docker_profiles?.length > 0 && (
        <Section title="Required Services">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {lab.docker_profiles.map((p, i) => (
              <code key={i} style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                padding: '4px 10px',
                fontSize: '0.8rem',
                color: 'var(--cyan)',
              }}>make start-{p}</code>
            ))}
          </div>
        </Section>
      )}

      {lab.tasks?.length > 0 && (
        <Section title="Tasks">
          {lab.tasks.map((task, i) => (
            <TaskCard key={task.id} task={task} index={i} />
          ))}
        </Section>
      )}

      {lab.safety_warning && (
        <div style={{
          background: 'rgba(234,179,8,0.08)',
          border: '1px solid rgba(234,179,8,0.3)',
          borderRadius: 'var(--radius)',
          padding: '12px 16px',
          marginBottom: 20,
          fontSize: '0.875rem',
          color: 'var(--yellow)',
        }}>
          Warning: {lab.safety_warning}
        </div>
      )}

      {lab.related_docs?.length > 0 && (
        <Section title="Related Documentation">
          <ul style={{ paddingLeft: 20 }}>
            {lab.related_docs.map((doc, i) => (
              <li key={i} style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: 4 }}>
                <code>{doc}</code>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}
