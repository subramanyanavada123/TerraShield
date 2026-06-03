"""
Cross-domain causal correlation engine.

Primary algorithm: PCMCI (Peter-Clark with Momentary Conditional Independence)
via the Tigramite library (Runge et al., Science Advances 2019).

PCMCI advantages over simple Pearson correlation:
  - Identifies *directed* causal links, not just association
  - Handles lagged dependencies (water → soil takes ~2 h)
  - Controls for confounders via conditional independence tests
  - Provides p-values for statistical rigour

Fallback: bivariate Granger causality when Tigramite is not installed.

What this powers in the UI
--------------------------
The 3×3 "CROSS-DOMAIN CORRELATION MATRIX" shows pairwise domain correlations.
In normal operation:  all pairs ≈ 0.85–0.98
Under attack:         the compromised domain's correlations collapse
                      (water↔soil first, then water↔health, then soil↔health)
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from tigramite import data_processing as pp
    from tigramite.independence_tests.parcorr import ParCorr
    from tigramite.pcmci import PCMCI

    HAS_TIGRAMITE = True
except ImportError:
    HAS_TIGRAMITE = False


# ── Granger causality (fallback) ──────────────────────────────────────────────

def granger_pairwise(
    x: np.ndarray,
    y: np.ndarray,
    max_lag: int = 5,
) -> Dict:
    """
    Test whether x Granger-causes y via restricted vs unrestricted VAR F-test.

    Returns p-value, F-statistic, causal flag, and effect strength.
    """
    from scipy import stats

    n = len(y)

    Y = y[max_lag:]
    X_r = np.column_stack([y[max_lag - i - 1 : n - i - 1] for i in range(max_lag)])
    X_u = np.column_stack([
        X_r,
        *[x[max_lag - i - 1 : n - i - 1] for i in range(max_lag)],
    ])

    def ols_rss(A: np.ndarray, b: np.ndarray) -> float:
        try:
            beta = np.linalg.lstsq(A, b, rcond=None)[0]
            return float(np.sum((b - A @ beta) ** 2))
        except np.linalg.LinAlgError:
            return float(np.sum(b ** 2))

    rss_r = ols_rss(X_r, Y)
    rss_u = ols_rss(X_u, Y)
    df1, df2 = max_lag, n - max_lag - 2 * max_lag - 1

    if df2 <= 0 or rss_u <= 0:
        return {"p_value": 1.0, "f_stat": 0.0, "causal": False, "strength": 0.0}

    f = ((rss_r - rss_u) / df1) / (rss_u / df2)
    p = float(1.0 - stats.f.cdf(f, df1, df2))

    return {
        "p_value":  p,
        "f_stat":   float(f),
        "causal":   p < 0.05,
        "strength": float(np.clip(1.0 - rss_u / max(rss_r, 1e-10), 0, 1)),
    }


# ── Main engine ───────────────────────────────────────────────────────────────

class CrossDomainCorrelationEngine:
    """
    Discovers and monitors causal links between TerraShield domains.

    Two modes
    ---------
    fit_causal_graph(data)
        Offline: run PCMCI/Granger on historical data to discover the
        causal DAG structure.  Typically run once on training data.

    compute_correlation_matrix(data, window)
        Online: rolling Pearson correlation between domain mean signals.
        This is the fast signal the UI polls every 80 ms.
    """

    DOMAIN_FEATURES: Dict[str, List[str]] = {
        "water":  ["ph", "turbidity", "flow_rate"],
        "soil":   ["moisture", "nitrogen", "salinity"],
        "health": ["malnutrition", "disease_incidence", "clinic_visits"],
    }

    def __init__(self, max_lag: int = 10):
        self.max_lag = max_lag
        self._causal_graph: Optional[Dict] = None

    # ── offline causal discovery ──────────────────────────────────────────────

    def fit_causal_graph(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """
        Discover the causal graph from multi-domain time-series data.

        Uses PCMCI (Tigramite) when available; falls back to Granger.

        Returns a dict  {(cause, effect, lag): {p_value, strength}}
        """
        if HAS_TIGRAMITE:
            graph = self._fit_pcmci(data)
        else:
            graph = self._fit_granger(data)

        self._causal_graph = graph
        return graph

    def _fit_pcmci(self, data: Dict[str, pd.DataFrame]) -> Dict:
        arrays, var_names = [], []
        for domain, df in data.items():
            for feat in self.DOMAIN_FEATURES.get(domain, []):
                if feat in df.columns:
                    arrays.append(df[feat].values)
                    var_names.append(f"{domain}:{feat}")

        X = np.column_stack(arrays).astype(float)
        X = (X - X.mean(0)) / (X.std(0) + 1e-9)

        dataframe = pp.DataFrame(X, var_names=var_names)
        pcmci     = PCMCI(dataframe=dataframe, cond_ind_test=ParCorr(), verbosity=0)
        res       = pcmci.run_pcmci(tau_max=self.max_lag, pc_alpha=0.05)

        graph = {}
        for i, cause in enumerate(var_names):
            for j, effect in enumerate(var_names):
                if i == j:
                    continue
                for lag in range(1, self.max_lag + 1):
                    p = float(res["p_matrix"][i, j, lag])
                    v = float(res["val_matrix"][i, j, lag])
                    if p < 0.05:
                        graph[(cause, effect, lag)] = {"p_value": p, "strength": abs(v)}

        return graph

    def _fit_granger(self, data: Dict[str, pd.DataFrame]) -> Dict:
        # Summarise each domain to a single mean signal for speed
        min_n = min(len(df) for df in data.values())
        signals = {
            d: df[[f for f in self.DOMAIN_FEATURES[d] if f in df.columns]]
              .values[:min_n]
              .mean(axis=1)
            for d, df in data.items()
        }

        graph = {}
        for d1 in signals:
            for d2 in signals:
                if d1 == d2:
                    continue
                res = granger_pairwise(signals[d1], signals[d2], self.max_lag)
                if res["causal"]:
                    graph[(d1, d2, 1)] = res

        return graph

    # ── online correlation monitoring ─────────────────────────────────────────

    def compute_correlation_matrix(
        self,
        data: Dict[str, pd.DataFrame],
        window: int = 200,
    ) -> pd.DataFrame:
        """
        Rolling Pearson correlation between domain mean signals.

        Each domain's features are z-scored then averaged into one scalar
        signal.  Rolling correlations of the three scalars give a 3×3 matrix
        collapsed to three off-diagonal pairs: water_soil, water_health,
        soil_health.

        Args:
            data:   dict of {domain: DataFrame}
            window: rolling window length in timesteps

        Returns:
            DataFrame with columns [water_soil, water_health, soil_health, idx]
        """
        min_n = min(len(df) for df in data.values())

        domain_signals: Dict[str, np.ndarray] = {}
        for domain, df in data.items():
            feats = [f for f in self.DOMAIN_FEATURES[domain] if f in df.columns]
            v = df[feats].values[:min_n].astype(float)
            z = (v - v.mean(0)) / (v.std(0) + 1e-9)
            domain_signals[domain] = z.mean(axis=1)

        rows: List[Dict] = []
        pairs = list(combinations(list(domain_signals), 2))

        for i in range(window, min_n):
            sl = slice(i - window, i)
            row: Dict = {"idx": i}
            for d1, d2 in pairs:
                key = f"{d1}_{d2}"
                corr = float(np.corrcoef(domain_signals[d1][sl], domain_signals[d2][sl])[0, 1])
                row[key] = float(np.clip(corr, -1.0, 1.0))
            rows.append(row)

        return pd.DataFrame(rows)

    def detect_correlation_breaks(
        self,
        corr_df: pd.DataFrame,
        baseline_rows: int = 100,
        threshold: float = 0.45,
    ) -> pd.DataFrame:
        """
        Flag timesteps where a pair's correlation drops > threshold below baseline.

        Args:
            corr_df:       Output of compute_correlation_matrix()
            baseline_rows: How many initial rows to use as baseline
            threshold:     Minimum drop to flag as a break

        Returns:
            corr_df with added '*_break' columns and 'break_detected' boolean
        """
        out = corr_df.copy()
        pair_cols = [c for c in corr_df.columns if "_" in c and c != "idx"]

        baselines = {c: corr_df[c].iloc[:baseline_rows].mean() for c in pair_cols}

        for c in pair_cols:
            out[f"{c}_break"] = (baselines[c] - out[c]) > threshold

        out["break_detected"] = out[[f"{c}_break" for c in pair_cols]].any(axis=1)
        return out


# ── CLI smoke-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "..")
    from data.synthetic_sensor_stream import TerraShieldDataGenerator

    gen = TerraShieldDataGenerator(seed=42)
    scenario = gen.generate_full_scenario(n=4_000, attack_start=2_500)

    engine = CrossDomainCorrelationEngine(max_lag=5)

    print("Rolling correlation matrix…")
    corr = engine.compute_correlation_matrix(scenario, window=120)

    print("Detecting breaks…")
    breaks = engine.detect_correlation_breaks(corr, baseline_rows=60, threshold=0.4)
    n_breaks = int(breaks["break_detected"].sum())
    print(f"  Breaks detected: {n_breaks} / {len(breaks)} timesteps ({n_breaks/len(breaks)*100:.1f}%)")

    print("\nFitting causal graph (Granger fallback if Tigramite absent)…")
    small = {k: v.head(600) for k, v in scenario.items()}
    graph = engine.fit_causal_graph(small)
    print(f"  Causal links found: {len(graph)}")
    for edge, stats in list(graph.items())[:4]:
        print(f"  {edge[0]} → {edge[1]} (lag={edge[2]}): strength={stats.get('strength', '?'):.3f}")
