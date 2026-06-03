"""
Bayesian Trust Scorer for TerraShield sensor nodes.

Each sensor maintains a continuous trust probability
    P(sensor_healthy | all_readings_so_far)
updated via Bayes' theorem on every new reading.

The log-odds form avoids numerical underflow and makes the update
additive: log-odds += log-likelihood-ratio.

Trust model
-----------
  Prior:        P(healthy) = 0.99   (sensors are almost always fine)
  Healthy:      readings ~ N(center, σ²)  within calibrated bounds
  Compromised:  readings shifted toward attacker target values
  Posterior:    updated with each reading; slow recovery via exponential decay

Typical output
--------------
  Normal operation:  trust ≈ 0.97–1.00
  Under attack:      trust collapses to < 0.15 within ~50 readings
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np


# ── Calibration ────────────────────────────────────────────────────────────────

@dataclass
class SensorCalibration:
    """Expected operating statistics for a domain's metrics."""
    bounds: Dict[str, tuple]   # metric → (lo_normal, hi_normal)
    sigma:  Dict[str, float]   # expected 1-σ noise in normal operation


DOMAIN_CALIBRATIONS: Dict[str, SensorCalibration] = {
    "water": SensorCalibration(
        bounds={"ph": (6.5, 8.5), "turbidity": (0.1, 4.0), "flow_rate": (12.0, 18.0)},
        sigma= {"ph": 0.15,       "turbidity": 0.40,        "flow_rate": 0.50},
    ),
    "soil": SensorCalibration(
        bounds={"moisture": (35.0, 55.0), "nitrogen": (140.0, 180.0), "salinity": (0.8, 1.4)},
        sigma= {"moisture": 2.0,          "nitrogen": 6.0,             "salinity": 0.08},
    ),
    "health": SensorCalibration(
        bounds={"malnutrition": (4.0, 7.0), "disease_incidence": (2.0, 5.0), "clinic_visits": (40.0, 60.0)},
        sigma= {"malnutrition": 0.40,       "disease_incidence": 0.30,        "clinic_visits": 3.0},
    ),
}


# ── Per-sensor Bayesian scorer ─────────────────────────────────────────────────

class BayesianTrustScorer:
    """
    Maintains a rolling Bayesian trust estimate for one sensor node.

    Parameters
    ----------
    domain:       One of 'water', 'soil', 'health'
    sensor_id:    Human-readable label (e.g. 'W-447')
    prior_trust:  Starting belief that the sensor is healthy (default 0.99)
    sensitivity:  LLR scaling — higher = faster trust collapse (default 0.25)
    decay:        Per-step recovery toward prior (0.999 ≈ 1-min half-life of 1 day)
    """

    def __init__(
        self,
        domain: str,
        sensor_id: str,
        prior_trust: float = 0.99,
        sensitivity: float = 0.25,
        decay: float = 0.999,
    ):
        if domain not in DOMAIN_CALIBRATIONS:
            raise ValueError(f"Unknown domain: {domain}")

        self.domain      = domain
        self.sensor_id   = sensor_id
        self.calib       = DOMAIN_CALIBRATIONS[domain]
        self.sensitivity = sensitivity
        self.decay       = decay

        self._prior_log_odds = float(np.log(prior_trust / (1.0 - prior_trust)))
        self._log_odds       = self._prior_log_odds
        self._history: List[float] = []

    # ── internals ─────────────────────────────────────────────────────────────

    def _llr(self, metric: str, value: float) -> float:
        """
        Log-likelihood ratio:  log P(value | compromised) − log P(value | healthy)

        Positive LLR = evidence of compromise.
        """
        lo, hi = self.calib.bounds[metric]
        sigma  = self.calib.sigma[metric]
        center = (lo + hi) / 2.0

        # Healthy: tight Gaussian at center
        log_p_h = -0.5 * ((value - center) / sigma) ** 2

        # Compromised: attacker shifts reading outside normal range
        # We model this as a much wider Gaussian (uninformative attacker)
        sigma_c = (hi - lo) * 2.0
        log_p_c = -0.5 * ((value - center) / sigma_c) ** 2 - np.log(sigma_c)

        return float(log_p_c - log_p_h)

    # ── public API ────────────────────────────────────────────────────────────

    def update(self, reading: Dict[str, float]) -> float:
        """
        Incorporate one sensor reading and return updated trust.

        Args:
            reading: {metric: value} dict for all metrics of this sensor

        Returns:
            Current trust probability P(healthy) ∈ [0, 1]
        """
        total_llr = sum(
            self._llr(m, v)
            for m, v in reading.items()
            if m in self.calib.bounds
        )

        # Bayesian update in log-odds space
        self._log_odds -= total_llr * self.sensitivity

        # Slow recovery toward prior (sensor recalibration / self-healing)
        self._log_odds = (
            self._log_odds * self.decay
            + self._prior_log_odds * (1.0 - self.decay)
        )

        # Numerical safety clamp
        self._log_odds = float(np.clip(self._log_odds, -12.0, 7.0))

        trust = float(1.0 / (1.0 + np.exp(-self._log_odds)))
        self._history.append(trust)
        return trust

    def update_batch(self, df: pd.DataFrame) -> pd.Series:
        """Process a DataFrame row-by-row; return a trust series."""
        import pandas as _pd
        features = [k for k in self.calib.bounds if k in df.columns]
        scores = [self.update({f: row[f] for f in features}) for _, row in df.iterrows()]
        return _pd.Series(scores, index=df.index, name=f"trust_{self.sensor_id}")

    def reset(self) -> None:
        """Reset to prior trust (call after confirmed sensor replacement)."""
        self._log_odds = self._prior_log_odds
        self._history.clear()

    @property
    def current_trust(self) -> float:
        return float(1.0 / (1.0 + np.exp(-self._log_odds)))

    @property
    def history(self) -> List[float]:
        return list(self._history)


# ── Multi-sensor fleet monitor ─────────────────────────────────────────────────

class MultiSensorTrustMonitor:
    """
    Maintains trust scores for a fleet of sensors across all domains.

    Domain-level trust = geometric mean of its sensors' trusts
    (geometric mean is appropriate for multiplicative probability products).
    """

    def __init__(self):
        self._scorers: Dict[str, BayesianTrustScorer] = {}

    def add_sensor(self, sensor_id: str, domain: str, **kwargs) -> "MultiSensorTrustMonitor":
        self._scorers[sensor_id] = BayesianTrustScorer(domain, sensor_id, **kwargs)
        return self

    def update_all(self, readings: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Update every sensor that has a new reading; return updated trusts."""
        return {
            sid: self._scorers[sid].update(readings[sid])
            for sid in readings
            if sid in self._scorers
        }

    def get_domain_trust(self) -> Dict[str, float]:
        """Aggregate trust per domain (geometric mean of sensor trusts)."""
        domain_scores: Dict[str, List[float]] = {}
        for sid, scorer in self._scorers.items():
            domain_scores.setdefault(scorer.domain, []).append(scorer.current_trust)

        return {
            d: float(np.exp(np.mean(np.log(np.clip(scores, 1e-9, 1.0)))))
            for d, scores in domain_scores.items()
        }

    @property
    def scorers(self) -> Dict[str, BayesianTrustScorer]:
        return dict(self._scorers)


# ── CLI smoke-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import pandas as pd  # noqa: F401 — needed for update_batch
    sys.path.insert(0, "..")
    from data.synthetic_sensor_stream import TerraShieldDataGenerator, AttackConfig

    gen = TerraShieldDataGenerator(seed=42)

    print("Normal operation (1 000 readings)…")
    normal = gen.generate_water_stream(1_000)
    scorer = BayesianTrustScorer("water", "W-447")
    normal_scores = scorer.update_batch(normal)
    print(f"  mean={normal_scores.mean():.4f}  min={normal_scores.min():.4f}")

    print("\nUnder attack (500 readings, immediate ramp)…")
    attack_cfg = AttackConfig(start_idx=0, duration=500, ramp_in=30)
    attacked   = gen.generate_water_stream(500, attack=attack_cfg)
    attack_scores = scorer.update_batch(attacked)
    print(f"  mean={attack_scores.mean():.4f}  min={attack_scores.min():.4f}")
