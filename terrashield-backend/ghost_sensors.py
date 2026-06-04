"""
Ghost Sensor Network — cryptographic honeypot layer.

Nine ghost sensors (3 per domain) accept inbound POST requests at
  POST /ghost/<sensor_id>/reading

Any write to a ghost endpoint:
  • Logs the intrusion with attacker IP, timestamp, and payload
  • Generates a SHA-256 fingerprint of (payload + timestamp)
  • Stores the event in the ghost_intrusions SQLite table
  • Pushes an alert to the shared-state alert queue
  • Returns HTTP 200 OK  (attacker must NOT know it's a honeypot)

A Flask Blueprint is returned by ``create_blueprint(state)`` and registered
on the main Flask app.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict

from flask import Blueprint, request, jsonify

from database import get_conn

# ── Ghost sensor registry ──────────────────────────────────────────────────────

GHOST_SENSORS = {
    # id → {domain, label}
    "GW-GHOST-7a3f": {"domain": "WATER",  "label": "Groundwater Node"},
    "SW-GHOST-2c91": {"domain": "WATER",  "label": "Surface Water"},
    "RW-GHOST-b44e": {"domain": "WATER",  "label": "Rainfall Monitor"},
    "SM-GHOST-9d12": {"domain": "SOIL",   "label": "Soil Moisture A"},
    "SN-GHOST-4f87": {"domain": "SOIL",   "label": "Nitrate Probe"},
    "SC-GHOST-1e55": {"domain": "SOIL",   "label": "Salinity Check"},
    "HN-GHOST-8b23": {"domain": "HEALTH", "label": "Health Node Alpha"},
    "HC-GHOST-3a67": {"domain": "HEALTH", "label": "Clinic Reporter"},
    "HM-GHOST-6c90": {"domain": "HEALTH", "label": "Malnutrition Tracker"},
}

# Intrusion event codes (returned in alerts)
STATUS_WATCHING           = "WATCHING"
STATUS_INTRUSION          = "INTRUSION DETECTED"
STATUS_LATERAL            = "LATERAL PROBE DETECTED"


def _fingerprint(payload: str, timestamp: str) -> str:
    """SHA-256 fingerprint of payload + timestamp."""
    raw = f"{payload}:{timestamp}".encode()
    return hashlib.sha256(raw).hexdigest()


# ── Blueprint factory ──────────────────────────────────────────────────────────

def create_blueprint(state: Dict) -> Blueprint:
    """
    Build and return the Flask Blueprint for all ghost-sensor routes.

    Args:
        state: Shared app state dict (owned by app.py)
    """
    bp = Blueprint("ghost", __name__)

    @bp.route("/ghost/<sensor_id>/reading", methods=["POST"])
    def ghost_reading(sensor_id: str):
        """
        Honeypot endpoint.  Returns 200 OK regardless — attacker must not
        know they've hit a decoy.  Logs everything silently.
        """
        if sensor_id not in GHOST_SENSORS:
            # Unknown sensor: still return 200 to avoid leaking info
            return jsonify({"status": "ok"}), 200

        ts          = datetime.now(timezone.utc).isoformat()
        raw_payload = request.get_data(as_text=True) or "{}"
        attacker_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
        fingerprint = _fingerprint(raw_payload, ts)

        # Parse payload best-effort
        try:
            payload_dict = json.loads(raw_payload)
        except json.JSONDecodeError:
            payload_dict = {"raw": raw_payload}

        # ── Persist intrusion event ───────────────────────────────────────────
        try:
            conn = get_conn()
            conn.execute(
                "INSERT INTO ghost_intrusions "
                "(ghost_id, timestamp, attacker_ip, attacker_fingerprint, payload) "
                "VALUES (?, ?, ?, ?, ?)",
                (sensor_id, ts, attacker_ip, fingerprint, raw_payload),
            )
            conn.commit()
        except Exception as exc:
            print(f"[Ghost] DB error logging intrusion: {exc}")

        # ── Determine status label ────────────────────────────────────────────
        meta   = GHOST_SENSORS[sensor_id]
        status = STATUS_INTRUSION if sensor_id == "GW-GHOST-7a3f" else STATUS_LATERAL

        # ── Build alert dict ──────────────────────────────────────────────────
        alert = {
            "sensor_id":   sensor_id,
            "domain":      meta["domain"],
            "label":       meta["label"],
            "status":      status,
            "timestamp":   ts,
            "attacker_ip": attacker_ip,
            "fingerprint": fingerprint,
            "write_attempt": _describe_attempt(payload_dict),
            "validated_sensor": "W-447" if meta["domain"] == "WATER" else None,
        }

        # ── Update shared state ───────────────────────────────────────────────
        with state["lock"]:
            state["ghost_events"].append(alert)
            if sensor_id in state["ghost_statuses"]:
                state["ghost_statuses"][sensor_id]["status"]    = status
                state["ghost_statuses"][sensor_id]["triggered"] = True
                state["ghost_statuses"][sensor_id]["alert"]     = alert

        print(
            f"[Ghost] ⚠  Intrusion on {sensor_id} "
            f"from {attacker_ip}  fp={fingerprint[:12]}…"
        )

        # Return 200 OK — honeypot doesn't reveal itself
        return jsonify({"status": "ok"}), 200

    return bp


# ── State initialiser ─────────────────────────────────────────────────────────

def init_ghost_state(state: Dict) -> None:
    """
    Populate the shared-state ghost_statuses dict with default WATCHING entries.
    Called by app.py during startup.
    """
    with state["lock"]:
        state["ghost_statuses"] = {
            sid: {
                "sensor_id": sid,
                "domain":    meta["domain"],
                "label":     meta["label"],
                "status":    STATUS_WATCHING,
                "triggered": False,
                "alert":     None,
            }
            for sid, meta in GHOST_SENSORS.items()
        }


# ── Payload interpretation ─────────────────────────────────────────────────────

def _describe_attempt(payload: Dict) -> str:
    """Generate a human-readable description of what the attacker tried to write."""
    if "ph" in payload:
        return f"pH value injection (value: {payload['ph']})"
    if "turbidity" in payload:
        return f"Turbidity injection (value: {payload['turbidity']})"
    if "moisture" in payload:
        return f"Moisture reading injection (value: {payload['moisture']})"
    keys = list(payload.keys())[:3]
    return f"Metric injection — fields: {', '.join(keys)}" if keys else "Unknown write attempt"


# ── Summary helper (used by /api/ghosts endpoint) ─────────────────────────────

def get_ghost_summary(state: Dict) -> Dict:
    """Return the full ghost network snapshot for the API response."""
    intrusions_caught = sum(
        1 for s in state["ghost_statuses"].values() if s["triggered"]
    )
    return {
        "sensors":         list(state["ghost_statuses"].values()),
        "intrusions":      list(state["ghost_events"]),
        "decoys_active":   f"{len(GHOST_SENSORS)}/{len(GHOST_SENSORS)}",
        "intrusions_caught": intrusions_caught,
        "real_sensors_protected": 24,
    }
