"""
Synthetic sensor data generator for TerraShield ML training.

Generates labeled multivariate time-series for the three TerraShield domains
(water, soil, health) with realistic diurnal patterns, noise, and the ability
to inject a sensor-compromise attack that propagates causally downstream.

The causal chain mirrors the UI:
    Water sensor compromise
        → Irrigation model receives bad data
            → Soil over-irrigated (moisture↑, salinity↑)
                → Crop yield failure
                    → Malnutrition / clinic demand rises
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


# ── Attack configuration ───────────────────────────────────────────────────────

@dataclass
class AttackConfig:
    start_idx: int
    duration: int                   # timesteps the attack lasts
    ramp_in: int = 60               # timesteps to ramp up (realistic gradual spoofing)
    target_domain: str = "water"


# ── Generator ─────────────────────────────────────────────────────────────────

class TerraShieldDataGenerator:
    """
    Reproducible synthetic sensor streams for TerraShield.

    One timestep = 1 minute.  Default scenario: 2 weeks (20 160 steps).
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    # ── individual domain generators ──────────────────────────────────────────

    def generate_water_stream(
        self,
        n: int,
        attack: Optional[AttackConfig] = None,
    ) -> pd.DataFrame:
        """Water quality: pH, turbidity, flow_rate with diurnal rhythm."""
        t = np.arange(n, dtype=float)

        # Diurnal variation + Gaussian noise
        ph = 7.5 + 0.30 * np.sin(2 * np.pi * t / 1440) + self.rng.normal(0, 0.08, n)
        ph = np.clip(ph, 6.5, 8.5)

        turbidity = (
            2.1
            + 0.5 * np.abs(np.sin(2 * np.pi * t / 720))
            + self.rng.gamma(1.0, 0.2, n)
        )
        turbidity = np.clip(turbidity, 0.1, 4.0)

        flow_rate = (
            15.0
            + 1.5 * np.sin(2 * np.pi * t / 1440)
            + self.rng.normal(0, 0.4, n)
        )
        flow_rate = np.clip(flow_rate, 12.0, 18.0)

        labels = np.zeros(n, dtype=np.int8)

        if attack:
            s = attack.start_idx
            e = min(s + attack.duration, n)
            r = min(attack.ramp_in, e - s)

            ramp = np.concatenate([np.linspace(0, 1, r), np.ones(e - s - r)])

            ph[s:e]        = ph[s:e]        * (1 - ramp) + (3.2  + self.rng.normal(0, 0.1,  e - s)) * ramp
            turbidity[s:e] = turbidity[s:e] * (1 - ramp) + (28.0 + self.rng.normal(0, 1.0,  e - s)) * ramp
            flow_rate[s:e] = flow_rate[s:e] * (1 - ramp) + (2.1  + self.rng.normal(0, 0.1,  e - s)) * ramp
            labels[s:e] = 1

        return pd.DataFrame({
            "timestamp":  pd.date_range("2024-01-01", periods=n, freq="min"),
            "ph":         ph,
            "turbidity":  turbidity,
            "flow_rate":  flow_rate,
            "is_attack":  labels,
            "domain":     "water",
        })

    def generate_soil_stream(
        self,
        n: int,
        upstream_water: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Soil metrics with optional causal coupling to upstream water.

        When upstream water is compromised, over-irrigation drives moisture↑
        and salinity↑ after a ~2-hour lag (irrigation response time).
        """
        t = np.arange(n, dtype=float)

        moisture = 45.0 + 5.0 * np.sin(2 * np.pi * t / 1440) + self.rng.normal(0, 1.5, n)
        nitrogen = 160.0 + self.rng.normal(0, 5.0, n)
        salinity = 1.1  + 0.1  * np.sin(2 * np.pi * t / 4320) + self.rng.normal(0, 0.05, n)

        labels = np.zeros(n, dtype=np.int8)

        if upstream_water is not None and "is_attack" in upstream_water.columns:
            attack_sig = upstream_water["is_attack"].values[:n]
            lag = 120  # 2-hour irrigation lag

            for i in range(lag, n):
                window = attack_sig[max(0, i - lag): i]
                if window.mean() > 0.5:
                    progress = min((i - lag) / 600.0, 1.0)
                    moisture[i] += progress * 33.0   # toward 78 %
                    salinity[i] += progress * 2.7    # toward 3.8 dS/m
                    labels[i] = 1

        return pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="min"),
            "moisture":  np.clip(moisture, 30.0, 90.0),
            "nitrogen":  np.clip(nitrogen, 120.0, 200.0),
            "salinity":  np.clip(salinity, 0.5, 5.0),
            "is_attack": labels,
            "domain":    "soil",
        })

    def generate_health_stream(
        self,
        n: int,
        upstream_soil: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Community health metrics with optional causal coupling to soil quality.

        Health impacts lag soil degradation by ~1 week (crop-growth cycle).
        """
        t = np.arange(n, dtype=float)

        malnutrition     = 5.5  + 0.5 * np.sin(2 * np.pi * t / 10080) + self.rng.normal(0, 0.2, n)
        disease_inc      = 3.5  + self.rng.normal(0, 0.3, n)
        clinic_visits    = 50.0 + 5.0 * np.sin(2 * np.pi * t / 10080) + self.rng.normal(0, 2.0, n)

        labels = np.zeros(n, dtype=np.int8)

        if upstream_soil is not None and "is_attack" in upstream_soil.columns:
            soil_sig = upstream_soil["is_attack"].values[:n]
            lag = 7 * 24 * 60  # 1-week lag

            for i in range(lag, n):
                window = soil_sig[max(0, i - lag): i]
                if window.mean() > 0.3:
                    progress = min((i - lag) / 1440.0, 1.0)
                    malnutrition[i]  += progress * 13.5
                    disease_inc[i]   += progress * 10.5
                    clinic_visits[i] += progress * 84.0
                    labels[i] = 1

        return pd.DataFrame({
            "timestamp":         pd.date_range("2024-01-01", periods=n, freq="min"),
            "malnutrition":      np.clip(malnutrition, 0.0, 25.0),
            "disease_incidence": np.clip(disease_inc, 0.0, 20.0),
            "clinic_visits":     np.clip(clinic_visits, 20.0, 200.0),
            "is_attack":         labels,
            "domain":            "health",
        })

    # ── full scenario ──────────────────────────────────────────────────────────

    def generate_full_scenario(
        self,
        n: int = 20_160,
        attack_start: int = 5_000,
        attack_duration: int = 3_000,
    ) -> dict[str, pd.DataFrame]:
        """
        Generate a complete causal-chain scenario:

            Water compromise → Soil degradation → Health outcomes

        Args:
            n:               Total timesteps (default = 2 weeks at 1-min resolution)
            attack_start:    Timestep at which sensor W-447 is compromised
            attack_duration: How long the attack lasts

        Returns:
            {'water': df, 'soil': df, 'health': df}
        """
        attack = AttackConfig(
            start_idx=attack_start,
            duration=attack_duration,
            ramp_in=60,
        )

        water  = self.generate_water_stream(n, attack=attack)
        soil   = self.generate_soil_stream(n, upstream_water=water)
        health = self.generate_health_stream(n, upstream_soil=soil)

        return {"water": water, "soil": soil, "health": health}

    def save(self, scenario: dict[str, pd.DataFrame], out_dir: str = "data") -> None:
        """Persist scenario DataFrames as Parquet files."""
        p = Path(out_dir)
        p.mkdir(parents=True, exist_ok=True)

        meta = {}
        for domain, df in scenario.items():
            path = p / f"{domain}_stream.parquet"
            df.to_parquet(path, index=False)
            n_attack = int(df["is_attack"].sum())
            meta[domain] = {
                "rows": len(df),
                "attack_rows": n_attack,
                "attack_pct": round(n_attack / len(df) * 100, 2),
            }
            print(f"  [{domain}] {len(df):,} rows — {n_attack:,} attack timesteps ({meta[domain]['attack_pct']}%)")

        (p / "scenario_meta.json").write_text(json.dumps(meta, indent=2))
        print(f"\nSaved to {p.resolve()}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating TerraShield synthetic scenario (2 weeks, attack at t=5000)…")
    gen = TerraShieldDataGenerator(seed=42)
    scenario = gen.generate_full_scenario()
    gen.save(scenario)
