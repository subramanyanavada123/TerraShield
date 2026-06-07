# TerraShield - Tri-Domain IoT Integrity Monitor with Analyst Dashboard

![Version](https://img.shields.io/badge/version-4.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![React](https://img.shields.io/badge/React-18.3+-blue)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![IEEE](https://img.shields.io/badge/IEEE-TIPPSS-gold)

A comprehensive cybersecurity visualization platform for detecting cross-domain sensor attacks in IoT networks. TerraShield provides two specialized interfaces (Agriculture Officer & Cybersecurity Analyst) with real-time cross-domain correlation anomaly detection, HMAC tamper verification, and forensic provenance tracing.

<video src="https://github.com/user-attachments/assets/0de0d0d1-7632-458f-9d7b-859eee8b0333" controls width="800">
  Your browser does not support the video tag.
</video>

**IEEE TIPPSS Framework Alignment**: Trust • Identity • Privacy • Protection • Safety • Security

---

## 🎯 The Problem We Solve

**Challenge**: Agricultural IoT systems have no cross-domain attack detection. A compromised water sensor could send false irrigation commands without detection because single-stream monitors can't see the relationship break.

**Solution**: TerraShield monitors the relationships BETWEEN domains:
- Water applies → soil moisture increases (expected)
- If water says "applied" but soil stays normal → likely attack
- Correlations drop, trust scores degrade, provenance traces root cause

---

## ✨ What's New in v4.0 - Complete Analyst Dashboard

### Major Changes from Previous Versions

#### **Two-Persona Architecture** ✅
- **Agriculture Officer**: Simplified map-based view, location monitoring, action recommendations
- **Cybersecurity Analyst**: Full technical dashboard with 7 analysis modes, tunable thresholds, forensic tools

#### **7 Analysis Modes for Analysts** ✅
```
OVERVIEW    - Dashboard with all panels at once
HEATMAP     - Correlation visualization + baseline statistics
LOGS        - Forensic audit log explorer with search/filters
CONFIG      - Threshold tuning panel + configuration changes log
STATS       - Regional baseline statistics + rule visualization
YIELD       - Crop yield ML attribution (feature importance)
RULES       - Advanced detection rule visualization with triggers
```

#### **New Dashboard Components** ✅

1. **Audit Log Explorer**
   - Searchable forensic logs of all sensor readings
   - Real-time signature verification (✓ Valid / ⚠ Unverified)
   - Expandable rows showing detailed anomaly analysis
   - Filter by sensor, anomaly status, date range
   - Mock data: Water, Soil, Health readings with HMAC verification

2. **Configuration Changes Log**
   - Admin action history (who changed what, when)
   - Track threshold updates, ghost deployments, detection toggles
   - Expandable rows showing old/new values + reason
   - Impact forecasts (FP rate, miss rate deltas)

3. **Regional Baseline Statistics**
   - 3-card display: Water, Soil, Health domains
   - Baseline metrics (pH 7.5±0.3, Moisture 32±2%, etc.)
   - Current values vs historical norms
   - Confidence percentages

4. **Correlation Heatmap**
   - Visual representation of W-S, W-H, S-H correlations
   - Color-coded by severity: Green (>0.8), Amber (0.5-0.8), Red (<0.5)
   - Gradient bars showing correlation coefficients
   - Updates in real-time (500ms intervals)

5. **Threshold Tuning Panel**
   - Dynamic slider controls for detection parameters:
     - Correlation Threshold (0.5-0.95)
     - Rate-of-Change Sensitivity (1.5-3.5 σ)
     - Time Window (1-24 hours)
   - Real-time impact preview (FP rate, miss rate)
   - Save/load presets

6. **Crop Yield Attribution**
   - ML feature importance display (R² = 0.87)
   - Sensor impact coefficients:
     - Soil Moisture: +58% importance
     - Water Quality: +42% importance
     - Health Index: -31% (inverse)
   - Prediction model info & disclaimers

7. **Ghost Sensor Deployment Panel**
   - Status dashboard: "3 Active Decoys | 12 Attack Attempts"
   - List of deployed honeypots with:
     - Region, field, sensor type
     - Active status indicator
     - Attack count & last attack timestamp
   - "+ DEPLOY" button to create new honeypots

8. **Advanced Rule Visualization**
   - List of active detection rules with:
     - Rule name & severity (RED/YELLOW)
     - Trigger count (last 7 days)
     - Visual severity indicator
   - Scrollable list with rule descriptions

#### **Real-Time API Integration** ✅
- **Weather**: Open-Meteo (temperature adjustments to water pH)
- **Seismic**: USGS Earthquake API (magnitude >4 = -25% trust, infrastructure alert)
- **Floods**: GDACS API (active floods = -30% water trust, contamination alert)
- All integrated into sensor readings with impact calculations

#### **Exclusive Scrolling** ✅
- Fixed viewport layout (position: fixed, 100vw × 100vh)
- Header stays at top (flexShrink: 0)
- Content area exclusive scroll (overflowY: auto)
- Status bar fixed at bottom
- No browser-level scrolling interference

#### **Light/Dark Theme - Complete Coverage** ✅
- THEMES object with dark & light palettes
- All new analyst components theme-aware
- Transitions on theme toggle (all 0.3s ease)
- Stored in localStorage

---

## Features Overview

### Core Monitoring
- **Real-time Sensor Streams** - Water, Soil, Health with 2-3s updates
- **Trust Score Analysis** - Individual domain trust (0-100%)
- **Sparkline Trends** - 20-point rolling history per metric
- **Cross-Domain Correlation** - 3×3 matrix with confidence scoring
- **5 Locations Monitored** - Madikeri, Somwarpet, Virajpet, Ponnampet, Kushalanagar (Karnataka)

### Attack Detection
- **Cross-Domain Anomaly Detection** - Pearson correlation with 20-point rolling window
- **Isolation Forest** - Bayesian anomaly detection
- **Ghost Sensor Network** - 9 cryptographic honeypots
- **Fingerprint Capture** - Attack signature + timestamp
- **Delayed Cascade Detection** - Water (0s), Soil (+3s), Health (+10s)

### Forensic Analysis
- **HMAC-SHA256 Signatures** - Tamper-evident readings
- **Provenance Trace** - 5-step causality chain reconstruction
- **Timeline Visualization** - Attack propagation steps
- **Forensic Log** - Immutable audit trail with chain verification
- **Export** - JSON reports for investigation

### Analyst Tools
- **7 Analysis Modes** - Overview, Heatmap, Logs, Config, Stats, Yield, Rules
- **Threshold Tuning** - Adjust detection sensitivity with impact preview
- **Configuration Audit** - Track all admin changes
- **False Alert Tracking** - FP rate calculation (falseAlerts/totalAlerts)
- **Geohazard Alerts** - Earthquake/flood integration with sensor impact

### Visual Polish
- **CRT Scanline Overlay** - Monitor aesthetic
- **Typewriter Effect** - Staggered component reveal
- **Pulsing Anomaly Border** - Red alert animation
- **Status Bar** - Dynamic warnings + mute toggle
- **Web Audio** - Beeps, pings, rumble effects
- **Responsive Design** - Desktop, tablet, mobile optimized

---

## Installation

### Prerequisites
- Node.js 16+
- npm or yarn
- Python 3.9+ (for backend, optional)

### Setup

```bash
# Clone repository
git clone https://github.com/subramanyanavada123/TerraShield.git
cd TerraShield/TerraShield

# Install frontend dependencies
npm install

# Start development server
npm run dev
```

App available at `http://localhost:5173/`

### Optional: Start Python Backend

```bash
cd terrashield-backend
pip install -r requirements.txt
python app.py
```

Backend available at `http://localhost:5000/`

---

## Usage Guide

### Demo Flow (Watch the Video)

**1. Page Load** (~2 seconds)
- Intro screen with TriKaal branding
- Click "ENTER SYSTEM" to start

**2. Agriculture Officer View** (Default)
- Simple location-based monitoring
- 3 sensor streams (Water, Soil, Health)
- Trust scores and sparklines
- "PROVENANCE" button for forensic trace
- Geohazard alerts (earthquakes, floods)

**3. Switch to Analyst View**
- Click **Persona Selector** → choose "ANALYST"
- See **7 Analysis Mode Tabs** at top:
  - **OVERVIEW**: Ghost sensors + heatmap + baseline + attribution
  - **HEATMAP**: Correlation visualization
  - **LOGS**: Forensic audit explorer
  - **CONFIG**: Threshold tuning + changes log
  - **STATS**: Baseline stats + rules
  - **YIELD**: Attribution calculator
  - **RULES**: Rule visualization

**4. Trigger Attack** (Click "⚡ ATTACK" Button)
- T=0s: Beep sequence, attack marker shows
- T=0-3s: Water sensor degrades
- T=3s: Water-Soil correlation breaks
- T=4s: Ghost sensor triggers (water intrusion) + PING sound
- T=6s: Lateral movement detected + PING sound
- T=8s: Health metrics spike
- T=10s: All domains flagged
- T=12s: Provenance panel slides up + RUMBLE sound
- T=12-20s: Causality chain reveals (5 nodes)
- T=20s+: Export button appears

**5. Explore Analyst Features**
- Click LOGS mode → search for specific sensor
- Click CONFIG mode → adjust threshold sliders
- Click HEATMAP → see correlation changes
- See baseline statistics update
- View rule triggers in RULES mode

**6. Reset**
- Click **"↻ RESET"** button
- All state returns to normal
- Ready for next demo

### Theme Toggle
- Click **🌙/☀️** (top-right) to switch Dark/Light
- All analyst dashboard components update theme

### Mute Audio
- Click **🔊/🔇** in status bar (bottom-right)
- All sound effects toggle

---

## Technical Architecture

### Frontend (React + Vite)

**Main Component**: `src/App.jsx` (3600+ lines)

#### State Variables (25+)
```javascript
// UI State
theme, showIntro, persona, isMuted, selectedLocation

// Sensor Readings
water, soil, health (with trust scores)
waterHist, soilHist, healthHist (sparkline data)

// Correlations
corr {ws, wh, sh}, conf (confidence), flaggedDomains

// Attack Tracking
isAttackActive, attackTimestamp, showProvenance

// Ghost Sensors
gwTriggered, swTriggered, captureTime

// Analyst Dashboard (NEW)
analysisMode (7 modes)
auditLog, ghostDeployments, thresholds
baselineStats, attributionData
correlationHistory, configLog
```

#### Components (30+)
- **UI**: Clock, PersonaSelector, LocationSelector, ThemeToggle, IntroScreen
- **Monitoring**: SensorMap, StreamCard, CorrelationPanel, SecurityStatus
- **Forensics**: ProvenanceQuery, ProvenancePanel, ResolveActions
- **Analyst Dashboard** (NEW):
  - AnalysisModeSelector, AuditLogExplorer, ConfigChangesLog
  - BaselineStatistics, CorrelationHeatmap, ThresholdTuningPanel
  - CropYieldAttribution, RuleVisualization, GhostSensorDeploymentPanel
- **Utility**: TIPPSSBadge, MetricRow, TrustBar, Sparkline, StatusBar

#### Styling System
- **THEMES object** with dark/light palettes (colors.bg, .cardBg, .border, .text, .accent, etc.)
- **Inline styles** (React style props)
- **CSS animations** in index.css (blink, pulse-dot, scanline, typewriter, etc.)
- **Responsive** media queries (@media max-width: 1024px, 768px, 480px)

#### Real-Time Updates
- **useEffect loops** with setInterval:
  - Water tick: 2s (sensor update)
  - Soil tick: 2s (sensor update)
  - Health tick: 3s (sensor update)
  - Correlation tick: 80ms (LERP smooth)
  - API fetch: 30s (weather/seismic/flood)

### Backend (Python Flask)

**Location**: `terrashield-backend/app.py`

#### REST Endpoints
```
GET  /api/streams              - Current readings
GET  /api/correlations         - 3×3 matrix + confidence
GET  /api/ghosts               - Honeypot statuses
GET  /api/provenance/trace     - 5-node causality chain
GET  /api/status               - System status
GET  /api/attribution          - ML coefficients
POST /api/attack/inject        - Trigger attack
POST /api/attack/reset         - Reset state
```

#### Supporting Modules
- **simulator.py** - Sensor data generation
- **correlator.py** - Pearson correlation calculation
- **ghost_sensors.py** - Honeypot endpoint logic
- **provenance.py** - Causality chain reconstruction
- **ml_model.py** - Linear regression for attribution
- **attacker_sim.py** - Attack cascade simulation
- **buffer.py** - Offline resilience buffering

---

## How It Works - Technical Flow

### 1. Normal Operation
```
Sensor Generator (genWater, genSoil, genHealth)
    ↓
Real-time values in state (water, soil, health)
    ↓
React re-render with new values
    ↓
Sparklines update (20-point rolling history)
    ↓
Trust scores calculated based on values
    ↓
Display to user (Stream cards + metric rows)
```

### 2. Correlation Monitoring (80ms loop)
```
Get water_hist, soil_hist, health_hist
    ↓
Calculate Pearson correlation (3 pairs)
    ↓
Compare to baseline (0.92, 0.89, 0.91)
    ↓
LERP smooth the values (smoothing factor 0.12)
    ↓
Update corr state: {ws, wh, sh}
    ↓
Compute confidence score based on deviation
    ↓
If confidence > 30%: flag anomaly
```

### 3. Attack Cascade (Timeline)
```
T=0s   : User clicks ATTACK button → setIsAttackActive(true)
         Beep sequence plays
         
T=0-3s : genWater(true) returns degraded values
         Trust score: 99% → 12%
         
T=3s   : genSoil(true) returns degraded values
         Water-Soil correlation drops: 0.92 → 0.32
         
T=4s   : Ghost water sensor triggered
         setGwTriggered(true)
         Ping sound plays
         
T=6s   : Ghost soil sensor triggered
         setSwTriggered(true)
         Ping sound plays
         
T=8s+  : genHealth(true) returns degraded values
         Health trust drops
         
T=12s  : Confidence > 90%
         setShowProvenance(true)
         Panel slides up (CSS animation)
         Rumble sound plays
         
T=12-20s: Timeline steps reveal (step-reveal animation)

T=20s+ : Export button appears
```

### 4. Forensic Provenance Trace
```
Attack detected at T=12s
    ↓
Provenance module reconstructs 5-step chain:
  1. Health Anomaly Detected (malnutrition spike)
  2. Crop Yield Failure (agricultural correlation drop)
  3. Irrigation Model Corruption (soil moisture overload)
  4. Poisoned Sensor Identified (water sensor W-447)
  5. Root Cause Resolved (causality chain complete)
    ↓
Display timeline with node reveals (staggered 500ms)
    ↓
User can export JSON report
```

### 5. Analyst Dashboard
```
User clicks Persona Selector → 'analyst'
    ↓
analysisMode = 'overview' (default)
    ↓
Show AnalysisModeSelector with 7 tabs
    ↓
User clicks tab (e.g., 'heatmap')
    ↓
setAnalysisMode('heatmap')
    ↓
Render: CorrelationHeatmap + BaselineStatistics
    ↓
In 'logs' mode:
  - Show AuditLogExplorer
  - User types in search box → filter results
  - User clicks row → expandedId state toggles
  - Expanded row shows details
    ↓
In 'config' mode:
  - Show ThresholdTuningPanel (sliders)
  - User adjusts slider → setThresholds({...})
  - Show ConfigChangesLog (admin history)
```

---

## Real-Time API Integration

### Weather (Open-Meteo)
```javascript
fetchLiveWeatherData(lat, lon)
  → Returns: {temperature, humidity, rainfall, windSpeed}
  → Adjust water pH based on temperature
  → Show in weather widget
```

### Seismic (USGS)
```javascript
fetchSeismicData(lat, lon)
  → Returns: {maxMagnitude, risk, timestamp, eventCount}
  → If magnitude > 4.0:
    - Apply -25% trust penalty to water
    - Show red alert: "🔴 SEISMIC ACTIVITY"
    - Display magnitude + risk level
```

### Floods (GDACS)
```javascript
fetchFloodWarnings(lat, lon)
  → Returns: {hasActiveFlood, floodAlerts, severity}
  → If hasActiveFlood:
    - Apply -30% trust to water
    - Apply +8 turbidity
    - Apply +15 soil moisture
    - Show alert with impact description
```

---

## Geohazard Integration

When earthquakes >4.0 magnitude or active floods detected:

```
Geohazard Alert Panel appears:
├─ SEISMIC ACTIVITY (if magnitude > 4.0)
│  └─ Magnitude: X.X | Risk: High | Impact: Infrastructure check needed
├─ FLOOD WARNING (if hasActiveFlood)
│  └─ Alerts: 3 | Severity: Extreme | Impact: Contamination risk
└─ Background: Red alert styling (#ef4444 border)
```

Sensor adjustments:
- **Water**: -25% trust (seismic), -30% trust (flood), +8 turbidity (flood)
- **Soil**: Normal (no direct impact)
- **Health**: -15% trust (flood, indirect water contamination)

---

## False Alert Tracking

```javascript
When user marks alert as false:
  → Click "False Alert" button in ResolveActions
  → setFalseAlerts(falseAlerts + 1)
  → setTotalAlerts(totalAlerts + 1)
  
Dashboard displays:
  → FALSE POSITIVE RATE: {falseAlerts}/{totalAlerts} ({percentage}%)
  → Example: 2/15 (13.3%)
  
Analyst can review in CONFIG mode to adjust thresholds
```

---

## Data Validation (HMAC Signatures)

Every sensor reading in audit log shows signature status:

```javascript
✓ Valid    - HMAC matches, reading trusted
⚠ Unverif  - Signature missing or unverified (ghost sensor)
✗ Invalid  - HMAC mismatch, likely tampered
```

Signature verification in forensic logs:
```
Reading: Water#42 = 88.5ppm
HMAC: 5a7f8c2b9e... (✓ valid)
Signer: water-belgaum-field7-42
Chain Verified: ✓ Yes
```

---

## Scrolling Architecture (v4.0 Fix)

### Fixed Viewport Layout
```
<div style={{
  position: 'fixed',
  top: 0, left: 0,
  width: '100vw',
  height: '100vh',
  overflow: 'hidden',  // Prevent browser scrolling
  display: 'flex',
  flexDirection: 'column'
}}>
  <header />  {/* flexShrink: 0 - stays at top */}
  
  <div style={{
    flex: 1,
    overflowY: 'scroll',  // EXCLUSIVE scrolling here
    height: 'calc(100vh - 40px)'
  }}>
    {/* All content - analyst dashboard panels, cards, etc. */}
  </div>
  
  <footer />  {/* Fixed at bottom */}
</div>
```

**Result**: Only content scrolls, header and footer stay fixed. No browser-level scrolling.

---

## Project Structure

```
TerraShield/
├── src/
│   ├── App.jsx              # Main 3600+ line component
│   ├── api.js               # API fetch wrappers
│   ├── useBackend.js        # Custom hooks for backend
│   ├── index.css            # Global styles, animations, media queries
│   └── main.jsx             # React entry point
├── public/
│   └── index.html           # HTML template
├── terrashield-backend/
│   ├── app.py               # Flask API server
│   ├── simulator.py         # Sensor generation
│   ├── correlator.py        # Correlation math
│   ├── ghost_sensors.py     # Honeypot logic
│   ├── provenance.py        # Causality chain
│   ├── ml_model.py          # ML attribution
│   ├── attacker_sim.py      # Attack cascade
│   ├── buffer.py            # Offline buffering
│   └── requirements.txt     # Python dependencies
├── vite.config.js           # Vite configuration
├── package.json             # Frontend dependencies
├── README.md                # This file
└── .gitignore              # Git exclusions
```

---

## Browser Support

- ✅ Chrome/Chromium 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

Web Audio API supported in all. Graceful degradation if unavailable.

---

## Performance

- **Frame Rate**: 60 FPS (60ms animations)
- **Bundle Size**: ~250KB gzipped
- **Initial Load**: <1s (Vite optimized)
- **Memory**: ~80MB runtime

---

## Version History

### v4.0 (Current) - Complete Analyst Dashboard
- 7 analysis modes with dedicated components
- Audit log explorer with search/filters
- Configuration changes log
- Baseline statistics cards
- Correlation heatmap visualization
- Threshold tuning panel with sliders
- Crop yield attribution display
- Ghost sensor deployment panel
- Advanced rule visualization
- Real-time API integration (weather, seismic, floods)
- Geohazard alerts with sensor impact
- Fixed viewport exclusive scrolling
- Light/Dark theme complete coverage
- False alert tracking metrics

### v3.0 - Visual Polish
- CRT scanline overlay
- Typewriter effect
- Pulsing anomaly border
- Fixed status bar
- Web Audio API sounds
- Mute toggle

### v2.0
- Cross-domain correlation
- Ghost sensors
- Provenance trace
- Attack fingerprinting

### v1.0
- Initial 3-stream monitoring
- Real-time data
- Trust scores
- Sparkline trends

---

## Known Limitations

- Single-user interface (no multi-user)
- Simulated sensor data (not real IoT)
- Hard-coded attack scenario (not real forensics)
- Audio requires user gesture for autoplay
- Mobile optimizations limited (designed for desktop)

---

## Future Enhancements

- Real sensor data integration
- Actual forensic log parsing
- Multi-scenario support
- Keyboard shortcuts
- Settings panel
- Export to PDF/JSON
- Multi-attack simulation
- Enhanced mobile support
- Backend API endpoints for analyst features

---

## IEEE TIPPSS Framework Alignment

| Principle | Implementation | Status |
|-----------|---|---|
| **T**rust | Score-based access control, confidence metrics | ✅ |
| **I**dentity | Sensor ID tracking, location identification | ✅ |
| **P**rivacy | Encryption status display, anonymization | ✅ |
| **P**rotection | Anomaly detection, rule-based filtering | ✅ |
| **S**afety | Cross-domain correlation, constraint validation | ✅ |
| **S**ecurity | HMAC signatures, provenance logs, audit trails | ✅ |

---

## Contributing

### Feature Branch Workflow

```bash
git checkout -b feature/your-feature-name
# Make changes
git add .
git commit -m "feat: description"
git push origin feature/your-feature-name
# Create Pull Request
```

### Commit Message Format
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Formatting
- `refactor:` - Code restructure
- `perf:` - Performance
- `test:` - Tests
- `chore:` - Build/deps

---

## License

MIT License - See LICENSE file

---

## Author

Created for IEEE SA Cybersecurity Hackathon 2026: "TIPPSS & Tricks: Hack the Threat"

---

## Support

For issues or questions:
1. Check existing GitHub issues
2. Create new issue with details
3. Include browser/OS info
4. Provide reproduction steps

---

**Status**: Production Ready for Hackathon  
**Last Updated**: June 6, 2026  
**Repository**: https://github.com/subramanyanavada123/TerraShield
