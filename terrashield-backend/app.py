"""
TerraShield Backend — Flask entry point.

Starts all subsystems and exposes 8 REST endpoints for the React frontend:

  GET  /api/streams            latest sensor values + trust scores
  GET  /api/correlations       correlation matrix + confidence + flags
  GET  /api/ghosts             ghost sensor statuses + intrusion log
  GET  /api/provenance/trace   causal chain for latest health anomaly
  POST /api/attack/inject      trigger attack mode across all streams
  POST /api/attack/reset       reset everything to normal
  GET  /api/status             overall system status
  GET  /api/attribution        ML crop-yield attribution scores

Ghost honeypot routes (also served by this app):
  POST /ghost/<sensor_id>/reading

Offline simulation:
  POST /simulate/network-drop
  POST /simulate/network-restore

Run:
  python app.py
  → http://localhost:5000
"""

import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict

import schedule
from flask import Flask, jsonify, request
from flask_cors import CORS

# ── Subsystem imports ──────────────────────────────────────────────────────────
from database     import init_db
from simulator    import SimulatorEngine
from correlator   import CorrelationEngine
from ghost_sensors import create_blueprint, init_ghost_state, get_ghost_summary
from provenance   import build_trace
from buffer       import OfflineBuffer, BUFFER_MAX
from ml_model     import CropYieldModel
from attacker_sim import AttackerSimulator


# ── Flask app setup ────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=None)
CORS(app, resources={r"/*": {"origins": "*"}})


# ── Shared state ───────────────────────────────────────────────────────────────
# A single mutable dict shared across all subsystems.
# Protected by an RLock; individual keys are updated atomically.

_lock = threading.RLock()

STATE: Dict[str, Any] = {
    "lock":           _lock,
    "attack_active":  False,
    "attack_ts":      None,
    "network_offline": False,
    "offline_buffer": deque(maxlen=BUFFER_MAX),
    "latest": {
        "water":  None,
        "soil":   None,
        "health": None,
    },
    "windows": {
        "water":  deque(maxlen=20),
        "soil":   deque(maxlen=20),
        "health": deque(maxlen=20),
    },
    "correlation":     None,
    "ghost_events":    [],
    "ghost_statuses":  {},
    "started_at":      time.time(),
}


# ── Subsystem instances ────────────────────────────────────────────────────────

correlator  = CorrelationEngine(STATE)
simulator   = SimulatorEngine(STATE, on_reading=lambda d, r: _on_reading(d, r))
offline_buf = OfflineBuffer(STATE, correlator)
ml_model    = CropYieldModel()
attacker    = AttackerSimulator()


def _on_reading(domain: str, reading: Dict) -> None:
    """Called by the simulator after every new reading; triggers correlation."""
    correlator.compute()


# ── Schedule: run correlation every 2s even if readings pause ─────────────────

def _schedule_loop():
    schedule.every(2).seconds.do(correlator.compute)
    while True:
        schedule.run_pending()
        time.sleep(0.5)


# ── Response helpers ───────────────────────────────────────────────────────────

def _ok(data: Dict, status: int = 200):
    return jsonify({"ok": True, **data}), status


def _err(msg: str, status: int = 400):
    return jsonify({"ok": False, "error": msg}), status


# ── Default correlation (before first window is full) ─────────────────────────

_DEFAULT_CORR = {
    "water_soil_corr":   0.92,
    "soil_health_corr":  0.89,
    "water_health_corr": 0.91,
    "confidence":        2.0,
    "flagged_domains":   [],
    "rules_violated":    [],
    "attack_vector":     None,
    "iso_score":         0.0,
    "timestamp":         None,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/streams")
def streams():
    """
    Latest sensor values + trust scores for all three domains.
    Polled by the React frontend every 2 seconds.
    """
    w = STATE["latest"].get("water")  or _default_water()
    s = STATE["latest"].get("soil")   or _default_soil()
    h = STATE["latest"].get("health") or _default_health()

    return _ok({
        "water": {
            "ph":          round(w.get("ph", 7.5), 2),
            "turbidity":   round(w.get("turbidity", 2.1), 2),
            "flow_rate":   round(w.get("flow_rate", 15.0), 1),
            "trust_score": w.get("trust_score", 99.0),
            "sensor_id":   w.get("sensor_id", "W-447"),
            "timestamp":   w.get("timestamp", _now()),
        },
        "soil": {
            "moisture":    round(s.get("moisture", 45.0), 1),
            "nitrogen":    round(s.get("nitrogen", 160.0), 0),
            "salinity":    round(s.get("salinity", 1.1), 2),
            "trust_score": s.get("trust_score", 98.5),
            "sensor_id":   s.get("sensor_id", "S-123"),
            "timestamp":   s.get("timestamp", _now()),
        },
        "health": {
            "malnutrition_index": round(h.get("malnutrition_index", 5.5), 1),
            "disease_incidence":  round(h.get("disease_incidence", 3.5), 1),
            "clinic_visits":      int(h.get("clinic_visits", 50)),
            "trust_score":        h.get("trust_score", 99.5),
            "sensor_id":          h.get("sensor_id", "H-890"),
            "timestamp":          h.get("timestamp", _now()),
        },
        "attack_active": STATE["attack_active"],
        "timestamp":     _now(),
    })


@app.get("/api/correlations")
def correlations():
    """Current cross-domain correlation matrix, anomaly confidence, and flags."""
    corr = STATE.get("correlation") or dict(_DEFAULT_CORR)
    corr["timestamp"] = corr.get("timestamp") or _now()
    return _ok(corr)


@app.get("/api/ghosts")
def ghosts():
    """Ghost sensor network status and logged intrusion events."""
    return _ok(get_ghost_summary(STATE))


@app.get("/api/provenance/trace")
def provenance_trace():
    """
    Causal chain reconstruction for the latest (or queried) health anomaly.
    Optional query param: ?health_spike_time=<ISO-8601>
    """
    spike_time = request.args.get("health_spike_time")
    return _ok(build_trace(spike_time))


@app.post("/api/attack/inject")
def attack_inject():
    """
    Trigger attack mode.  All three streams switch to attack values.
    Also launches the attacker simulator thread to hit ghost sensors.
    """
    if STATE["attack_active"]:
        return _ok({"message": "Attack already active", "attack_ts": STATE["attack_ts"]})

    simulator.trigger_attack()
    attacker.start()

    return _ok({
        "message":    "⚡ Attack injected — sensor W-447 compromised",
        "attack_ts":  STATE["attack_ts"],
        "delays": {
            "water":  "immediate",
            "soil":   "3s",
            "health": "10s",
        },
        "ghost_intrusions_scheduled": ["GW-GHOST-7a3f @ +4s", "SW-GHOST-2c91 @ +6s"],
    })


@app.post("/api/attack/reset")
def attack_reset():
    """Reset all streams to normal. Clears ghost intrusions and correlation state."""
    simulator.reset()

    with STATE["lock"]:
        STATE["ghost_events"]    = []
        STATE["correlation"]     = None
        # Re-initialise ghost statuses to WATCHING
    init_ghost_state(STATE)

    return _ok({
        "message":    "✓ System reset to nominal operation",
        "timestamp":  _now(),
    })


@app.get("/api/status")
def status():
    """Overall system status: NOMINAL, ANOMALY, or CRITICAL."""
    corr       = STATE.get("correlation") or {}
    confidence = corr.get("confidence", 0.0)
    flagged    = corr.get("flagged_domains", [])
    intrusions = sum(1 for s in STATE["ghost_statuses"].values() if s.get("triggered"))

    if confidence >= 70 or intrusions >= 2:
        level, label = "CRITICAL", "CRITICAL — ROOT CAUSE IDENTIFIED"
    elif confidence >= 30 or intrusions >= 1:
        level, label = "ANOMALY", "ANOMALY DETECTED"
    else:
        level, label = "NOMINAL", "ALL SYSTEMS NOMINAL"

    return _ok({
        "status":              level,
        "label":               label,
        "confidence":          round(confidence, 2),
        "flagged_domains":     flagged,
        "intrusions_caught":   intrusions,
        "attack_active":       STATE["attack_active"],
        "network_offline":     STATE["network_offline"],
        "uptime_s":            round(time.time() - STATE["started_at"], 1),
        "timestamp":           _now(),
    })


@app.get("/api/attribution")
def attribution():
    """ML crop-yield attribution — which sensors drove the current prediction."""
    corr    = STATE.get("correlation") or {}
    flagged = corr.get("flagged_domains", [])
    return _ok(ml_model.predict(STATE, anomalous_domains=flagged))


# ── Offline simulation endpoints ──────────────────────────────────────────────

@app.post("/simulate/network-drop")
def network_drop():
    return _ok(offline_buf.go_offline())


@app.post("/simulate/network-restore")
def network_restore():
    return _ok(offline_buf.go_online())


# ── Ghost sensor honeypot routes (registered via Blueprint) ───────────────────

app.register_blueprint(create_blueprint(STATE))


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return _ok({"version": "1.0.0", "uptime_s": round(time.time() - STATE["started_at"], 1)})


# ── Default seed values (before simulator has produced a reading) ─────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _default_water():
    return {"ph": 7.5, "turbidity": 2.1, "flow_rate": 15.0,
            "trust_score": 99.0, "sensor_id": "W-447", "timestamp": _now()}

def _default_soil():
    return {"moisture": 45.0, "nitrogen": 160.0, "salinity": 1.1,
            "trust_score": 98.5, "sensor_id": "S-123", "timestamp": _now()}

def _default_health():
    return {"malnutrition_index": 5.5, "disease_incidence": 3.5, "clinic_visits": 50,
            "trust_score": 99.5, "sensor_id": "H-890", "timestamp": _now()}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STARTUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _start_background_services() -> None:
    init_db()
    init_ghost_state(STATE)
    simulator.start()

    sched_thread = threading.Thread(
        target=_schedule_loop, daemon=True, name="scheduler"
    )
    sched_thread.start()

    print("[App] ✓ All services started")
    print("[App]   Endpoints:")
    for rule in app.url_map.iter_rules():
        methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        print(f"         {methods:<6} {rule.rule}")


if __name__ == "__main__":
    _start_background_services()
    print("\n[App] 🚀  TerraShield backend running on http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True, use_reloader=False)
