/**
 * TerraShield Backend Integration Hook
 * Manages API calls and state synchronization with Flask backend
 */

import { useState, useEffect, useRef } from 'react'
import * as API from './api'

// Default fallback values for offline mode
const DEFAULT_WATER = {
  ph: 7.5,
  turbidity: 2.1,
  flowRate: 15.0,
  trustScore: 99.0,
}

const DEFAULT_SOIL = {
  moisture: 45.0,
  nitrogen: 160.0,
  salinity: 1.1,
  trustScore: 98.5,
}

const DEFAULT_HEALTH = {
  malnutrition: 5.5,
  diseaseIncidence: 3.5,
  clinicVisits: 50,
  trustScore: 99.5,
}

const DEFAULT_CORR = {
  ws: 0.92,
  sh: 0.89,
  wh: 0.91,
  confidence: 2.0,
}

/**
 * useBackendData: Manages all API data fetching and state
 * Falls back to local generation if backend is unavailable
 */
export function useBackendData() {
  const [backendAvailable, setBackendAvailable] = useState(false)
  const [water, setWater] = useState(DEFAULT_WATER)
  const [soil, setSoil] = useState(DEFAULT_SOIL)
  const [health, setHealth] = useState(DEFAULT_HEALTH)
  const [corr, setCorr] = useState(DEFAULT_CORR)
  const [ghosts, setGhosts] = useState({ statuses: [], events: [] })
  const [isAttackActive, setIsAttackActive] = useState(false)
  const [attackTimestamp, setAttackTimestamp] = useState(null)
  const checkHealthRef = useRef(false)

  // ── Health check ──────────────────────────────────────────────────────
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const isHealthy = await API.healthCheck()
        setBackendAvailable(isHealthy)
        
        if (isHealthy) {
          console.log('✓ TerraShield Backend connected (localhost:5000)')
        } else {
          console.log('⚠ TerraShield Backend unavailable, using local simulation')
        }
      } catch {
        console.log('⚠ TerraShield Backend unavailable, using local simulation')
      }
    }

    if (!checkHealthRef.current) {
      checkHealthRef.current = true
      checkBackend()
    }
  }, [])

  // ── Fetch streams (water, soil, health) ─────────────────────────────
  useEffect(() => {
    if (!backendAvailable) return

    const id = setInterval(async () => {
      try {
        const data = await API.getStreams()
        if (data.water) setWater(data.water)
        if (data.soil) setSoil(data.soil)
        if (data.health) setHealth(data.health)
      } catch (error) {
        console.error('Error fetching streams:', error)
      }
    }, 2000)

    return () => clearInterval(id)
  }, [backendAvailable])

  // ── Fetch correlations ─────────────────────────────────────────────
  useEffect(() => {
    if (!backendAvailable) return

    const id = setInterval(async () => {
      try {
        const data = await API.getCorrelations()
        setCorr({
          ws: data.ws,
          sh: data.sh,
          wh: data.wh,
          confidence: data.confidence,
        })
      } catch (error) {
        console.error('Error fetching correlations:', error)
      }
    }, 500) // Poll more frequently for correlation updates

    return () => clearInterval(id)
  }, [backendAvailable])

  // ── Fetch ghost sensors ────────────────────────────────────────────
  useEffect(() => {
    if (!backendAvailable) return

    const id = setInterval(async () => {
      try {
        const data = await API.getGhosts()
        setGhosts(data)
      } catch (error) {
        console.error('Error fetching ghosts:', error)
      }
    }, 1000)

    return () => clearInterval(id)
  }, [backendAvailable])

  // ── Fetch status ───────────────────────────────────────────────────
  useEffect(() => {
    if (!backendAvailable) return

    const id = setInterval(async () => {
      try {
        const data = await API.getStatus()
        setIsAttackActive(data.attackActive)
      } catch (error) {
        console.error('Error fetching status:', error)
      }
    }, 1000)

    return () => clearInterval(id)
  }, [backendAvailable])

  return {
    backendAvailable,
    water,
    soil,
    health,
    corr,
    ghosts,
    isAttackActive,
    attackTimestamp,
    setAttackTimestamp,
  }
}

/**
 * useBackendActions: Manages attack/reset operations
 */
export function useBackendActions() {
  const [isAttackActive, setIsAttackActive] = useState(false)
  const [attackTimestamp, setAttackTimestamp] = useState(null)

  const handleAttack = async () => {
    try {
      const result = await API.injectAttack()
      if (result.ok) {
        setIsAttackActive(true)
        setAttackTimestamp(result.attackTimestamp)
      }
    } catch (error) {
      console.error('Error injecting attack:', error)
    }
  }

  const handleReset = async () => {
    try {
      const result = await API.resetAttack()
      if (result.ok) {
        setIsAttackActive(false)
        setAttackTimestamp(null)
      }
    } catch (error) {
      console.error('Error resetting attack:', error)
    }
  }

  return {
    isAttackActive,
    attackTimestamp,
    handleAttack,
    handleReset,
    setIsAttackActive,
    setAttackTimestamp,
  }
}
