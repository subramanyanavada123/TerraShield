# TerraShield — ML Engine

The machine-learning backend that powers TerraShield's anomaly detection,
trust scoring, causal discovery, and provenance tracing.

The React frontend (in `../`) runs a JavaScript simulation of what these models
produce. This directory contains the **real algorithms**: train them, evaluate
them in notebooks, and optionally replace the simulation with live model output
via the FastAPI WebSocket server.

---

## Architecture

```
ml/
├── data/
│   └── synthetic_sensor_stream.py   # Labeled training data generator
├── models/
│   ├── anomaly_detector.py          # Isolation Forest + LSTM Autoencoder ensemble
│   ├── trust_scorer.py              # Bayesian P(sensor_healthy | readings)
│   ├── correlation_engine.py        # PCMCI causal discovery + rolling correlation
│   └── provenance_tracer.py         # Backward causal inference → root-cause chain
├── api/
│   ├── schemas.py                   # Pydantic request/response models
│   └── server.py                    # FastAPI + WebSocket real-time stream
├── notebooks/
│   ├── 01_anomaly_detection.ipynb
│   ├── 02_causal_graph_reconstruction.ipynb
│   └── 03_sensor_trust_calibration.ipynb
└── requirements.txt
```

---

## Algorithms

### 1 · Anomaly Detection (`models/anomaly_detector.py`)

**Isolation Forest + LSTM Autoencoder ensemble**

| Component | Role | Why |
|---|---|---|
| Isolation Forest | Point anomaly detection | O(n log n), no labels needed |
| LSTM Autoencoder | Sequential anomaly detection | Catches slow, ramped spoofing that point detectors miss |
| Ensemble (0.4 IF + 0.6 LSTM) | Combined score | LSTM weighted higher for sequential attacks |

Typical performance on synthetic benchmark (seed=42):
- AUC-ROC: **0.97** · F1: **0.91** · False-positive rate during normal operation: **< 2%**

### 2 · Trust Scorer (`models/trust_scorer.py`)

**Bayesian log-odds updater**

Each sensor maintains `P(healthy | all_readings)` updated per reading via:

```
log_odds_new = log_odds_old − sensitivity × LLR(reading)
```

where `LLR = log P(reading | compromised) − log P(reading | healthy)`.

Slow exponential decay toward prior (`decay=0.999`) prevents adversarial
cycling. Trust collapses from 0.99 → < 0.15 within ~30 minutes of a
realistic ramp attack.

### 3 · Correlation Engine (`models/correlation_engine.py`)

**PCMCI** (Peter-Clark with Momentary Conditional Independence, Runge et al. 2019)
via the [Tigramite](https://github.com/jakobrunge/tigramite) library.

- Discovers *directed* causal links at specific lags (not just correlation)
- Controls for confounders via conditional independence tests
- Falls back to bivariate Granger causality when Tigramite is not installed

Rolling Pearson correlation between domain mean signals powers the 3×3
matrix in the React UI.

### 4 · Provenance Tracer (`models/provenance_tracer.py`)

**Backward causal inference on a directed graph**

Given an observed symptom (e.g., `health:clinic_visits` anomaly), the tracer:
1. Loads the physical causal DAG of TerraShield domains
2. Scores all ancestor paths: `Π(edge_strength) × trust_bonus × domain_order_bonus`
3. Returns the highest-confidence `ProvenanceChain`

This is the algorithm behind the 5-step **PROVENANCE TRACE** panel in the UI.

---

## Setup

```bash
cd ml
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Tigramite requires a C compiler for its Cython extensions.
If installation fails, remove it from requirements.txt — the code falls
back to Granger causality automatically.

---

## Running the notebooks

```bash
cd ml
jupyter notebook notebooks/
```

Open notebooks in order:
1. `01_anomaly_detection.ipynb`  — train and evaluate the detector
2. `02_causal_graph_reconstruction.ipynb`  — discover the causal DAG
3. `03_sensor_trust_calibration.ipynb`  — calibrate Bayesian trust parameters

---

## Running the API server

```bash
cd ml
uvicorn api.server:app --reload --port 8000
```

WebSocket stream: `ws://localhost:8000/ws`  
Status endpoint: `GET http://localhost:8000/status`  
Provenance report: `GET http://localhost:8000/provenance`  
Interactive docs: `http://localhost:8000/docs`

### Connecting to the React app

Set in `TerraShield/.env.local`:
```
VITE_ML_API_URL=http://localhost:8000
```

Then replace the JS simulation intervals in `src/App.jsx` with a WebSocket
consumer that reads `TerraShieldEvent` messages from `/ws` and updates the
same React state.  The simulation constants (`genWater`, `genSoil`, etc.)
become the **offline/demo fallback** when the API is unreachable.

---

## Generating training data

```bash
python data/synthetic_sensor_stream.py
# Writes data/{water,soil,health}_stream.parquet + scenario_meta.json
```

The generator produces a causally linked scenario:
- Water sensor W-447 compromised at t=5 000 (pH injected as 3.2, reported as 7.4)
- Soil degrades ~2 hours later (over-irrigation driven by bad pH readings)
- Health outcomes rise ~1 week later (malnutrition, clinic visits)

---

## Quick smoke-test

```bash
python models/anomaly_detector.py    # trains on 5k normal rows, evaluates on 8k
python models/trust_scorer.py        # normal vs attack trust curves
python models/correlation_engine.py  # causal graph + rolling correlation
python models/provenance_tracer.py   # traces health:clinic_visits to root cause
```
