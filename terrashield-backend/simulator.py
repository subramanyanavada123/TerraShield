"""
IoT sensor stream simulation engine.

Three background daemon threads generate realistic sensor readings:
  water_stream  → every 2 seconds   (sensor W-447)
  soil_stream   → every 2 seconds   (sensor S-123)
  health_stream → every 3 seconds   (sensor H-890)

Each reading is:
  1. Generated with small Gaussian jitter around the expected value
  2. Signed with HMAC-SHA256 using a per-sensor secret key
  3. Written to the SQLite sensor_readings table
  4. Published to the shared state for the correlation engine

Attack mode:
  water  → immediate shift to attack values
  soil   → shifts after a 3-second delay
  health → shifts after a 10-second delay
"""

import hashlib
import hmac
import json
import random
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from database import get_conn

# ── Per-sensor HMAC secret keys ───────────────────────────────────────────────
# In production these would come from a hardware security module or vault.

SENSOR_KEYS: Dict[str, bytes] = {
    "W-447": b"ts-water-w447-xK9mP2qR",
    "S-123": b"ts-soil-s123-nL7vW4jY",
    "H-890": b"ts-health-h890-zB5cT8fA",
}


# ── HMAC helpers ──────────────────────────────────────────────────────────────

def sign_reading(sensor_id: str, timestamp: str, values: Dict) -> str:
    """Return HMAC-SHA256 hex digest for a sensor reading."""
    key = SENSOR_KEYS.get(sensor_id, b"ts-default-secret")
    msg = f"{sensor_id}|{timestamp}|{json.dumps(values, sort_keys=True)}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_reading(sensor_id: str, timestamp: str, values: Dict, signature: str) -> bool:
    """Return True if signature matches the re-computed HMAC."""
    expected = sign_reading(sensor_id, timestamp, values)
    return hmac.compare_digest(expected, signature)


# ── Value generation helpers ──────────────────────────────────────────────────

def _j(val: float, pct: float = 0.018) -> float:
    """Add ±pct Gaussian noise, relative to |val|."""
    return val + random.gauss(0, abs(val) * pct + 1e-6)


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


# ── Trust score helper (shared with correlator) ───────────────────────────────

NORMAL_RANGES = {
    "water": {
        "ph": (6.5, 8.5),
        "turbidity": (0.1, 4.0),
        "flow_rate": (12.0, 18.0),
    },
    "soil": {
        "moisture": (35.0, 55.0),
        "nitrogen": (140.0, 180.0),
        "salinity": (0.8, 1.4),
    },
    "health": {
        "malnutrition_index": (4.0, 7.0),
        "disease_incidence": (2.0, 5.0),
        "clinic_visits": (40.0, 60.0),
    },
}

ATTACK_TRUST_FLOOR = {"water": 12.0, "soil": 34.0, "health": 41.0}


def compute_trust(domain: str, values: Dict) -> float:
    """Derive trust score (0–100) from how far readings stray from normal bounds."""
    ranges = NORMAL_RANGES.get(domain, {})
    if not ranges:
        return 99.0
    in_range = sum(
        1 for k, (lo, hi) in ranges.items() if lo <= values.get(k, lo) <= hi
    )
    total = len(ranges)
    if in_range == total:
        return round(_clamp(_j(99.0, 0.004), 97.0, 100.0), 1)
    if in_range == 0:
        floor = ATTACK_TRUST_FLOOR.get(domain, 12.0)
        return round(_clamp(_j(floor, 0.05), floor * 0.7, floor * 1.3), 1)
    frac = in_range / total
    floor = ATTACK_TRUST_FLOOR.get(domain, 12.0)
    return round(_clamp(floor + (99.0 - floor) * frac, floor, 99.0), 1)


# ── Simulator engine ──────────────────────────────────────────────────────────

class SimulatorEngine:
    """
    Manages three daemon threads producing continuous sensor readings.

    The caller (app.py) can toggle attack_active at any time via
    ``trigger_attack()`` / ``reset()``.  Thread-safe.
    """

    def __init__(self, state: Dict, on_reading: Optional[Callable] = None):
        """
        Args:
            state:      Mutable shared-state dict owned by app.py
            on_reading: Optional callback(domain, reading) after each reading
        """
        self._state = state
        self._on_reading = on_reading
        self._running = False

    # ── value generators ──────────────────────────────────────────────────────

    def _water(self, elapsed: float) -> Dict:
        if self._state["attack_active"]:
            return {
                "ph":        _clamp(_j(3.2,  0.04), 2.8,  3.8),
                "turbidity": _clamp(_j(28.0, 0.04), 22.0, 33.0),
                "flow_rate": _clamp(_j(2.1,  0.04), 1.5,  2.8),
            }
        return {
            "ph":        _clamp(_j(7.5,  0.015), 6.5,  8.5),
            "turbidity": _clamp(_j(2.1,  0.04),  0.1,  4.0),
            "flow_rate": _clamp(_j(15.0, 0.015), 12.0, 18.0),
        }

    def _soil(self, elapsed: float) -> Dict:
        if self._state["attack_active"] and elapsed >= 3.0:
            return {
                "moisture":  _clamp(_j(78.0, 0.025), 70.0, 86.0),
                "nitrogen":  _clamp(_j(160.0, 0.03), 140.0, 180.0),
                "salinity":  _clamp(_j(3.8,  0.03),  3.2,  4.4),
            }
        return {
            "moisture":  _clamp(_j(45.0, 0.025), 35.0, 55.0),
            "nitrogen":  _clamp(_j(160.0, 0.03), 140.0, 180.0),
            "salinity":  _clamp(_j(1.1,   0.04), 0.8,  1.4),
        }

    def _health(self, elapsed: float) -> Dict:
        if self._state["attack_active"] and elapsed >= 10.0:
            return {
                "malnutrition_index": _clamp(_j(19.0, 0.025), 16.0, 22.0),
                "disease_incidence":  _clamp(_j(14.0, 0.03),  11.0, 17.0),
                "clinic_visits":      int(_clamp(_j(134.0, 0.025), 118.0, 148.0)),
            }
        return {
            "malnutrition_index": _clamp(_j(5.5, 0.03), 4.0, 7.0),
            "disease_incidence":  _clamp(_j(3.5, 0.04), 2.0, 5.0),
            "clinic_visits":      int(_clamp(_j(50.0, 0.04), 40.0, 60.0)),
        }

    # ── storage + state update ────────────────────────────────────────────────

    def _emit(self, sensor_id: str, domain: str, values: Dict) -> None:
        ts  = datetime.now(timezone.utc).isoformat()
        sig = sign_reading(sensor_id, ts, values)

        # Persist to DB (best-effort; don't crash the thread on DB errors)
        if not self._state.get("network_offline"):
            try:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO sensor_readings "
                    "(sensor_id, domain, timestamp, values_json, hmac_signature, region, is_ghost) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (sensor_id, domain, ts, json.dumps(values), sig, "REGION-1", 0),
                )
                conn.commit()
            except Exception as exc:
                print(f"[Simulator] DB write error: {exc}")
        else:
            # Offline: push to buffer instead
            self._state["offline_buffer"].append(
                {"sensor_id": sensor_id, "domain": domain,
                 "timestamp": ts, "values": values, "sig": sig}
            )

        trust = compute_trust(domain, values)
        reading = {**values, "sensor_id": sensor_id, "timestamp": ts,
                   "hmac": sig, "trust_score": trust}

        with self._state["lock"]:
            self._state["latest"][domain] = reading
            self._state["windows"][domain].append(reading)

        if self._on_reading:
            self._on_reading(domain, reading)

    # ── thread bodies ─────────────────────────────────────────────────────────

    def _elapsed(self) -> float:
        ts = self._state.get("attack_ts")
        if self._state["attack_active"] and ts:
            return time.time() - ts
        return 0.0

    def _run_water(self):
        while self._running:
            self._emit("W-447", "water", self._water(self._elapsed()))
            time.sleep(2)

    def _run_soil(self):
        while self._running:
            self._emit("S-123", "soil", self._soil(self._elapsed()))
            time.sleep(2)

    def _run_health(self):
        while self._running:
            self._emit("H-890", "health", self._health(self._elapsed()))
            time.sleep(3)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        for target in (self._run_water, self._run_soil, self._run_health):
            t = threading.Thread(target=target, daemon=True, name=f"sim-{target.__name__}")
            t.start()
        print("[Simulator] ✓ 3 sensor streams active")

    def stop(self) -> None:
        self._running = False

    def trigger_attack(self) -> None:
        with self._state["lock"]:
            self._state["attack_active"] = True
            self._state["attack_ts"]     = time.time()
        print("[Simulator] ⚡ Attack mode activated")

    def reset(self) -> None:
        with self._state["lock"]:
            self._state["attack_active"] = False
            self._state["attack_ts"]     = None
        print("[Simulator] ✓ Reset to normal operation")
