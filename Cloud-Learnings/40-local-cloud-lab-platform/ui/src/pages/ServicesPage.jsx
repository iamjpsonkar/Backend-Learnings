import React, { useState, useEffect } from 'react'
import { fetchServices, fetchActiveProfiles } from '../api/client.js'

const PROFILE_COMMANDS = {
  core: 'make start-core',
  observability: 'make start-observability',
  security: 'make start-security',
  cicd: 'make start-cicd',
  data: 'make start-data',
  'aws-local': 'make start-aws-local',
  'azure-local': 'make start-azure-local',
}

function ServiceRow({ service }) {
  const statusColor = {
    running: 'var(--green)',
    exited: 'var(--text-muted)',
    not_running: 'var(--text-muted)',
    unhealthy: 'var(--red)',
    starting: 'var(--yellow)',
  }[service.status] || 'var(--text-muted)'

  return (
    <tr style={{ borderBottom: '1px solid var(--border)' }}>
      <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
        {service.name}
      </td>
      <td style={{ padding: '10px 16px' }}>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          fontSize: '0.8rem',
          color: statusColor,
        }}>
          <span style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: statusColor,
            flexShrink: 0,
          }} />
          {service.status}
          {service.health && service.health !== service.status && ` (${service.health})`}
        </span>
      </td>
      <td style={{ padding: '10px 16px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        <span style={{
          background: 'var(--bg-hover)',
          borderRadius: 3,
          padding: '2px 6px',
        }}>
          {service.profile}
        </span>
      </td>
      <td style={{ padding: '10px 16px', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
        {service.ports?.join(', ') || '—'}
      </td>
    </tr>
  )
}

export default function ServicesPage() {
  const [services, setServices] = useState([])
  const [activeProfiles, setActiveProfiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const reload = () => {
    setLoading(true)
    Promise.all([fetchServices(), fetchActiveProfiles()])
      .then(([svcData, profileData]) => {
        setServices(svcData?.services || [])
        setActiveProfiles(profileData?.profiles || [])
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    reload()
    const interval = setInterval(reload, 15000)
    return () => clearInterval(interval)
  }, [])

  const runningCount = services.filter(s => s.status === 'running').length
  const inactiveProfiles = Object.keys(PROFILE_COMMANDS).filter(p => !activeProfiles.includes(p))

  if (loading && services.length === 0) {
    return <div style={{ color: 'var(--text-muted)', padding: 40 }}>Loading...</div>
  }

  if (error) {
    return (
      <div style={{ color: 'var(--red)', padding: 40 }}>
        Error loading services: {error}
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>Services</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            {runningCount} of {services.length} containers running
          </p>
        </div>
        <button
          onClick={reload}
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            color: 'var(--text-secondary)',
            padding: '8px 14px',
            fontSize: '0.8rem',
          }}
        >
          Refresh
        </button>
      </div>

      {/* Active profiles */}
      {activeProfiles.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
            Active Profiles
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {activeProfiles.map(p => (
              <span key={p} style={{
                background: 'rgba(34,197,94,0.1)',
                border: '1px solid rgba(34,197,94,0.3)',
                borderRadius: 'var(--radius)',
                color: 'var(--green)',
                padding: '4px 12px',
                fontSize: '0.8rem',
                fontWeight: 500,
              }}>
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Inactive profiles */}
      {inactiveProfiles.length > 0 && (
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '14px 16px',
            marginBottom: 24,
          }}
        >
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 10 }}>
            Start additional service profiles:
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {inactiveProfiles.map(p => (
              <code
                key={p}
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  color: 'var(--text-secondary)',
                  padding: '4px 10px',
                  fontSize: '0.78rem',
                }}
              >
                {PROFILE_COMMANDS[p]}
              </code>
            ))}
          </div>
        </div>
      )}

      {/* Services table */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        overflow: 'hidden',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
              {['Service', 'Status', 'Profile', 'Ports'].map(h => (
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
            {services.map(service => (
              <ServiceRow key={service.name} service={service} />
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 12, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        Auto-refreshes every 15 seconds. All services are on the <code>cloud-lab-network</code> Docker network.
      </div>
    </div>
  )
}
