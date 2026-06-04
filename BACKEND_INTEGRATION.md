# TerraShield Frontend-Backend Integration Guide

## Summary of Changes

### ✅ COMPLETED: Mobile UI Responsive Design
- **Issue**: Mobile UI was broken - sidebar (280px) took up entire viewport, content cramped and unreadable
- **Solution**: Added responsive CSS media queries for three breakpoints
  - `@media (max-width: 1024px)` - Tablet sizing
  - `@media (max-width: 768px)` - Mobile layout (sidebar hidden, cards stack vertically)
  - `@media (max-width: 480px)` - Small phone optimization
- **Result**: App now displays correctly on all device sizes

### 🆕 CREATED: Backend Integration Infrastructure
Two new integration files have been created:

#### 1. `/src/api.js` - API Service Layer
- Centralized API client for all backend communication
- Endpoints mapped:
  - `getStreams()` → GET `/api/streams`
  - `getCorrelations()` → GET `/api/correlations`
  - `getGhosts()` → GET `/api/ghosts`
  - `getProvenance()` → GET `/api/provenance/trace`
  - `injectAttack()` → POST `/api/attack/inject`
  - `resetAttack()` → POST `/api/attack/reset`
  - `getStatus()` → GET `/api/status`
  - `getAttribution()` → GET `/api/attribution`
  - `healthCheck()` → GET `/health`
- Error handling with detailed APIError class
- Data transformation from backend format to frontend format

#### 2. `/src/useBackend.js` - Custom React Hooks
- `useBackendData()` - Manages all data polling from backend
  - Auto-detects backend availability
  - Falls back to local defaults if backend unavailable
  - Polls streams every 2s
  - Polls correlations every 500ms (frequent updates)
  - Polls ghosts every 1s
  - Polls status every 1s
- `useBackendActions()` - Manages attack/reset operations
  - `handleAttack()` - Calls `/api/attack/inject`
  - `handleReset()` - Calls `/api/attack/reset`

---

## Next Steps to Complete Integration

### Step 1: Update App.jsx to Use Backend Hooks

Replace the current local generation and state management with the backend hooks:

```jsx
import { useBackendData, useBackendActions } from './useBackend'

export default function App() {
  // Replace local generation with backend data
  const backendData = useBackendData()
  const actions = useBackendActions()
  
  // Use backendData properties instead of local state
  const [water, setWater] = useState(backendData.water)
  const [soil, setSoil] = useState(backendData.soil)
  const [health, setHealth] = useState(backendData.health)
  const [corr, setCorr] = useState(backendData.corr)
  
  // Remove the current useEffect loops for local generation
  // Remove handleAttack and handleReset implementations
  // Use actions.handleAttack and actions.handleReset instead
}
```

### Step 2: Update History Management

Modify history tracking to work with backend data:

```jsx
// Wrap data updates with history push
useEffect(() => {
  if (backendData.water) {
    setWaterHist(h => pushHistory(h, backendData.water))
  }
}, [backendData.water])
```

### Step 3: Update Ghost Sensor Rendering

Use ghost data from backend:

```jsx
// Replace GHOST_SENSORS array with dynamic data from backendData.ghosts
{backendData.ghosts.statuses.map((sensor, i) => (
  <SensorRow
    key={sensor.id}
    sensor={sensor}
    index={i}
    isIntrusion={sensor.status === 'intrusion'}
    isLateral={sensor.status === 'lateral'}
    captureTime={/* map from events */}
  />
))}
```

### Step 4: Update Provenance Panel

Load actual provenance trace from backend:

```jsx
useEffect(() => {
  if (backendData.isAttackActive) {
    API.getProvenance().then(data => {
      // Transform and render STEPS based on data.trace
      setProvenance(data)
    })
  }
}, [backendData.isAttackActive])
```

---

## Architecture After Integration

```
Frontend (React)
├── src/App.jsx (UI Components)
├── src/api.js (API Layer)
├── src/useBackend.js (Data Management)
└── src/index.css (Responsive Styling)
        ↓
    HTTP Requests
        ↓
Backend (Flask @ localhost:5000)
├── app.py (REST API)
├── simulator.py (Data Generation)
├── correlator.py (Anomaly Detection)
├── ghost_sensors.py (Honeypot Logging)
├── provenance.py (Causal Chain)
└── database.py (Persistence)
```

---

## Configuration

### Backend URL
Currently set to `http://localhost:5000/api` in `src/api.js`

To change backend URL, update:
```javascript
const API_BASE = 'http://localhost:5000/api'
```

### CORS
Backend is configured with CORS for `*` origins. No additional frontend configuration needed.

---

## Testing the Integration

### 1. Start Backend
```bash
cd terrashield-backend
pip install -r requirements.txt
python app.py
```
Server runs at `http://localhost:5000`

### 2. Start Frontend
```bash
npm run dev
```
Frontend at `http://localhost:5173`

### 3. Monitor Logs
Frontend console will show:
```
✓ TerraShield Backend connected (localhost:5000)
```

If backend is unavailable:
```
⚠ TerraShield Backend unavailable, using local simulation
```

---

## Migration Path

### Phase 1 (Current)
✅ Mobile UI responsive design complete
✅ Backend API infrastructure ready
⏳ Frontend still uses local generation

### Phase 2 (Next)
- Update App.jsx to use `useBackendData()` hook
- Replace local state management with backend polling
- Keep UI components unchanged (backward compatible)

### Phase 3 (Polish)
- Remove old generation functions (`genWater`, `genSoil`, etc.)
- Optimize polling intervals
- Add offline mode toggle
- Cache responses for offline support

---

## Benefits of Backend Integration

1. **Real-time Data**: Sensor data comes from live backend simulation
2. **Shared State**: Multiple frontends can connect to single backend
3. **Scalability**: Backend can be replaced with real IoT infrastructure
4. **Persistence**: Attack events and anomalies saved to database
5. **ML Attribution**: Backend computes crop yield impact
6. **Reproducibility**: Same backend state across sessions

---

## Notes

- Backend is still in **offline simulation mode** (no real IoT hardware)
- All data is generated by backend's `SimulatorEngine`
- Attack sequences are orchestrated by backend
- Frontend only displays backend state
- This is a complete prototype-to-production pipeline

---

**Status**: Mobile UI ✅ | Backend Infra ✅ | App Integration ⏳

**Last Updated**: 2026-06-04
