/**
 * ui/src/api/client.js — API client for the Lab Platform backend
 *
 * All functions return parsed JSON or throw an Error.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:4567'

/**
 * Generic fetch wrapper with error handling and logging.
 */
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    let errorMsg = `API error: ${response.status} ${response.statusText}`
    try {
      const errData = await response.json()
      errorMsg = errData.detail || errData.error || errorMsg
    } catch {
      // ignore parse error
    }
    throw new Error(errorMsg)
  }

  // 204 No Content
  if (response.status === 204) return null

  return response.json()
}

// ─────────────────────────────────────────────
// Health
// ─────────────────────────────────────────────

export function fetchHealth() {
  return apiFetch('/health')
}

// ─────────────────────────────────────────────
// Labs
// ─────────────────────────────────────────────

/**
 * List all labs. Optionally filter by category and/or difficulty.
 * @param {Object} filters - { category?: string, difficulty?: string }
 */
export function fetchLabs(filters = {}) {
  const params = new URLSearchParams()
  if (filters.category) params.set('category', filters.category)
  if (filters.difficulty) params.set('difficulty', filters.difficulty)
  const qs = params.toString() ? `?${params}` : ''
  return apiFetch(`/api/v1/labs${qs}`)
}

/**
 * Get full details for a lab.
 * @param {string} labId - e.g. "04-docker/docker-basics"
 */
export function fetchLab(labId) {
  return apiFetch(`/api/v1/labs/${labId}`)
}

// ─────────────────────────────────────────────
// Progress
// ─────────────────────────────────────────────

/**
 * Get all progress records, optionally filtered by lab_id.
 */
export function fetchProgress(labId = null) {
  const qs = labId ? `?lab_id=${encodeURIComponent(labId)}` : ''
  return apiFetch(`/api/v1/progress${qs}`)
}

/**
 * Record lab progress.
 * @param {Object} data - { lab_id, status, score, max_score, feedback? }
 */
export function recordProgress(data) {
  return apiFetch('/api/v1/progress', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/**
 * Reset progress for a lab.
 */
export function resetProgress(labId) {
  return apiFetch(`/api/v1/progress/${encodeURIComponent(labId)}`, {
    method: 'DELETE',
  })
}

// ─────────────────────────────────────────────
// Runner
// ─────────────────────────────────────────────

/**
 * Trigger a lab validation/grading run.
 * @param {string} labId
 * @param {boolean} verbose
 */
export function runLab(labId, verbose = false) {
  return apiFetch('/api/v1/runner/run', {
    method: 'POST',
    body: JSON.stringify({ lab_id: labId, verbose }),
  })
}

// ─────────────────────────────────────────────
// Services
// ─────────────────────────────────────────────

/**
 * Get Docker service statuses.
 * @param {string|null} profile - filter by profile
 */
export function fetchServices(profile = null) {
  const qs = profile ? `?profile=${encodeURIComponent(profile)}` : ''
  return apiFetch(`/api/v1/services${qs}`)
}

/**
 * Get active Docker Compose profiles.
 */
export function fetchActiveProfiles() {
  return apiFetch('/api/v1/services/profiles')
}
