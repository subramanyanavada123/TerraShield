"""
TerraShield FastAPI backend.

Endpoints
---------
POST /ingest/{domain}   Receive a sensor reading; run trust + anomaly scoring
GET  /status            Current system trust state
GET  /provenance        Trigger provenance trace for the latest anomaly
GET  /health            Liveness probe
WS   /ws                Real-time event stream consumed by the React frontend

WebSocket protocol
------------------
  Server → Client: TerraShieldEvent JSON on every sensor update
  Client → Server: ignored (read-only stream)

Running
-------
  uvicorn api.server:app --reload --port 8000

Integration with React app
--------------------------
  Set VITE_ML_API_URL=http://localhost:8000 in TerraShield/.env.local
  Then replace the JS simulation engine with a WebSocket consumer that
  listens to /ws and updates the same React state the simulation currently drives.
"""

from __future__ import annotations

import asyncio
import sys
import os
import time
from datetime import datetime
from typing import Dict, List, Set

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    AnomalyAlert, CorrelationSnapshot, ProvenanceReportOut,
    ProvenanceStepOut, SensorReading, StatusResponse, TerraShieldEvent,
    TrustUpdate,
)
from models.correlation_engine import CrossDomainCorrelationEngine
from models.provenance_tracer import ProvenanceTracer
from models.trust_scorer import MultiSensorTrustMonitor

import numpy as np

# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TerraShield ML API",
    description=(
        "Real-time sensor integrity monitoring.\n\n"
        "Replaces the JavaScript simulation engine in the React frontend "
        "with genuine ML model output."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_start_time = time.time()

# ── Shared ML state ────────────────────────────────────────────────────────────

monitor = MultiSensorTrustMonitor()
for _domain in ("water", "soil", "health"):
    for _i in range(3):
        monitor.add_sensor(f"{_domain}_{_i}", _domain)

corr_engine  = CrossDomainCorrelationEngine()
prov_tracer  = ProvenanceTracer()
prov_tracer.load_physical_structure()

# Rolling reading buffers for correlation computation
_buffers: Dict[str, List[Dict]] = {"water": [], "soil": [], "health": []}
_BUFFER_LIMIT = 500

# Latest correlation snapshot
_latest_corr = CorrelationSnapshot(
    water_soil=0.92, water_health=0.89, soil_health=0.91,
    timestamp=datetime.utcnow(),
)

# Active WebSocket connections
_ws_pool: Set[WebSocket] = set()

# ── WebSocket helpers ──────────────────────────────────────────────────────────

async def _broadcast(event: TerraShieldEvent) -> None:
    msg  = event.model_dump_json()
    dead: Set[WebSocket] = set()
    for ws in _ws_pool:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    _ws_pool.difference_update(dead)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    _ws_pool.add(websocket)

    # Send current state on connect so the UI is immediately populated
    await websocket.send_text(TerraShieldEvent(
        event_type="trust_update",
        payload={"domain_trust": monitor.get_domain_trust()},
    ).model_dump_json())

    try:
        while True:
            await asyncio.sleep(20)
            await websocket.send_text('{"event_type":"ping","payload":{},"timestamp":"' +
                                      datetime.utcnow().isoformat() + '"}')
    except WebSocketDisconnect:
        _ws_pool.discard(websocket)


# ── REST endpoints ─────────────────────────────────────────────────────────────

@app.post("/ingest/{domain}", response_model=TrustUpdate)
async def ingest(domain: str, reading: SensorReading) -> TrustUpdate:
    """
    Ingest one sensor reading and run the full ML pipeline:

    1. Update Bayesian trust score for this sensor
    2. Compute domain-level trust aggregates
    3. Buffer reading for rolling correlation update
    4. Broadcast trust_update + optional anomaly alert via WebSocket
    """
    # ── 1. Trust update ──────────────────────────────────────────────────────
    sensor_trust = monitor.update_all({reading.sensor_id: reading.values}).get(
        reading.sensor_id, 1.0
    )
    domain_trust = monitor.get_domain_trust()

    trust_out = TrustUpdate(
        sensor_id=reading.sensor_id,
        domain=domain,
        sensor_trust=sensor_trust,
        domain_trust=domain_trust,
    )

    # ── 2. Buffer ─────────────────────────────────────────────────────────────
    buf = _buffers.setdefault(domain, [])
    buf.append({"values": reading.values, "ts": reading.timestamp.isoformat()})
    if len(buf) > _BUFFER_LIMIT:
        _buffers[domain] = buf[-_BUFFER_LIMIT:]

    # ── 3. Broadcast trust update ─────────────────────────────────────────────
    await _broadcast(TerraShieldEvent(
        event_type="trust_update",
        payload={
            "sensor_id":   reading.sensor_id,
            "domain":      domain,
            "sensor_trust": sensor_trust,
            "domain_trust": domain_trust,
        },
    ))

    # ── 4. Anomaly alert if trust drops significantly ──────────────────────────
    min_trust = min(domain_trust.values())
    if min_trust < 0.5:
        severity = "critical" if min_trust < 0.2 else "warning"
        await _broadcast(TerraShieldEvent(
            event_type="anomaly",
            payload=AnomalyAlert(
                sensor_id=reading.sensor_id,
                domain=domain,
                anomaly_score=round(1.0 - sensor_trust, 4),
                is_anomaly=True,
                severity=severity,
                timestamp=reading.timestamp,
            ).model_dump(),
        ))

    return trust_out


@app.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    return StatusResponse(
        domain_trust=monitor.get_domain_trust(),
        active_ws_clients=len(_ws_pool),
        buffer_sizes={k: len(v) for k, v in _buffers.items()},
        uptime_s=round(time.time() - _start_time, 1),
        timestamp=datetime.utcnow(),
    )


@app.get("/provenance", response_model=ProvenanceReportOut)
async def provenance() -> ProvenanceReportOut:
    """
    Trigger a provenance trace starting from 'health:clinic_visits'.

    In production this would be parameterised by the anomaly node and
    incorporate real anomaly-detector output.  Here it demonstrates the
    static physical causal structure.
    """
    # Register any low-trust sensors as evidence
    domain_colors = {"water": "#ef4444", "soil": "#f59e0b", "health": "#22c55e"}
    for sid, scorer in monitor.scorers.items():
        if scorer.current_trust < 0.5:
            prov_tracer.add_trust_drop(sid, scorer.current_trust)

    chain = prov_tracer.trace("health:clinic_visits")
    if chain is None:
        chain = prov_tracer.trace("health:malnutrition")

    if chain is None:
        return ProvenanceReportOut(
            chain_length=0, root_cause="unknown",
            cascade_duration_h=None, overall_confidence=0.0,
            detection_latency_s=0.0, steps=[],
        )

    steps = [
        ProvenanceStepOut(
            step=i + 1,
            node_id=n.node_id,
            domain=n.domain,
            event_type=n.event_type,
            title=n.node_id.replace(":", " ").upper(),
            confidence=round(n.confidence, 3),
            color=domain_colors.get(n.domain, "#9ca3af"),
            description=n.description,
            timestamp=n.timestamp,
        )
        for i, n in enumerate(chain.nodes)
    ]

    duration_h = (
        chain.cascade_duration.total_seconds() / 3600
        if chain.cascade_duration else None
    )

    return ProvenanceReportOut(
        chain_length=len(chain.nodes),
        root_cause=chain.root_cause.node_id,
        cascade_duration_h=round(duration_h, 1) if duration_h else None,
        overall_confidence=round(chain.overall_confidence, 3),
        detection_latency_s=chain.detection_latency_s,
        steps=steps,
    )


@app.get("/health")
async def health_check() -> Dict:
    return {"status": "ok", "version": "1.0.0", "uptime_s": round(time.time() - _start_time, 1)}


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
