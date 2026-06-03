import { useState, useEffect, useRef, useCallback } from 'react'
import { LineChart, Line, ResponsiveContainer } from 'recharts'

// ─── helpers ──────────────────────────────────────────────────────────────────

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
const jitter = (center, half) => center + (Math.random() - 0.5) * half * 2

// ─── sound effects ────────────────────────────────────────────────────────────

const audioContext = typeof window !== 'undefined' ? new (window.AudioContext || window.webkitAudioContext)() : null

function playBeepSequence(enabled = true) {
  if (!enabled || !audioContext) return
  const now = audioContext.currentTime
  const freqs = [800, 600, 400]
  
  freqs.forEach((freq, i) => {
    const osc = audioContext.createOscillator()
    const gain = audioContext.createGain()
    
    osc.connect(gain)
    gain.connect(audioContext.destination)
    
    gain.gain.setValueAtTime(0.15, now + i * 0.15)
    gain.gain.exponentialRampToValueAtTime(0.01, now + i * 0.15 + 0.12)
    
    osc.frequency.value = freq
    osc.start(now + i * 0.15)
    osc.stop(now + i * 0.15 + 0.12)
  })
}

function playPing(enabled = true) {
  if (!enabled || !audioContext) return
  const now = audioContext.currentTime
  
  const osc = audioContext.createOscillator()
  const gain = audioContext.createGain()
  
  osc.connect(gain)
  gain.connect(audioContext.destination)
  
  gain.gain.setValueAtTime(0.12, now)
  gain.gain.exponentialRampToValueAtTime(0.01, now + 0.18)
  
  osc.frequency.setValueAtTime(1200, now)
  osc.frequency.exponentialRampToValueAtTime(600, now + 0.18)
  
  osc.start(now)
  osc.stop(now + 0.18)
}

function playRumble(enabled = true) {
  if (!enabled || !audioContext) return
  const now = audioContext.currentTime
  
  const osc = audioContext.createOscillator()
  const gain = audioContext.createGain()
  
  osc.connect(gain)
  gain.connect(audioContext.destination)
  
  gain.gain.setValueAtTime(0, now)
  gain.gain.linearRampToValueAtTime(0.08, now + 0.3)
  gain.gain.exponentialRampToValueAtTime(0.01, now + 1.5)
  
  osc.frequency.value = 60
  osc.start(now)
  osc.stop(now + 1.5)
}

// ─── sensor generators ────────────────────────────────────────────────────────

function genWater(attacked) {
  if (attacked) return {
    ph:          clamp(jitter(3.20,  0.18), 2.8,  3.8),
    turbidity:   clamp(jitter(28.0,  1.40), 23.5, 32.5),
    flowRate:    clamp(jitter(2.10,  0.18), 1.6,  2.7),
    trustScore:  clamp(jitter(12.0,  1.80), 7,    18),
  }
  return {
    ph:          clamp(jitter(7.50,  0.22), 6.5,  8.5),
    turbidity:   clamp(jitter(2.10,  0.38), 0.1,  4.0),
    flowRate:    clamp(jitter(15.0,  0.65), 12.0, 18.0),
    trustScore:  clamp(jitter(99.0,  0.45), 98.0, 100.0),
  }
}

function genSoil(attacked) {
  if (attacked) return {
    moisture:    clamp(jitter(78.0,  2.00), 71,   86),
    nitrogen:    clamp(jitter(160.0, 7.00), 140,  180),
    salinity:    clamp(jitter(3.80,  0.18), 3.2,  4.4),
    trustScore:  clamp(jitter(34.0,  2.80), 26,   43),
  }
  return {
    moisture:    clamp(jitter(45.0,  2.80), 35.0, 55.0),
    nitrogen:    clamp(jitter(160.0, 7.00), 140,  180),
    salinity:    clamp(jitter(1.10,  0.14), 0.8,  1.4),
    trustScore:  clamp(jitter(98.5,  0.55), 97.0, 100.0),
  }
}

function genHealth(attacked, elapsedMs) {
  if (!attacked) return {
    malnutrition:     clamp(jitter(5.5,  0.42), 4.0,  7.0),
    diseaseIncidence: clamp(jitter(3.5,  0.42), 2.0,  5.0),
    clinicVisits:     Math.round(clamp(jitter(50,  3.5), 40, 60)),
    trustScore:       clamp(jitter(99.5, 0.28), 99.0, 100.0),
  }
  return {
    malnutrition:     elapsedMs >= 8000
      ? clamp(jitter(19.0, 0.65), 17.0, 22.0)
      : clamp(jitter(5.5,  0.42), 4.0,  7.0),
    diseaseIncidence: elapsedMs >= 10000
      ? clamp(jitter(14.0, 0.65), 12.0, 16.5)
      : clamp(jitter(3.5,  0.42), 2.0,  5.0),
    clinicVisits:     Math.round(elapsedMs >= 12000
      ? clamp(jitter(134,  4.5), 122, 146)
      : clamp(jitter(50,   3.5), 40,  60)),
    trustScore:       elapsedMs >= 10000
      ? clamp(jitter(41.0, 2.20), 34,  49)
      : clamp(jitter(99.5, 0.28), 99.0, 100.0),
  }
}

// ─── history management ────────────────────────────────────────────────────────

const HIST = 20

function seedHistory(genFn, args) {
  const out = {}
  for (let i = 0; i < HIST; i++) {
    Object.entries(genFn(...args)).forEach(([k, v]) => {
      if (!out[k]) out[k] = []
      out[k].push(v)
    })
  }
  return out
}

function pushHistory(prev, data) {
  const next = {}
  Object.keys(data).forEach(k => {
    next[k] = [...(prev[k] || []).slice(-(HIST - 1)), data[k]]
  })
  return next
}

const INIT_WATER  = seedHistory(genWater,  [false])
const INIT_SOIL   = seedHistory(genSoil,   [false])
const INIT_HEALTH = seedHistory(genHealth, [false, 0])

// ─── correlation status ────────────────────────────────────────────────────────

function getCorrStatus(score) {
  if (score >= 0.80) return { label: 'CORRELATED',          color: '#22c55e', blink: false }
  if (score >= 0.25) return { label: 'ANOMALY',             color: '#f59e0b', blink: false }
  if (score >= 0.10) return { label: 'DIVERGENCE DETECTED', color: '#ef4444', blink: false }
  return                    { label: 'CRITICAL DIVERGENCE', color: '#ef4444', blink: true  }
}

// ─── ghost sensor config ──────────────────────────────────────────────────────

const GHOST_SENSORS = [
  { id: 'GW-GHOST-7a3f', label: 'Groundwater Node',     domain: 'WATER'  },
  { id: 'SW-GHOST-2c91', label: 'Surface Water',        domain: 'WATER'  },
  { id: 'RW-GHOST-b44e', label: 'Rainfall Monitor',     domain: 'WATER'  },
  { id: 'SM-GHOST-9d12', label: 'Soil Moisture A',      domain: 'SOIL'   },
  { id: 'SN-GHOST-4f87', label: 'Nitrate Probe',        domain: 'SOIL'   },
  { id: 'SC-GHOST-1e55', label: 'Salinity Check',       domain: 'SOIL'   },
  { id: 'HN-GHOST-8b23', label: 'Health Node Alpha',    domain: 'HEALTH' },
  { id: 'HC-GHOST-3a67', label: 'Clinic Reporter',      domain: 'HEALTH' },
  { id: 'HM-GHOST-6c90', label: 'Malnutrition Tracker', domain: 'HEALTH' },
]

const DOMAIN_COLOR = { WATER: '#38bdf8', SOIL: '#f59e0b', HEALTH: '#22c55e' }

// ─── Clock ────────────────────────────────────────────────────────────────────

function Clock() {
  const [t, setT] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setT(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <span style={{ color: '#f59e0b', fontSize: '0.76rem', letterSpacing: '0.12em' }}>
      {t.toISOString().replace('T', ' ').slice(0, 19)} UTC
    </span>
  )
}

// ─── MetricRow ─────────────────────────────────────────────────────────────────

function MetricRow({ label, value, unit, precision = 1 }) {
  const display = precision === 0 ? String(Math.round(value)) : value.toFixed(precision)
  return (
    <div style={{
      display: 'flex',
      alignItems: 'baseline',
      padding: '4px 0',
      borderBottom: '1px solid #0f1520',
    }}>
      <span style={{ flex: 1, fontSize: '0.63rem', color: '#4b5563', letterSpacing: '0.09em', textTransform: 'uppercase' }}>
        {label}
      </span>
      <span style={{
        fontSize: '0.9rem', color: '#d1d5db', fontVariantNumeric: 'tabular-nums',
        minWidth: '60px', textAlign: 'right', marginRight: '8px', letterSpacing: '0.03em',
      }}>
        {display}
      </span>
      <span style={{ fontSize: '0.6rem', color: '#374151', minWidth: '42px', letterSpacing: '0.05em' }}>
        {unit}
      </span>
    </div>
  )
}

// ─── TrustBar ──────────────────────────────────────────────────────────────────

function TrustBar({ pct }) {
  const color = pct < 50 ? '#ef4444' : pct < 80 ? '#f59e0b' : '#22c55e'
  return (
    <div style={{ width: '100%', height: '4px', background: '#0f1520', border: '1px solid #1a2030', marginTop: '10px' }}>
      <div style={{
        width: `${pct}%`, height: '100%', background: color,
        transition: 'width 0.55s ease, background 0.55s ease',
        boxShadow: `0 0 5px ${color}88`,
      }} />
    </div>
  )
}

// ─── Sparkline ─────────────────────────────────────────────────────────────────

const SPARK_COLORS = ['#f59e0b', '#22c55e', '#60a5fa']

function Sparkline({ hist, keys, ranges }) {
  const len = (hist[keys[0]] || []).length
  const data = Array.from({ length: len }, (_, i) => {
    const pt = {}
    keys.forEach((k, j) => {
      const [lo, hi] = ranges[j]
      pt[k] = clamp(((hist[k][i] - lo) / (hi - lo)) * 100, 0, 100)
    })
    return pt
  })

  return (
    <div style={{ marginTop: '12px', paddingTop: '8px', borderTop: '1px solid #0f1520' }}>
      <div style={{ fontSize: '0.56rem', color: '#374151', letterSpacing: '0.14em', marginBottom: '5px' }}>
        ▶ TREND ANALYSIS — 20PT ROLLING
      </div>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '4px' }}>
        {keys.map((k, j) => (
          <span key={k} style={{ fontSize: '0.54rem', color: SPARK_COLORS[j], letterSpacing: '0.08em' }}>
            ■ {k.replace(/([A-Z])/g, ' $1').toUpperCase()}
          </span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={54}>
        <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          {keys.map((k, j) => (
            <Line key={k} type="monotone" dataKey={k}
              stroke={SPARK_COLORS[j]} dot={false} strokeWidth={1.4} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ─── StreamCard ────────────────────────────────────────────────────────────────

function TypewriterTitle({ text, delayMs = 0 }) {
  const [displayedText, setDisplayedText] = useState('')
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    const startTimer = setTimeout(() => {
      let charIndex = 0
      const interval = setInterval(() => {
        if (charIndex <= text.length) {
          setDisplayedText(text.slice(0, charIndex))
          charIndex++
        } else {
          setIsComplete(true)
          clearInterval(interval)
        }
      }, 80)

      return () => clearInterval(interval)
    }, delayMs)

    return () => clearTimeout(startTimer)
  }, [text, delayMs])

  return (
    <span style={{
      display: 'inline-block',
      borderRight: isComplete ? 'none' : '2px solid #f59e0b',
      paddingRight: isComplete ? 0 : '2px',
      animation: isComplete ? 'none' : 'none',
      minHeight: '1em',
    }}>
      {displayedText}
    </span>
  )
}

function StreamCard({ title, trust, metrics, hist, sparkKeys, sparkRanges, delayMs = 0 }) {
  const borderColor = trust < 50 ? '#ef4444' : trust < 80 ? '#f59e0b' : '#1a2030'
  const glow = trust < 50
    ? '0 0 22px rgba(239,68,68,0.45), 0 0 7px rgba(239,68,68,0.3)'
    : trust < 80
    ? '0 0 22px rgba(245,158,11,0.38), 0 0 7px rgba(245,158,11,0.22)'
    : 'none'
  const trustColor = trust < 50 ? '#ef4444' : trust < 80 ? '#f59e0b' : '#22c55e'

  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      background: '#0c1018', border: `1px solid ${borderColor}`, boxShadow: glow,
      padding: '12px 14px', transition: 'box-shadow 0.7s ease, border-color 0.7s ease',
      overflow: 'hidden', minWidth: 0,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '10px', paddingBottom: '8px', borderBottom: '1px solid #1a2030', flexShrink: 0,
      }}>
        <span style={{ fontSize: '0.68rem', color: '#f59e0b', letterSpacing: '0.18em', fontWeight: 700, minHeight: '1.2em' }}>
          <TypewriterTitle text={title} delayMs={delayMs} />
        </span>
        <span style={{ fontSize: '0.6rem', color: trustColor, letterSpacing: '0.1em' }}>
          TRUST {trust.toFixed(1)}%
        </span>
      </div>
      <div style={{ flexShrink: 0 }}>{metrics}</div>
      <TrustBar pct={trust} />
      <Sparkline hist={hist} keys={sparkKeys} ranges={sparkRanges} />
    </div>
  )
}

// ─── AttackButton ─────────────────────────────────────────────────────────────

function AttackButton({ active, onAttack }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '5px 0', flexShrink: 0 }}>
      <button
        onClick={onAttack}
        disabled={active}
        style={{
          padding: '9px 44px',
          background: active ? 'rgba(239,68,68,0.07)' : 'transparent',
          border: `2px solid ${active ? '#ef4444' : '#f59e0b'}`,
          color: active ? '#ef4444' : '#f59e0b',
          fontFamily: "'Share Tech Mono', monospace",
          fontSize: '0.82rem', letterSpacing: '0.2em', textTransform: 'uppercase',
          cursor: active ? 'not-allowed' : 'pointer',
          boxShadow: active
            ? '0 0 20px rgba(239,68,68,0.3), inset 0 0 20px rgba(239,68,68,0.05)'
            : '0 0 18px rgba(245,158,11,0.25), inset 0 0 18px rgba(245,158,11,0.04)',
          transition: 'all 0.45s ease',
          outline: 'none',
        }}
      >
        {active ? '■ ATTACK SEQUENCE ACTIVE' : '⚡ INJECT SENSOR COMPROMISE'}
      </button>
    </div>
  )
}

// ─── CorrCell ─────────────────────────────────────────────────────────────────

function CorrCell({ score }) {
  if (score === null) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#080b10', border: '1px solid #0f1520',
        color: '#1f2937', fontSize: '0.85rem', letterSpacing: '0.12em',
      }}>
        ——
      </div>
    )
  }
  const st = getCorrStatus(score)
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: '5px', padding: '5px 4px', background: '#080d14', border: '1px solid #0f1520',
    }}>
      <span style={{ fontSize: '1.0rem', color: '#d1d5db', fontVariantNumeric: 'tabular-nums', letterSpacing: '0.04em' }}>
        {score.toFixed(2)}
      </span>
      <span style={{
        fontSize: '0.5rem', color: st.color, letterSpacing: '0.1em', textTransform: 'uppercase',
        border: `1px solid ${st.color}44`, padding: '2px 5px',
        animation: st.blink ? 'blink 0.75s infinite' : 'none', whiteSpace: 'nowrap',
      }}>
        {st.label}
      </span>
    </div>
  )
}

// ─── CorrelationPanel ─────────────────────────────────────────────────────────

const DOMAINS = ['WATER', 'SOIL', 'HEALTH']

function CorrelationPanel({ corr, conf }) {
  const getScore = (r, c) => {
    if (r === c) return null
    if ((r === 0 && c === 1) || (r === 1 && c === 0)) return corr.ws
    if ((r === 0 && c === 2) || (r === 2 && c === 0)) return corr.wh
    return corr.sh
  }

  const flagged = [...new Set([
    ...(corr.ws < 0.5 ? ['WATER', 'SOIL']   : []),
    ...(corr.sh < 0.5 ? ['SOIL', 'HEALTH']  : []),
    ...(corr.wh < 0.5 ? ['WATER', 'HEALTH'] : []),
  ])]

  const showVector = conf > 70
  const confColor  = conf < 20 ? '#22c55e' : conf < 60 ? '#f59e0b' : '#ef4444'

  const headerCells = [
    <div key="tl" />,
    ...DOMAINS.map(d => (
      <div key={`ch-${d}`} style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '0.6rem', color: '#f59e0b', letterSpacing: '0.14em',
        borderBottom: '1px solid #1a2030', paddingBottom: '4px',
      }}>
        {d}
      </div>
    )),
  ]

  const dataCells = DOMAINS.flatMap((row, r) => [
    <div key={`rh-${r}`} style={{
      display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
      paddingRight: '10px', fontSize: '0.6rem', color: '#f59e0b',
      letterSpacing: '0.14em', borderRight: '1px solid #1a2030',
    }}>
      {row}
    </div>,
    ...DOMAINS.map((_, c) => <CorrCell key={`c-${r}-${c}`} score={getScore(r, c)} />),
  ])

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', background: '#0c1018',
      border: `1px solid ${conf > 50 ? '#ef4444' : '#1a2030'}`,
      padding: '10px 14px', height: '100%', overflow: 'hidden',
      animation: conf > 50 ? 'pulsing-border 0.9s ease-in-out infinite' : 'none',
      transition: 'border-color 0.5s ease',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '8px', paddingBottom: '6px', borderBottom: '1px solid #1a2030', flexShrink: 0,
      }}>
        <span style={{ color: '#f59e0b', fontSize: '0.68rem', letterSpacing: '0.18em', fontWeight: 700 }}>
          CROSS-DOMAIN CORRELATION MATRIX
        </span>
        <span style={{ fontSize: '0.56rem', color: '#2d3748', letterSpacing: '0.1em' }}>
          TRI-STREAM INTEGRITY ANALYSIS
        </span>
      </div>

      <div style={{ flex: 1, display: 'flex', gap: '14px', overflow: 'hidden', minHeight: 0 }}>
        <div style={{
          flex: '0 0 auto', display: 'grid',
          gridTemplateColumns: '58px repeat(3, 1fr)',
          gridTemplateRows: '26px repeat(3, 1fr)',
          gap: '2px', width: '52%',
        }}>
          {headerCells}
          {dataCells}
        </div>

        <div style={{ width: '1px', background: '#1a2030', flexShrink: 0 }} />

        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          justifyContent: 'center', gap: '14px', overflow: 'hidden', padding: '4px 0',
        }}>
          <div>
            <div style={{ fontSize: '0.56rem', color: '#4b5563', letterSpacing: '0.14em', marginBottom: '5px' }}>
              ▶ ANOMALY CONFIDENCE
            </div>
            <div style={{
              fontSize: '1.5rem', color: confColor, letterSpacing: '0.04em',
              fontVariantNumeric: 'tabular-nums', lineHeight: 1, transition: 'color 0.5s ease',
            }}>
              {conf.toFixed(1)}%
            </div>
            <div style={{ width: '100%', height: '3px', background: '#0f1520', marginTop: '5px', border: '1px solid #1a2030' }}>
              <div style={{
                width: `${conf}%`, height: '100%', background: confColor,
                transition: 'width 0.25s ease, background 0.5s ease',
                boxShadow: `0 0 5px ${confColor}88`,
              }} />
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.56rem', color: '#4b5563', letterSpacing: '0.14em', marginBottom: '5px' }}>
              ▶ FLAGGED DOMAINS
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {flagged.length === 0
                ? <span style={{ fontSize: '0.65rem', color: '#22c55e', letterSpacing: '0.1em' }}>NONE</span>
                : flagged.map(d => (
                  <span key={d} style={{
                    fontSize: '0.6rem', color: '#ef4444', border: '1px solid #ef444455',
                    padding: '2px 7px', letterSpacing: '0.12em', background: 'rgba(239,68,68,0.06)',
                  }}>
                    {d}
                  </span>
                ))
              }
            </div>
          </div>

          <div style={{
            opacity: showVector ? 1 : 0,
            transform: showVector ? 'translateY(0)' : 'translateY(4px)',
            transition: 'opacity 0.8s ease, transform 0.8s ease',
          }}>
            <div style={{ fontSize: '0.56rem', color: '#4b5563', letterSpacing: '0.14em', marginBottom: '5px' }}>
              ▶ ATTACK VECTOR IDENTIFIED
            </div>
            <div style={{
              fontSize: '0.72rem', color: '#ef4444', letterSpacing: '0.1em',
              border: '1px solid #ef444444', padding: '5px 10px', background: 'rgba(239,68,68,0.07)',
              animation: showVector ? 'blink 1.4s infinite' : 'none',
            }}>
              WATER SENSOR NODE W-447
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── SensorRow ────────────────────────────────────────────────────────────────

function SensorRow({ sensor, index, isIntrusion, isLateral, captureTime }) {
  const triggered   = isIntrusion || isLateral
  const domainColor = DOMAIN_COLOR[sensor.domain]

  // stagger the ghost-pulse so each sensor fires at a slightly different phase
  const pulseDelay  = `${(index * 0.38).toFixed(2)}s`
  const statusAnim  = triggered
    ? 'blink 0.55s infinite'
    : `ghost-pulse 3.2s ${pulseDelay} infinite ease-in-out`

  const statusText  = isIntrusion ? 'INTRUSION DETECTED'
    : isLateral   ? 'LATERAL PROBE DETECTED'
    : '● WATCHING'

  return (
    <div style={{
      padding: '7px 12px',
      borderBottom: '1px solid #0a0e14',
      background: triggered ? 'rgba(239,68,68,0.04)' : 'transparent',
      // intrusion-flash plays once on mount when triggered === true
      animation: triggered ? 'intrusion-flash 1.2s ease-out forwards' : 'none',
      transition: 'background 0.6s ease',
    }}>

      {/* row 1: id + domain chip */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '2px' }}>
        <span style={{
          flex: 1, fontSize: '0.6rem', letterSpacing: '0.04em',
          color: triggered ? '#d1d5db' : '#4b5563',
          transition: 'color 0.4s ease',
        }}>
          {sensor.id}
        </span>
        <span style={{
          fontSize: '0.48rem', color: domainColor,
          border: `1px solid ${domainColor}33`, padding: '0px 4px', letterSpacing: '0.1em',
          flexShrink: 0,
        }}>
          {sensor.domain}
        </span>
      </div>

      {/* row 2: label + status */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.53rem', color: '#374151', letterSpacing: '0.06em' }}>
          {sensor.label}
        </span>
        <span style={{
          fontSize: '0.52rem',
          color: triggered ? '#ef4444' : '#22c55e',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          animation: statusAnim,
          flexShrink: 0,
          marginLeft: '6px',
          transition: 'color 0.4s ease',
        }}>
          {statusText}
        </span>
      </div>

      {/* intrusion fingerprint block */}
      {isIntrusion && (
        <div style={{
          marginTop: '8px', paddingTop: '7px', borderTop: '1px solid #1a2030',
        }}>
          <div style={{
            fontSize: '0.52rem', color: '#f59e0b', letterSpacing: '0.12em', marginBottom: '6px',
          }}>
            ▶ FINGERPRINT CAPTURED
          </div>
          <div style={{ fontSize: '0.5rem', color: '#6b7280', lineHeight: 1.85, letterSpacing: '0.04em' }}>
            <div>
              <span style={{ color: '#374151' }}>ATTACKER SIG&nbsp;&nbsp;</span>
              <span style={{ color: '#ef4444' }}>0xf3a9...d441</span>
            </div>
            <div>
              <span style={{ color: '#374151' }}>WRITE ATTEMPT&nbsp;</span>
              pH value injection
            </div>
            <div>
              <span style={{ color: '#374151' }}>TIMESTAMP&nbsp;&nbsp;&nbsp;&nbsp;</span>
              {captureTime ? captureTime.toISOString().slice(11, 19) : '--:--:--'} UTC
            </div>
            <div style={{ color: '#22c55e', marginTop: '3px' }}>
              REAL SENSOR W-447: VALIDATED ✓
            </div>
          </div>
        </div>
      )}

      {/* lateral probe block */}
      {isLateral && (
        <div style={{
          marginTop: '8px', paddingTop: '7px', borderTop: '1px solid #1a2030',
        }}>
          <div style={{
            fontSize: '0.52rem', color: '#f59e0b', letterSpacing: '0.12em', marginBottom: '5px',
          }}>
            ▶ LATERAL MOVEMENT LOGGED
          </div>
          <div style={{ fontSize: '0.5rem', color: '#6b7280', lineHeight: 1.85, letterSpacing: '0.04em' }}>
            <div><span style={{ color: '#374151' }}>ORIGIN&nbsp;&nbsp;</span>W-CLUSTER-4</div>
            <div><span style={{ color: '#374151' }}>TARGET&nbsp;&nbsp;</span>SURFACE WATER ARRAY</div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── GhostSidebar ─────────────────────────────────────────────────────────────

function GhostSidebar({ gwTriggered, swTriggered, captureTime }) {
  const caught = (gwTriggered ? 1 : 0) + (swTriggered ? 1 : 0)

  return (
    <aside style={{
      width: '280px',
      flexShrink: 0,
      display: 'flex',
      flexDirection: 'column',
      background: '#080b10',
      borderLeft: '1px solid #1a2030',
      overflow: 'hidden',
    }}>

      {/* panel header */}
      <div style={{
        padding: '10px 12px 9px',
        borderBottom: '1px solid #1a2030',
        flexShrink: 0,
      }}>
        <div style={{ fontSize: '0.64rem', color: '#f59e0b', letterSpacing: '0.14em', fontWeight: 700, lineHeight: 1.3 }}>
          GHOST SENSOR NETWORK
          <span style={{ color: '#2d3748' }}> // </span>
          ACTIVE DECOYS
        </div>
        <div style={{ fontSize: '0.52rem', color: '#374151', letterSpacing: '0.07em', marginTop: '4px' }}>
          Cryptographic honeypots monitoring for intrusion
        </div>
        {/* domain legend */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
          {Object.entries(DOMAIN_COLOR).map(([d, c]) => (
            <span key={d} style={{ fontSize: '0.46rem', color: c, letterSpacing: '0.08em' }}>
              ■ {d}
            </span>
          ))}
        </div>
      </div>

      {/* sensor list — scrollable */}
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        {GHOST_SENSORS.map((sensor, i) => (
          <SensorRow
            key={sensor.id}
            sensor={sensor}
            index={i}
            isIntrusion={sensor.id === 'GW-GHOST-7a3f' && gwTriggered}
            isLateral={sensor.id === 'SW-GHOST-2c91' && swTriggered}
            captureTime={captureTime}
          />
        ))}
      </div>

      {/* panel footer */}
      <div style={{
        padding: '9px 12px',
        borderTop: '1px solid #1a2030',
        background: '#060810',
        flexShrink: 0,
      }}>
        <div style={{ fontSize: '0.57rem', color: '#4b5563', letterSpacing: '0.1em', lineHeight: 2 }}>
          <div>
            DECOYS ACTIVE&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
            <span style={{ color: '#22c55e' }}>9 / 9</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span>INTRUSIONS CAUGHT&nbsp;</span>
            {/* key forces CSS animation replay when count increments */}
            <span key={caught} style={{
              color: caught === 0 ? '#22c55e' : '#ef4444',
              animation: caught > 0 ? 'blink 0.35s 5' : 'none',
              fontVariantNumeric: 'tabular-nums',
            }}>
              {caught}
            </span>
          </div>
          <div>
            REAL SENSORS PROTECTED&nbsp;
            <span style={{ color: '#22c55e' }}>24</span>
          </div>
        </div>
      </div>

    </aside>
  )
}

// ─── ProvenancePanel ──────────────────────────────────────────────────────────

function ProvenancePanel({ attackTimestamp, captureTime }) {
  const [visibleSteps, setVisibleSteps] = useState(1)
  const timelineRef = useRef(null)

  // Reveal each step 1.5s after the previous, starting immediately on mount
  useEffect(() => {
    const timers = [
      setTimeout(() => setVisibleSteps(2), 1500),
      setTimeout(() => setVisibleSteps(3), 3000),
      setTimeout(() => setVisibleSteps(4), 4500),
      setTimeout(() => setVisibleSteps(5), 6000),
    ]
    return () => timers.forEach(clearTimeout)
  }, [])

  // Smooth-scroll timeline to reveal each new step as it appears
  useEffect(() => {
    const el = timelineRef.current
    if (!el) return
    const raf = requestAnimationFrame(() => {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    })
    return () => cancelAnimationFrame(raf)
  }, [visibleSteps])

  const ats = attackTimestamp
    ? attackTimestamp.toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
    : '--:--:-- UTC'
  const cts = captureTime
    ? captureTime.toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
    : '--:--:-- UTC'

  // Step definitions — each line is either plain {t} or structured {t, v, s, hi}
  const STEPS = [
    {
      id: 1, color: '#ef4444', badge: 'STEP 01',
      title: 'HEALTH ANOMALY DETECTED',
      lines: [
        { t: 'District 7 Malnutrition Index: ', v: '19.3%', s: ' (+174% above baseline)', hi: true },
        { t: `Detected: ${cts}` },
        { t: 'Confidence: ', v: '94%', hi: true },
      ],
      conn: { label: '↓ TRACING UPSTREAM...', root: false },
    },
    {
      id: 2, color: '#f59e0b', badge: 'STEP 02',
      title: 'CROP YIELD FAILURE CORRELATED',
      lines: [
        { t: 'Wheat yield projections: ', v: '-67%', s: ' vs seasonal average', hi: true },
        { t: 'Period: 6 weeks prior to health anomaly' },
        { t: 'Source: Agricultural Advisory AI — Model v2.3' },
      ],
      conn: { label: '↓ TRACING UPSTREAM...', root: false },
    },
    {
      id: 3, color: '#f59e0b', badge: 'STEP 03',
      title: 'IRRIGATION MODEL CORRUPTION',
      lines: [
        { t: 'Soil moisture readings fed incorrect water volumes' },
        { t: 'Over-irrigation event: ', v: '+340%', s: ' normal flow', hi: true },
        { t: 'Duration: ', v: '18 days' },
        { t: 'Soil salinity rose from ', v: '1.1 → 3.8 dS/m', s: ' (crop damage threshold: 2.0)', hi: true },
      ],
      conn: { label: '↓ TRACING UPSTREAM...', root: false },
    },
    {
      id: 4, color: '#ef4444', badge: 'STEP 04',
      title: 'POISONED SENSOR IDENTIFIED',
      lines: [
        { t: 'SENSOR ID: ', v: 'W-447', s: ' // Groundwater Node, Sector 4', hi: true },
        { t: 'Compromised reading: ', v: 'pH 3.2', s: ' (reported as 7.4)', hi: true },
        { t: 'Turbidity: ', v: '28 NTU', s: ' (reported as 1.2)' },
        { t: `Compromise window: ${ats}` },
        { t: 'Ghost sensor GW-GHOST-7a3f confirmed intrusion attempt', amber: true },
      ],
      conn: { label: '↓ ROOT CAUSE', root: true },
    },
    {
      id: 5, color: '#22c55e', badge: 'STEP 05', final: true,
      title: 'ROOT CAUSE IDENTIFIED ✓',
      lines: [
        { t: 'Single compromised sensor (W-447) propagated through:' },
        { t: 'Water → Irrigation AI → Soil Conditions → Crop Failure → Health Outcomes', chain: true },
        { t: 'Total cascade duration: ', v: '~8 weeks simulated' },
        { t: 'TerraShield detection time: ', v: '4.2 seconds', hi: true },
        { t: '⚠ Without TerraShield: INVISIBLE until health survey', alert: true },
      ],
      conn: null,
    },
  ]

  return (
    <>
      {/* dim scrim behind the panel — draws focus to the trace */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 199,
        background: 'rgba(0,0,0,0.55)',
        animation: 'fade-scrim 0.5s ease both',
        pointerEvents: 'none',
      }} />

      <div style={{
        position: 'fixed',
        bottom: 0, left: 0, right: 0,
        height: '78vh',
        zIndex: 200,
        display: 'flex',
        flexDirection: 'column',
        background: '#0f1117',
        borderTop: '2px solid #ef4444',
        boxShadow: '0 -30px 90px rgba(239,68,68,0.18), 0 -2px 0 #ef4444',
        animation: 'slide-up-panel 0.65s cubic-bezier(0.16, 1, 0.3, 1) both',
      }}>

        {/* ── Panel header ── */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 24px 9px',
          background: '#0a0c10',
          borderBottom: '1px solid #1a2030',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0,
              background: '#ef4444', boxShadow: '0 0 8px #ef4444',
              animation: 'pulse-dot 0.8s infinite',
            }} />
            <span style={{ color: '#ef4444', fontSize: '0.8rem', letterSpacing: '0.18em', fontWeight: 700 }}>
              PROVENANCE TRACE
            </span>
            <span style={{ color: '#2d3748', fontSize: '0.8rem', letterSpacing: '0.18em' }}>
              // CAUSALITY CHAIN RECONSTRUCTED
            </span>
          </div>
          {/* step progress pills */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '0.54rem', color: '#4b5563', letterSpacing: '0.12em' }}>
              {visibleSteps} / 5 NODES
            </span>
            <div style={{ display: 'flex', gap: '3px' }}>
              {STEPS.map(s => (
                <div key={s.id} style={{
                  width: '18px', height: '3px',
                  background: s.id <= visibleSteps ? s.color : '#1a2030',
                  boxShadow: s.id <= visibleSteps ? `0 0 5px ${s.color}` : 'none',
                  transition: 'background 0.4s ease, box-shadow 0.4s ease',
                }} />
              ))}
            </div>
          </div>
        </div>

        {/* ── Scrollable timeline ── */}
        <div
          ref={timelineRef}
          style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', padding: '20px 28px 12px' }}
        >
          {STEPS.filter(s => s.id <= visibleSteps).map(step => (
            <div key={step.id}>

              {/* Step row: node circle + content block */}
              <div style={{
                display: 'flex', alignItems: 'flex-start', gap: '16px',
                animation: 'step-reveal 0.55s ease both',
              }}>

                {/* Colored ring node */}
                <div style={{ flexShrink: 0, paddingTop: '2px' }}>
                  <div style={{
                    width: '22px', height: '22px', borderRadius: '50%',
                    background: `${step.color}18`,
                    border: `2px solid ${step.color}`,
                    boxShadow: `0 0 14px ${step.color}55, 0 0 4px ${step.color}33`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    animation: step.final ? 'node-pulse 2.2s ease-in-out infinite' : 'none',
                  }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: step.color }} />
                  </div>
                </div>

                {/* Text block */}
                <div style={{
                  flex: 1, minWidth: 0,
                  background: '#0c1018',
                  border: '1px solid #1a2030',
                  borderLeft: `3px solid ${step.color}77`,
                  padding: '10px 14px',
                }}>
                  {/* Badge + title */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
                    <span style={{
                      fontSize: '0.48rem', color: '#374151',
                      border: '1px solid #1a2030', padding: '1px 6px', letterSpacing: '0.14em', flexShrink: 0,
                    }}>
                      {step.badge}
                    </span>
                    <span style={{ fontSize: '0.74rem', color: step.color, letterSpacing: '0.1em', fontWeight: 700 }}>
                      {step.title}
                    </span>
                  </div>

                  {/* Detail lines */}
                  <div style={{ fontSize: '0.6rem', lineHeight: 1.95, letterSpacing: '0.04em' }}>
                    {step.lines.map((line, j) => (
                      <div key={j} style={{
                        color: line.chain ? step.color
                          : line.alert ? '#ef4444'
                          : line.amber ? '#f59e0b'
                          : '#6b7280',
                        fontWeight: line.chain ? 600 : 'normal',
                      }}>
                        {line.v ? (
                          <>
                            <span style={{ color: '#4b5563' }}>{line.t}</span>
                            <span style={{ color: line.hi ? '#d1d5db' : step.color }}>{line.v}</span>
                            {line.s && <span style={{ color: '#374151' }}>{line.s}</span>}
                          </>
                        ) : line.t}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Animated connector (appears when next step reveals) */}
              {step.conn && visibleSteps > step.id && (
                <div style={{ display: 'flex', gap: '16px', margin: '4px 0' }}>
                  <div style={{ width: '22px', flexShrink: 0, display: 'flex', justifyContent: 'center' }}>
                    <div style={{
                      width: '0',
                      height: '36px',
                      borderLeft: `2px dashed ${step.conn.root ? '#f59e0b55' : '#2a354866'}`,
                      transformOrigin: 'top center',
                      animation: 'draw-connector 0.45s ease both',
                    }} />
                  </div>
                  <div style={{
                    paddingTop: '8px',
                    fontSize: '0.52rem',
                    color: step.conn.root ? '#f59e0b' : '#2d3748',
                    letterSpacing: '0.16em',
                    animation: 'step-reveal 0.4s 0.2s ease both',
                  }}>
                    {step.conn.label}
                  </div>
                </div>
              )}

            </div>
          ))}
        </div>

        {/* ── Export footer ── */}
        {visibleSteps >= 5 && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '10px 28px 12px',
            borderTop: '1px solid #1a2030',
            background: '#0a0c10',
            flexShrink: 0,
            animation: 'step-reveal 0.6s 0.3s ease both',
          }}>
            <div style={{ fontSize: '0.54rem', color: '#374151', letterSpacing: '0.1em', lineHeight: 1.75 }}>
              <div>CHAIN LENGTH: 5 NODES&nbsp; |&nbsp; CASCADE: ~8 WEEKS SIMULATED</div>
              <div>
                DETECTION TIME: <span style={{ color: '#22c55e' }}>4.2s</span>
                &nbsp;|&nbsp; CONFIDENCE: <span style={{ color: '#22c55e' }}>94.0%</span>
                &nbsp;|&nbsp; STATUS: <span style={{ color: '#22c55e' }}>RESOLVED</span>
              </div>
            </div>
            <button
              onClick={() => {}}
              style={{
                padding: '9px 22px',
                background: 'transparent',
                border: '1px solid #22c55e',
                color: '#22c55e',
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: '0.68rem',
                letterSpacing: '0.16em',
                cursor: 'pointer',
                textTransform: 'uppercase',
                boxShadow: '0 0 16px rgba(34,197,94,0.18), inset 0 0 12px rgba(34,197,94,0.04)',
                outline: 'none',
                transition: 'background 0.25s ease, box-shadow 0.25s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(34,197,94,0.08)'
                e.currentTarget.style.boxShadow  = '0 0 26px rgba(34,197,94,0.35), inset 0 0 14px rgba(34,197,94,0.08)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.boxShadow  = '0 0 16px rgba(34,197,94,0.18), inset 0 0 12px rgba(34,197,94,0.04)'
              }}
            >
              ↗ EXPORT PROVENANCE REPORT
            </button>
          </div>
        )}

      </div>
    </>
  )
}

// ─── StatusBar ────────────────────────────────────────────────────────────────

function StatusBar({ anomaly, isAttackActive, isMuted, onMuteToggle }) {
  return (
    <footer style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      display: 'flex', alignItems: 'center', gap: '10px',
      padding: '7px 18px', background: '#0c1018',
      borderTop: '1px solid #1a2030', zIndex: 100,
      height: '32px',
    }}>
      <div style={{
        width: '7px', height: '7px', borderRadius: '50%',
        background: anomaly ? '#ef4444' : '#22c55e',
        boxShadow: `0 0 6px ${anomaly ? '#ef4444' : '#22c55e'}`,
        animation: anomaly ? 'pulse-dot 0.9s infinite' : 'pulse-dot 2s infinite',
        flexShrink: 0,
      }} />
      
      {isAttackActive ? (
        <div style={{
          flex: 1,
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          height: '20px',
        }}>
          <span style={{
            fontSize: '0.7rem', letterSpacing: '0.18em',
            color: '#ef4444',
            animation: 'marquee 8s linear infinite',
            display: 'inline-block',
            whiteSpace: 'nowrap',
            paddingRight: '100%',
          }}>
            ⚠ CROSS-DOMAIN ANOMALY DETECTED — SECTOR 4 — WATER INTEGRITY COMPROMISED
          </span>
        </div>
      ) : (
        <>
          <span style={{
            fontSize: '0.7rem', letterSpacing: '0.18em',
            color: '#22c55e',
            animation: 'status-pulse 1.5s ease-in-out infinite',
            className: 'status-pulse',
          }}>
            ALL SYSTEMS NOMINAL
          </span>
          <span style={{ marginLeft: 'auto', fontSize: '0.58rem', color: '#2d3748', letterSpacing: '0.09em' }}>
            STREAMS: W[2s] S[2s] H[3s]&nbsp; |&nbsp; CORR[80ms]&nbsp; |&nbsp; GHOST[9]&nbsp; |&nbsp; TERRASHIELD v3.0
          </span>
        </>
      )}
      
      <button
        onClick={onMuteToggle}
        style={{
          background: 'transparent',
          border: `1px solid ${isMuted ? '#f59e0b' : '#374151'}`,
          color: isMuted ? '#f59e0b' : '#6b7280',
          fontFamily: "'Share Tech Mono', monospace",
          fontSize: '0.65rem',
          padding: '2px 7px',
          cursor: 'pointer',
          letterSpacing: '0.1em',
          transition: 'all 0.2s ease',
          outline: 'none',
          flexShrink: 0,
        }}
        onMouseEnter={e => {
          if (!isMuted) {
            e.currentTarget.style.borderColor = '#f59e0b'
            e.currentTarget.style.color = '#f59e0b'
          }
        }}
        onMouseLeave={e => {
          if (!isMuted) {
            e.currentTarget.style.borderColor = '#374151'
            e.currentTarget.style.color = '#6b7280'
          }
        }}
      >
        {isMuted ? '🔇' : '🔊'}
      </button>
    </footer>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [isAttackActive,  setIsAttackActive]  = useState(false)
  const [attackTimestamp, setAttackTimestamp] = useState(null)
  const [isMuted, setIsMuted] = useState(false)

  // sensor readings
  const [water,  setWater]  = useState(() => genWater(false))
  const [soil,   setSoil]   = useState(() => genSoil(false))
  const [health, setHealth] = useState(() => genHealth(false, 0))

  // sparkline history
  const [waterHist,  setWaterHist]  = useState(INIT_WATER)
  const [soilHist,   setSoilHist]   = useState(INIT_SOIL)
  const [healthHist, setHealthHist] = useState(INIT_HEALTH)

  // correlation lerp state
  const corrTarget  = useRef({ ws: 0.92, wh: 0.89, sh: 0.91 })
  const corrCurrent = useRef({ ws: 0.92, wh: 0.89, sh: 0.91 })
  const [corr, setCorr] = useState({ ws: 0.92, wh: 0.89, sh: 0.91 })
  const [conf, setConf] = useState(2.0)

  // ghost sensor trigger state — refs prevent double-fire in 80ms loop
  const gwTrigRef = useRef(false)
  const swTrigRef = useRef(false)
  const beepRef = useRef(false)
  const pingRef = useRef(false)
  const rumbleRef = useRef(false)
  const [gwTriggered, setGwTriggered] = useState(false)
  const [swTriggered, setSwTriggered] = useState(false)
  const [captureTime, setCaptureTime] = useState(null)

  // provenance trace trigger
  const provenanceTrigRef = useRef(false)
  const [showProvenance, setShowProvenance] = useState(false)

  // water tick — 2s
  useEffect(() => {
    const id = setInterval(() => {
      const d = genWater(isAttackActive)
      setWater(d)
      setWaterHist(h => pushHistory(h, d))
    }, 2000)
    return () => clearInterval(id)
  }, [isAttackActive])

  // soil tick — 2s
  useEffect(() => {
    const id = setInterval(() => {
      const d = genSoil(isAttackActive)
      setSoil(d)
      setSoilHist(h => pushHistory(h, d))
    }, 2000)
    return () => clearInterval(id)
  }, [isAttackActive])

  // health tick — 3s
  useEffect(() => {
    const id = setInterval(() => {
      const elapsed = attackTimestamp ? Date.now() - Number(attackTimestamp) : 0
      const d = genHealth(isAttackActive, elapsed)
      setHealth(d)
      setHealthHist(h => pushHistory(h, d))
    }, 3000)
    return () => clearInterval(id)
  }, [isAttackActive, attackTimestamp])

  // 80ms loop: correlation lerp + ghost sensor triggers
  useEffect(() => {
    const LERP = 0.12

    const id = setInterval(() => {
      const elapsed = isAttackActive && attackTimestamp
        ? Date.now() - Number(attackTimestamp)
        : 0

      // ── correlation targets ──────────────────────────────────────────────
      let wsT, whT, shT, confVal

      if (!isAttackActive) {
        wsT = clamp(corrTarget.current.ws + (Math.random() - 0.5) * 0.012, 0.85, 0.98)
        whT = clamp(corrTarget.current.wh + (Math.random() - 0.5) * 0.012, 0.85, 0.98)
        shT = clamp(corrTarget.current.sh + (Math.random() - 0.5) * 0.012, 0.85, 0.98)
        confVal = 2.0 + (Math.random() - 0.5) * 0.6
      } else {
        wsT = elapsed >= 3000
          ? clamp(0.12 + (Math.random() - 0.5) * 0.04, 0.05, 0.21)
          : clamp(corrTarget.current.ws + (Math.random() - 0.5) * 0.008, 0.85, 0.98)
        whT = elapsed >= 8000
          ? clamp(0.08 + (Math.random() - 0.5) * 0.03, 0.03, 0.14)
          : clamp(corrTarget.current.wh + (Math.random() - 0.5) * 0.008, 0.85, 0.98)
        shT = elapsed >= 6000
          ? clamp(0.31 + (Math.random() - 0.5) * 0.06, 0.20, 0.42)
          : clamp(corrTarget.current.sh + (Math.random() - 0.5) * 0.008, 0.85, 0.98)
        confVal = Math.min(94, 2 + (elapsed / 10000) * 92) + (Math.random() - 0.5) * 0.8
      }

      corrTarget.current = { ws: wsT, wh: whT, sh: shT }

      const c = corrCurrent.current
      c.ws += (wsT - c.ws) * LERP
      c.wh += (whT - c.wh) * LERP
      c.sh += (shT - c.sh) * LERP

      setCorr({ ws: c.ws, wh: c.wh, sh: c.sh })
      setConf(clamp(confVal, 1.0, 100.0))

      // ── ghost sensor triggers ────────────────────────────────────────────
      if (isAttackActive) {
        // beep sequence on attack start (once)
        if (elapsed >= 0 && !beepRef.current && elapsed < 100) {
          beepRef.current = true
          playBeepSequence(!isMuted)
        }
        
        if (elapsed >= 4000 && !gwTrigRef.current) {
          gwTrigRef.current = true
          setGwTriggered(true)
          setCaptureTime(new Date())
          playPing(!isMuted)
        }
        if (elapsed >= 6000 && !swTrigRef.current) {
          swTrigRef.current = true
          setSwTriggered(true)
          playPing(!isMuted)
        }
        if (elapsed >= 12000 && !provenanceTrigRef.current) {
          provenanceTrigRef.current = true
          setShowProvenance(true)
          playRumble(!isMuted)
        }
      }
    }, 80)

    return () => clearInterval(id)
  }, [isAttackActive, attackTimestamp, isMuted])

  const handleAttack = useCallback(() => {
    setIsAttackActive(true)
    setAttackTimestamp(new Date())
  }, [])

  const handleReset = useCallback(() => {
    setIsAttackActive(false)
    setAttackTimestamp(null)
    setShowProvenance(false)
    
    // Reset refs
    gwTrigRef.current = false
    swTrigRef.current = false
    beepRef.current = false
    pingRef.current = false
    rumbleRef.current = false
    provenanceTrigRef.current = false
    
    // Reset state
    setGwTriggered(false)
    setSwTriggered(false)
    setCaptureTime(null)
    
    // Reset sensor data to normal
    setWater(genWater(false))
    setSoil(genSoil(false))
    setHealth(genHealth(false, 0))
    
    // Reset history
    setWaterHist(INIT_WATER)
    setSoilHist(INIT_SOIL)
    setHealthHist(INIT_HEALTH)
    
    // Reset correlations
    corrTarget.current = { ws: 0.92, wh: 0.89, sh: 0.91 }
    corrCurrent.current = { ws: 0.92, wh: 0.89, sh: 0.91 }
    setCorr({ ws: 0.92, wh: 0.89, sh: 0.91 })
    setConf(2.0)
  }, [])

  const minTrust = Math.min(water.trustScore, soil.trustScore, health.trustScore)
  const anomaly  = minTrust < 90

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: '#0a0c0f',
      fontFamily: "'Share Tech Mono', monospace",
      overflow: 'hidden',
      paddingBottom: '32px',
    }}>

      {/* ── Header ── */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '9px 18px', background: '#0c1018',
        borderBottom: '1px solid #1a2030', flexShrink: 0,
      }}>
        <div>
          <span style={{ color: '#f59e0b', fontSize: '0.92rem', letterSpacing: '0.22em', fontWeight: 700 }}>
            TERRASHIELD
          </span>
          <span style={{ color: '#2d3748', fontSize: '0.92rem', letterSpacing: '0.22em' }}>
            {' '}// TRI-DOMAIN INTEGRITY MONITOR
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <Clock />
          <button
            onClick={handleReset}
            style={{
              padding: '6px 12px',
              background: 'transparent',
              border: '1px solid #f59e0b',
              color: '#f59e0b',
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: '0.65rem',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              cursor: 'pointer',
              outline: 'none',
              transition: 'all 0.25s ease',
              boxShadow: '0 0 12px rgba(245,158,11,0.15)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(245,158,11,0.08)'
              e.currentTarget.style.boxShadow = '0 0 18px rgba(245,158,11,0.35)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.boxShadow = '0 0 12px rgba(245,158,11,0.15)'
            }}
          >
            ↻ RESET
          </button>
        </div>
      </header>

      {/* ── Content row: main + ghost sidebar ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 }}>

        {/* left: cards + button + correlation */}
        <main style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          padding: '10px',
          overflow: 'hidden',
          minHeight: 0,
        }}>
          {/* stream cards */}
          <div style={{ flex: 5, display: 'flex', gap: '10px', overflow: 'hidden', minHeight: 0 }}>
            <StreamCard
              title="WATER SENSOR ARRAY"
              trust={water.trustScore}
              hist={waterHist}
              sparkKeys={['ph', 'turbidity', 'flowRate']}
              sparkRanges={[[2, 10], [0, 32], [0, 20]]}
              delayMs={0}
              metrics={<>
                <MetricRow label="pH Level"    value={water.ph}         unit="pH"    precision={2} />
                <MetricRow label="Turbidity"   value={water.turbidity}  unit="NTU"   precision={2} />
                <MetricRow label="Flow Rate"   value={water.flowRate}   unit="L/min" precision={1} />
                <MetricRow label="Trust Score" value={water.trustScore} unit="%"     precision={1} />
              </>}
            />
            <StreamCard
              title="SOIL SENSOR ARRAY"
              trust={soil.trustScore}
              hist={soilHist}
              sparkKeys={['moisture', 'nitrogen', 'salinity']}
              sparkRanges={[[25, 90], [120, 200], [0.5, 5.0]]}
              delayMs={400}
              metrics={<>
                <MetricRow label="Moisture"    value={soil.moisture}   unit="%"    precision={1} />
                <MetricRow label="Nitrogen"    value={soil.nitrogen}   unit="ppm"  precision={0} />
                <MetricRow label="Salinity"    value={soil.salinity}   unit="dS/m" precision={2} />
                <MetricRow label="Trust Score" value={soil.trustScore} unit="%"    precision={1} />
              </>}
            />
            <StreamCard
              title="COMMUNITY HEALTH NODES"
              trust={health.trustScore}
              hist={healthHist}
              sparkKeys={['malnutrition', 'diseaseIncidence', 'clinicVisits']}
              sparkRanges={[[0, 25], [0, 18], [30, 150]]}
              delayMs={800}
              metrics={<>
                <MetricRow label="Malnutrition Idx"  value={health.malnutrition}     unit="%"     precision={1} />
                <MetricRow label="Disease Incidence" value={health.diseaseIncidence}  unit="/1000" precision={1} />
                <MetricRow label="Clinic Visits"     value={health.clinicVisits}      unit="/week" precision={0} />
                <MetricRow label="Trust Score"       value={health.trustScore}        unit="%"     precision={1} />
              </>}
            />
          </div>

          {/* attack trigger */}
          <AttackButton active={isAttackActive} onAttack={handleAttack} />

          {/* correlation panel */}
          <div style={{ flex: 4, overflow: 'hidden', minHeight: 0 }}>
            <CorrelationPanel corr={corr} conf={conf} />
          </div>
        </main>

        {/* right: ghost sensor sidebar */}
        <GhostSidebar
          gwTriggered={gwTriggered}
          swTriggered={swTriggered}
          captureTime={captureTime}
        />

      </div>

      {/* ── Status Bar (fixed to bottom) ── */}
      <StatusBar 
        anomaly={minTrust < 90}
        isAttackActive={isAttackActive}
        isMuted={isMuted}
        onMuteToggle={() => setIsMuted(!isMuted)}
      />

      {/* ── Provenance Trace (slides up 12s after attack) ── */}
      {showProvenance && (
        <ProvenancePanel
          attackTimestamp={attackTimestamp}
          captureTime={captureTime}
        />
      )}

    </div>
  )
}
