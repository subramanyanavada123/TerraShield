# TerraShield Backend

**All data is simulated. No external APIs or hardware required.**

A Python Flask backend that powers TerraShield's real-time anomaly detection, causal chain reconstruction, and honeypot intrusion logging. Designed to demonstrate the full attack→detection→attribution pipeline in a self-contained prototype.

---

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Server runs on `http://localhost:5000`. The React frontend (in `../`) connects at this address.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flask API (app.py)                        │
│                      8 REST endpoints                        │
└─────────────────────────────────────────────────────────────┘
         ↑
    ┌────┴────┬────────┬──────────┬──────────┬────────────┐
    │          │        │          │          │            │
┌───v──┐  ┌──v──┐  ┌──v──┐  ┌───v─┐  ┌────v─┐  ┌────────v┐
│Sim   │  │Corr │  │Ghost│  │Prov │  │Buff  │  │ ML      │
│ulator│  │ rel │  │Sensor│ │enance│ │ buffer│ │ Model   │
└───┬──┘  └──┬──┘  └──┬──┘  └───┬─┘  └────┬─┘  └────────┬┘
    │         │        │         │        │               │
    └─────────┼────────┼─────────┼────────┴───────────────┘
              │
          ┌───v──────────────────┐
          │   SQLite Database    │
          │  (sensor_readings,   │
          │   anomaly_events,    │
          │   ghost_intrusions)  │
          └──────────────────────┘
```

### Modules

| Module | Purpose |
|--------|---------|
| **simulator.py** | 3 daemon threads generate water/soil/health readings every 2-3s with HMAC-256 signatures |
| **correlator.py** | Rolling Pearson correlations + hard-coded rules → anomaly confidence score |
| **ghost_sensors.py** | 9 honeypot endpoints that log intrusions silently, return HTTP 200 OK |
| **provenance.py** | HMAC tamper-check + causal chain reconstruction from anomaly → root cause |
| **buffer.py** | Simulates offline edge node: buffers readings when network is down, replays on reconnect |
| **ml_model.py** | LinearRegression crop-yield predictor with per-sensor attribution scores |
| **attacker_sim.py** | Auto-triggers ghost-sensor writes 4s and 6s after attack is injected |
| **database.py** | SQLite init + thread-local connection pool |
| **app.py** | Flask entry point, orchestration, 8 REST endpoints |

---

## REST Endpoints

### Sensor Readings

**`GET /api/streams`**
```json
{
  "ok": true,
  "water": { "ph": 7.5, "turbidity": 2.1, "flow_rate": 15.0, "trust_score": 99.0, ... },
  "soil": { "moisture": 45.0, "nitrogen": 160.0, "salinity": 1.1, "trust_score": 98.5, ... },
  "health": { "malnutrition_index": 5.5, "disease_incidence": 3.5, "clinic_visits": 50, ... },
  "attack_active": false,
  "timestamp": "2026-01-15T10:30:45.123Z"
}
```

### Cross-Domain Anomalies

**`GET /api/correlations`**
```json
{
  "ok": true,
  "water_soil_corr": 0.92,
  "soil_health_corr": 0.89,
  "water_health_corr": 0.91,
  "confidence": 2.0,
  "flagged_domains": [],
  "rules_violated": [],
  "attack_vector": null,
  "iso_score": 0.0,
  "timestamp": "2026-01-15T10:30:45.123Z"
}
```

### Ghost Sensors

**`GET /api/ghosts`**
```json
{
  "ok": true,
  "sensors": [
    {
      "sensor_id": "GW-GHOST-7a3f",
      "domain": "WATER",
      "label": "Groundwater Node",
      "status": "WATCHING",
      "triggered": false,
      "alert": null
    },
    ...
  ],
  "intrusions": [...],
  "decoys_active": "9/9",
  "intrusions_caught": 0,
  "real_sensors_protected": 24
}
```

### Provenance Chain

**`GET /api/provenance/trace`**

Optional query: `?health_spike_time=2026-01-15T10:30:00Z`

```json
{
  "ok": true,
  "chain": [
    {
      "step": 1,
      "event_type": "HEALTH ANOMALY DETECTED",
      "sensor_id": "H-890",
      "confidence": 2.0,
      "hmac_verified": true,
      ...
    },
    {
      "step": 2,
      "event_type": "SOIL STRESS CORRELATED",
      "sensor_id": "S-123",
      "values": { "salinity": 1.1, "moisture": 45.0 },
      "hmac_verified": true,
      ...
    },
    ...
  ],
  "chain_length": 5,
  "all_hmac_verified": true,
  "tamper_detected": false
}
```

### Attack Control

**`POST /api/attack/inject`**
```json
{
  "ok": true,
  "message": "⚡ Attack injected — sensor W-447 compromised",
  "attack_ts": "2026-01-15T10:30:45.123Z",
  "ghost_intrusions_scheduled": ["GW-GHOST-7a3f @ +4s", "SW-GHOST-2c91 @ +6s"]
}
```

**`POST /api/attack/reset`**
```json
{
  "ok": true,
  "message": "✓ System reset to nominal operation",
  "timestamp": "2026-01-15T10:30:50.456Z"
}
```

### System Status

**`GET /api/status`**
```json
{
  "ok": true,
  "status": "NOMINAL",
  "label": "ALL SYSTEMS NOMINAL",
  "confidence": 2.0,
  "intrusions_caught": 0,
  "attack_active": false,
  "uptime_s": 45.2
}
```

### ML Attribution

**`GET /api/attribution`**
```json
{
  "ok": true,
  "predicted_yield_index": 72.5,
  "yield_rating": "GOOD",
  "attributions": [
    {
      "sensor": "moisture",
      "domain": "soil",
      "value": 45.0,
      "coefficient_pct": 22.1,
      "influence": "HIGH",
      "trusted": true,
      "status": "TRUSTED"
    },
    ...
  ],
  "untrusted_sensors": [],
  "iso_anomaly": false
}
```

---

## Demo Sequence

### 1. Start the backend

```bash
python app.py
```

You'll see:
```
[DB] Initialised → /path/to/terrashield.db
[Simulator] ✓ 3 sensor streams active
[ML] CropYieldModel trained — R² on synthetic data ≈ 0.856
[App] ✓ All services started
[App] 🚀  TerraShield backend running on http://localhost:5000
```

### 2. Monitor normal operation

```bash
# Terminal 1: watch /api/streams
curl -s http://localhost:5000/api/streams | jq '.water.trust_score'

# Terminal 2: watch correlations
curl -s http://localhost:5000/api/correlations | jq '.confidence'
```

Values should stay stable:
- Trust scores: 97–100%
- Correlation confidence: 0–5%
- No flagged domains

### 3. Inject attack

```bash
curl -X POST http://localhost:5000/api/attack/inject
```

Watch the cascade unfold:

| Timeline | Event | Effect |
|----------|-------|--------|
| **+0s** | Water W-447 compromised (pH→3.2, turbidity→28) | Trust water → 12% |
| **+3s** | Soil senses over-irrigation (moisture→78%, salinity→3.8) | Trust soil → 34% |
| **+4s** | GW-GHOST-7a3f logs intrusion | Ghost status → INTRUSION DETECTED |
| **+6s** | SW-GHOST-2c91 logs lateral probe | Ghost count → 2 intrusions |
| **+10s** | Health metrics spike (malnutrition→19%, clinic→134) | Confidence → 94%, Status → CRITICAL |

### 4. Query provenance

```bash
curl -s http://localhost:5000/api/provenance/trace | jq '.chain[] | {step, event_type, hmac_verified}'
```

Returns the 5-step causal chain:
1. Health anomaly
2. Soil stress
3. Water compromise
4. Ghost intrusion
5. Root cause identified

### 5. Reset

```bash
curl -X POST http://localhost:5000/api/attack/reset
```

Everything returns to nominal.

---

## Offline Buffer Demo

Simulate network outage:

```bash
curl -X POST http://localhost:5000/simulate/network-drop
# Readings buffer locally (no SQLite writes)

sleep 30

curl -X POST http://localhost:5000/simulate/network-restore
# Buffered readings replayed, anomaly detection re-runs
```

---

## Database Schema

### `sensor_readings`
```
id, sensor_id, domain, timestamp, values_json, hmac_signature, region, is_ghost
```

Every reading signed with HMAC-SHA256. Signature verified on query.

### `anomaly_events`
```
id, timestamp, confidence, flagged_domains, correlation_scores_json, rules_violated
```

Persisted when confidence > 20.

### `ghost_intrusions`
```
id, ghost_id, timestamp, attacker_ip, attacker_fingerprint, payload
```

Logged on any POST to `/ghost/<sensor_id>/reading`.

---

## Design Highlights

### No External Dependencies
- SQLite: built-in (no separate database server)
- All data generated synthetically
- All ML models trained on synthetic data
- No API calls or hardware sensors

### Thread-Safe Streaming
- Simulator produces readings in parallel threads (2s, 2s, 3s intervals)
- Shared state protected by RLock
- Flask request threads read safely without blocking writes

### HMAC Tamper Detection
- Every reading signed with per-sensor secret key (512-bit)
- On provenance query, signatures re-verified
- Mismatch → "TAMPERED" flag in response

### Causality Pipeline
Anomaly confidence computed by:
```
confidence = min(94, num_violations * 18 + corr_drop * 40)
```

This combines:
- **Hard-coded rules** (agronomic physics)
- **Pearson correlations** (statistical association)
- **Isolation Forest** (unsupervised outlier detection)

### Demo Realism
- Attack doesn't instantly affect all streams (soil lags 3s, health lags 10s)
- Confidence climbs over time as evidence accumulates
- Ghost sensors fire at realistic times (4s, 6s)
- Provenance chain shows the full causal path

---

## Verification Checklist

- [x] All 8 endpoints return valid JSON
- [x] Attack inject + reset cycle works cleanly
- [x] HMAC verification works on provenance query
- [x] Ghost intrusion logged when attacker_sim runs
- [x] Correlation confidence climbs correctly during attack
- [x] Offline buffer buffers and replays readings
- [x] ML model attribution scores reflect agronomic relationships
- [x] Zero external dependencies

---

## Troubleshooting

**"Address already in use"** — Flask port 5000 is occupied:
```bash
lsof -i :5000
kill -9 <PID>
# or change PORT in app.py
```

**SQLite locked** — rare, but if you see it:
```bash
rm -f terrashield.db
# Restart app.py to reinitialise
```

**Ghost intrusions not logging** — ensure attacker_sim can reach Flask:
```bash
curl http://127.0.0.1:5000/ghost/GW-GHOST-7a3f/reading -X POST -H "Content-Type: application/json" -d '{"ph": 3.2}'
# Should return 200 OK
```

---

## Next Steps

To connect the React frontend:

1. Ensure Flask is running on `:5000`
2. React frontend already has CORS enabled
3. Frontend calls `/api/streams` every 2s (poll-friendly)
4. Frontend listens to status changes and triggers demo via `/api/attack/inject`

To extend the backend:

- Add more rules to `correlator.py`
- Train the ML model on real sensor data in `ml_model.py`
- Implement WebSocket for real-time push instead of polling
- Add authentication (JWT) to the Flask endpoints

---

**TerraShield Backend v1.0** — Secure, auditable, simulated sensor ecosystem.
