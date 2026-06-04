"""
Offline buffer — simulates IoT edge-node disconnection and reconnection.

When the network is taken "offline":
  • The simulator stops writing to SQLite
  • Readings accumulate in a local deque (max 500 entries)

When the network is "restored":
  • All buffered readings are replayed into SQLite with their original timestamps
  • The correlation engine re-evaluates the replayed window
  • Out-of-order safety: inserts are ordered by original timestamp

This demonstrates TerraShield's edge-resilience story: even if the cloud
connection drops during an attack, evidence is preserved and analysed on
reconnect.
"""

import json
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from database import get_conn


BUFFER_MAX = 500


class OfflineBuffer:
    """Thread-safe offline read buffer with replay capability."""

    def __init__(self, state: Dict, correlator: Optional[Any] = None):
        """
        Args:
            state:      Shared app state (owns ``network_offline`` flag and
                        ``offline_buffer`` deque)
            correlator: Optional CorrelationEngine; re-run after replay if provided
        """
        self._state      = state
        self._correlator = correlator

    # ── network simulation ────────────────────────────────────────────────────

    def go_offline(self) -> Dict:
        """
        Set the network_offline flag.
        The simulator will start buffering instead of writing to SQLite.
        """
        with self._state["lock"]:
            self._state["network_offline"] = True
            buf_size = len(self._state["offline_buffer"])

        print(f"[Buffer] 🔴 Network offline.  Buffer has {buf_size} entries.")
        return {
            "status":   "offline",
            "buffered": buf_size,
            "message":  "Simulator now writing to local edge buffer (SQLite bypassed)",
        }

    def go_online(self) -> Dict:
        """
        Clear the network_offline flag and replay all buffered readings.
        Returns a summary of what was replayed.
        """
        with self._state["lock"]:
            self._state["network_offline"] = False
            to_replay: List[Dict] = list(self._state["offline_buffer"])
            self._state["offline_buffer"].clear()

        if not to_replay:
            return {
                "status":   "online",
                "replayed": 0,
                "anomalies_detected": 0,
                "message":  "Network restored — buffer was empty",
            }

        print(f"[Buffer] 🟢 Replaying {len(to_replay)} buffered readings…")
        replayed     = 0
        anomalies    = 0
        replay_start = time.time()

        # Sort by original timestamp (out-of-order safety)
        to_replay.sort(key=lambda r: r["timestamp"])

        conn = get_conn()

        for entry in to_replay:
            try:
                conn.execute(
                    "INSERT INTO sensor_readings "
                    "(sensor_id, domain, timestamp, values_json, hmac_signature, region, is_ghost) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        entry["sensor_id"],
                        entry["domain"],
                        entry["timestamp"],
                        json.dumps(entry["values"]),
                        entry.get("sig", "replayed"),
                        "REGION-1",
                        0,
                    ),
                )
                replayed += 1

                # Reload reading into the windows for correlation analysis
                reading = {**entry["values"],
                           "sensor_id":  entry["sensor_id"],
                           "timestamp":  entry["timestamp"],
                           "trust_score": 50.0}  # conservative trust for replayed data

                with self._state["lock"]:
                    self._state["windows"][entry["domain"]].append(reading)

            except Exception as exc:
                print(f"[Buffer] Replay error: {exc}")

        conn.commit()

        # Re-run correlation analysis on the replayed window
        if self._correlator:
            result = self._correlator.compute()
            if result.get("confidence", 0) > 20:
                anomalies = 1

        elapsed = round(time.time() - replay_start, 3)
        print(f"[Buffer] Replay complete: {replayed} readings in {elapsed}s — anomalies: {anomalies}")

        return {
            "status":            "online",
            "replayed":          replayed,
            "anomalies_detected": anomalies,
            "replay_duration_s": elapsed,
            "message":           (
                f"Network restored — replayed {replayed} buffered readings "
                f"({anomalies} anomalies detected during replay)"
            ),
        }

    # ── status ────────────────────────────────────────────────────────────────

    def status(self) -> Dict:
        with self._state["lock"]:
            offline  = self._state["network_offline"]
            buf_size = len(self._state["offline_buffer"])

        return {
            "network_offline": offline,
            "buffered_count":  buf_size,
            "buffer_capacity": BUFFER_MAX,
            "buffer_pct_full": round(buf_size / BUFFER_MAX * 100, 1),
        }
