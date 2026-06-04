"""
Simulated attacker — auto-triggers ghost-sensor intrusions for the demo.

When attack mode is activated (POST /api/attack/inject), app.py launches
this module in a daemon thread.

Timeline:
  t + 4s  → POST fake pH injection to GW-GHOST-7a3f  (water, primary attack)
  t + 6s  → POST lateral probe to SW-GHOST-2c91       (water, lateral movement)

The requests go back to the local Flask server at http://127.0.0.1:5000.
The ghost endpoint returns 200 OK silently while logging the intrusion.
"""

import json
import threading
import time
from datetime import datetime, timezone
from typing import Optional

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[AttackerSim] Warning: 'requests' not installed — using urllib fallback")

BASE_URL = "http://127.0.0.1:5000"

# Payloads the simulated attacker injects
_ATTACK_PAYLOADS = {
    "GW-GHOST-7a3f": {
        "sensor_id": "GW-GHOST-7a3f",
        "ph":        3.2,       # compromised value (should be ~7.4)
        "turbidity": 28.0,      # compromised value (should be ~2.1)
        "flow_rate": 2.1,       # compromised value (should be ~15.0)
        "note":      "routine_calibration",  # attacker disguises write as calibration
    },
    "SW-GHOST-2c91": {
        "sensor_id": "SW-GHOST-2c91",
        "ph":        3.5,
        "turbidity": 22.0,
        "note":      "probe_scan",
    },
}


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _post(url: str, payload: dict) -> int:
    """Send HTTP POST; return status code (0 on failure)."""
    if HAS_REQUESTS:
        try:
            r = _requests.post(url, json=payload, timeout=5)
            return r.status_code
        except Exception as exc:
            print(f"[AttackerSim] HTTP error: {exc}")
            return 0
    else:
        # urllib fallback (no extra dependency)
        import urllib.request, urllib.error
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status
        except Exception as exc:
            print(f"[AttackerSim] urllib error: {exc}")
            return 0


# ── Attacker simulation ───────────────────────────────────────────────────────

class AttackerSimulator:
    """
    Launches a single daemon thread that sends two ghost-sensor intrusions
    after a short delay to simulate a real attacker probing the network.
    """

    def __init__(self, base_url: str = BASE_URL):
        self._base = base_url.rstrip("/")
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Spawn the attacker thread (idempotent — no-op if already running)."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="attacker-sim"
        )
        self._thread.start()
        print("[AttackerSim] ⚡ Attacker thread started")

    def _run(self) -> None:
        # Step 1 — Primary intrusion on water groundwater node (4s after attack start)
        time.sleep(4)
        self._inject("GW-GHOST-7a3f")

        # Step 2 — Lateral probe on surface water sensor (2s later)
        time.sleep(2)
        self._inject("SW-GHOST-2c91")

        print("[AttackerSim] Both intrusion attempts sent.")

    def _inject(self, sensor_id: str) -> None:
        url     = f"{self._base}/ghost/{sensor_id}/reading"
        payload = _ATTACK_PAYLOADS.get(sensor_id, {"sensor_id": sensor_id, "ph": 3.2})
        ts      = datetime.now(timezone.utc).isoformat()
        payload["injected_at"] = ts

        status = _post(url, payload)
        print(
            f"[AttackerSim] → POST /ghost/{sensor_id}/reading  "
            f"status={status}  ts={ts[:19]}"
        )


# ── CLI entry-point (manual test) ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Sending simulated attack directly (ensure Flask is running on :5000)…")
    sim = AttackerSimulator()

    for sid in ("GW-GHOST-7a3f", "SW-GHOST-2c91"):
        url     = f"{BASE_URL}/ghost/{sid}/reading"
        payload = _ATTACK_PAYLOADS[sid]
        status  = _post(url, payload)
        print(f"  {sid} → {status}")
        time.sleep(2)

    print("Done.  Check GET http://localhost:5000/api/ghosts for logged intrusions.")
