import React, { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { fetchLabs, fetchProgress } from '../api/client.js'

const DIFFICULTIES = ['all', 'beginner', 'intermediate', 'advanced']

const DIFF_COLORS = {
  beginner: 'var(--green)',
  intermediate: 'var(--yellow)',
  advanced: 'var(--red)',
}

function LabCard({ lab, progressMap }) {
  const progress = progressMap[lab.id]
  const status = progress?.status || 'not_started'

  return (
    <Link
      to={`/labs/${lab.id}`}
      style={{ textDecoration: 'none' }}
    >
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: '16px',
          cursor: 'pointer',
          transition: 'border-color 0.15s, background 0.15s',
          position: 'relative',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = 'var(--accent)'
          e.currentTarget.style.background = 'var(--bg-hover)'
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = 'var(--border)'
          e.currentTarget.style.background = 'var(--bg-card)'
        }}
      >
        {/* Status indicator */}
        {status === 'completed' && (
          <span
            style={{
              position: 'absolute',
              top: 12,
              right: 12,
              color: 'var(--green)',
              fontSize: '1rem',
            }}
            title="Completed"
          >
            ✓
          </span>
        )}

        <div style={{ marginBottom: 8 }}>
          <span
            style={{
              fontSize: '0.7rem',
              fontWeight: 600,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            {lab.category}
          </span>
        </div>

        <h3
          style={{
            fontSize: '0.95rem',
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: 8,
            lineHeight: 1.4,
          }}
        >
          {lab.title}
        </h3>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <span
            className={`badge badge-${lab.difficulty}`}
          >
            {lab.difficulty}
          </span>
          {lab.estimated_time && (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {lab.estimated_time}
            </span>
          )}
          {status !== 'not_started' && (
            <span className={`badge badge-${status}`}>
              {status.replace('_', ' ')}
            </span>
          )}
        </div>

        {progress?.score > 0 && (
          <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Score: {progress.score}/{progress.max_score}
          </div>
        )}
      </div>
    </Link>
  )
}

export default function LabList() {
  const [labs, setLabs] = useState([])
  const [progress, setProgress] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedDifficulty, setSelectedDifficulty] = useState('all')
  const [selectedCategory, setSelectedCategory] = useState('all')

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchLabs(), fetchProgress()])
      .then(([labsData, progressData]) => {
        setLabs(labsData || [])
        setProgress(progressData || [])
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const progressMap = useMemo(() => {
    return Object.fromEntries(progress.map(p => [p.lab_id, p]))
  }, [progress])

  const categories = useMemo(() => {
    const cats = [...new Set(labs.map(l => l.category))].sort()
    return ['all', ...cats]
  }, [labs])

  const filteredLabs = useMemo(() => {
    return labs.filter(lab => {
      const matchSearch = !searchQuery ||
        lab.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lab.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lab.id.toLowerCase().includes(searchQuery.toLowerCase())
      const matchDiff = selectedDifficulty === 'all' || lab.difficulty === selectedDifficulty
      const matchCat = selectedCategory === 'all' || lab.category === selectedCategory
      return matchSearch && matchDiff && matchCat
    })
  }, [labs, searchQuery, selectedDifficulty, selectedCategory])

  const completedCount = progress.filter(p => p.status === 'completed').length

  if (loading) {
    return (
      <div style={{ color: 'var(--text-muted)', padding: 40, textAlign: 'center' }}>
        Loading labs...
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ color: 'var(--red)', padding: 40 }}>
        Error loading labs: {error}
      </div>
    )
  }

  return (
    <div>
      {/* Header stats */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>Lab Catalog</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          {labs.length} labs · {completedCount} completed
        </p>
      </div>

      {/* Filters */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          marginBottom: 24,
          flexWrap: 'wrap',
          alignItems: 'center',
        }}
      >
        <input
          type="search"
          placeholder="Search labs..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            color: 'var(--text-primary)',
            padding: '8px 12px',
            fontSize: '0.875rem',
            width: 240,
            outline: 'none',
          }}
        />

        <select
          value={selectedDifficulty}
          onChange={e => setSelectedDifficulty(e.target.value)}
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            color: 'var(--text-primary)',
            padding: '8px 12px',
            fontSize: '0.875rem',
            outline: 'none',
          }}
        >
          {DIFFICULTIES.map(d => (
            <option key={d} value={d}>{d === 'all' ? 'All difficulties' : d}</option>
          ))}
        </select>

        <select
          value={selectedCategory}
          onChange={e => setSelectedCategory(e.target.value)}
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            color: 'var(--text-primary)',
            padding: '8px 12px',
            fontSize: '0.875rem',
            outline: 'none',
          }}
        >
          {categories.map(c => (
            <option key={c} value={c}>{c === 'all' ? 'All categories' : c}</option>
          ))}
        </select>

        {(searchQuery || selectedDifficulty !== 'all' || selectedCategory !== 'all') && (
          <button
            onClick={() => {
              setSearchQuery('')
              setSelectedDifficulty('all')
              setSelectedCategory('all')
            }}
            style={{
              background: 'none',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              color: 'var(--text-muted)',
              padding: '8px 12px',
              fontSize: '0.875rem',
            }}
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Lab grid */}
      {filteredLabs.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 60 }}>
          No labs match your filters.
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: 12,
          }}
        >
          {filteredLabs.map(lab => (
            <LabCard key={lab.id} lab={lab} progressMap={progressMap} />
          ))}
        </div>
      )}

      <div style={{ marginTop: 16, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        Showing {filteredLabs.length} of {labs.length} labs
      </div>
    </div>
  )
}
