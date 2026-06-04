/**
 * TerraShield API Service Layer
 * Connects React frontend to Flask backend at http://localhost:5000
 */

const API_BASE = 'http://localhost:5000/api'

// ── Error handling ─────────────────────────────────────────────────────────

class APIError extends Error {
  constructor(message, status, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

async function fetchAPI(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    const data = await response.json()

    if (!response.ok) {
      throw new APIError(
        data.error || `HTTP ${response.status}`,
        response.status,
        data
      )
    }

    return data
  } catch (error) {
    if (error instanceof APIError) throw error
    throw new APIError(`Network error: ${error.message}`, 0, null)
  }
}

// ── Stream Data ────────────────────────────────────────────────────────────

export async function getStreams() {
  /**
   * GET /api/streams
   * Returns: { ok, water, soil, health }
   */
  const result = await fetchAPI('/streams')
  
  return {
    water: result.water
      ? {
          ph: result.water.ph,
          turbidity: result.water.turbidity,
          flowRate: result.water.flow_rate,
          trustScore: result.water.trust_score,
        }
      : null,
    soil: result.soil
      ? {
          moisture: result.soil.moisture,
          nitrogen: result.soil.nitrogen,
          salinity: result.soil.salinity,
          trustScore: result.soil.trust_score,
        }
      : null,
    health: result.health
      ? {
          malnutrition: result.health.malnutrition,
          diseaseIncidence: result.health.disease_incidence,
          clinicVisits: result.health.clinic_visits,
          trustScore: result.health.trust_score,
        }
      : null,
  }
}

// ── Correlations ──────────────────────────────────────────────────────────

export async function getCorrelations() {
  /**
   * GET /api/correlations
   * Returns: { ok, water_soil_corr, soil_health_corr, water_health_corr, confidence, ... }
   */
  const result = await fetchAPI('/correlations')
  
  return {
    ws: result.water_soil_corr ?? 0.92,
    sh: result.soil_health_corr ?? 0.89,
    wh: result.water_health_corr ?? 0.91,
    confidence: result.confidence ?? 2.0,
    flaggedDomains: result.flagged_domains || [],
    attackVector: result.attack_vector,
  }
}

// ── Ghost Sensors ──────────────────────────────────────────────────────────

export async function getGhosts() {
  /**
   * GET /api/ghosts
   * Returns: { ok, statuses: [{id, domain, status, ...}], events: [...] }
   */
  const result = await fetchAPI('/ghosts')
  
  return {
    statuses: result.statuses || [],
    events: result.events || [],
  }
}

// ── Provenance Trace ───────────────────────────────────────────────────────

export async function getProvenance() {
  /**
   * GET /api/provenance/trace
   * Returns: { ok, trace: [step1, step2, ...], attack_ts, capture_ts, confidence }
   */
  const result = await fetchAPI('/provenance/trace')
  
  return {
    trace: result.trace || [],
    attackTimestamp: result.attack_ts ? new Date(result.attack_ts) : null,
    captureTime: result.capture_ts ? new Date(result.capture_ts) : null,
    confidence: result.confidence ?? 0,
  }
}

// ── System Status ──────────────────────────────────────────────────────────

export async function getStatus() {
  /**
   * GET /api/status
   * Returns: { ok, attack_active, uptime, ... }
   */
  const result = await fetchAPI('/status')
  
  return {
    attackActive: result.attack_active ?? false,
    uptime: result.uptime ?? 0,
  }
}

// ── Attribution (ML) ───────────────────────────────────────────────────────

export async function getAttribution() {
  /**
   * GET /api/attribution
   * Returns: { ok, crop_yield_change, factors: [...] }
   */
  const result = await fetchAPI('/attribution')
  
  return {
    cropYieldChange: result.crop_yield_change ?? 0,
    factors: result.factors || [],
  }
}

// ── Attack Control ────────────────────────────────────────────────────────

export async function injectAttack() {
  /**
   * POST /api/attack/inject
   * Triggers attack sequence on the backend
   * Returns: { ok, attack_timestamp, ... }
   */
  const result = await fetchAPI('/attack/inject', {
    method: 'POST',
  })
  
  return {
    ok: result.ok,
    attackTimestamp: result.attack_timestamp ? new Date(result.attack_timestamp) : new Date(),
  }
}

export async function resetAttack() {
  /**
   * POST /api/attack/reset
   * Resets all state on the backend
   * Returns: { ok, ... }
   */
  const result = await fetchAPI('/attack/reset', {
    method: 'POST',
  })
  
  return { ok: result.ok }
}

// ── Health Check ───────────────────────────────────────────────────────────

export async function healthCheck() {
  /**
   * GET /health
   * Quick connectivity test
   */
  try {
    const response = await fetch(`${API_BASE.replace('/api', '')}/health`)
    return response.ok
  } catch {
    return false
  }
}
