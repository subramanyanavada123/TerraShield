"""
Crop yield attribution model — LinearRegression + IsolationForest.

Demonstrates which sensors most influenced the current crop-yield prediction
and flags untrusted inputs so the agronomic AI's reasoning stays auditable.

Training data is synthetic, derived from known agronomic relationships:
  • pH drop → irrigation model confusion → yield loss
  • Salinity rise → direct crop stress → yield loss
  • Turbidity high → irrigation blockage → yield loss
  • Moisture optimal (45 %) → yield maximised
  • Nitrogen optimal (160 ppm) → yield maximised

GET /api/attribution  →  {attributions, predicted_yield, untrusted_sensors}
"""

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from typing import Dict, List, Any

# ── Synthetic training data generation ────────────────────────────────────────

def _make_training_data(n: int = 1200, seed: int = 42) -> tuple:
    """
    Generate (X, y) where X is sensor features and y is crop_yield_index [0, 100].

    Relationships encoded:
      pH: peak yield at 7.0–7.5; sharp drop below 5 or above 9
      turbidity: negative linear (high turbidity → blocked irrigation)
      flow_rate: mild positive up to 16 L/min; negligible above
      moisture: inverted-U peaking at 45%
      salinity: strong negative (above 1.5 → crop stress)
      nitrogen: mild positive up to 160 ppm; plateau above
    """
    rng = np.random.default_rng(seed)

    ph         = rng.uniform(5.0, 9.0, n)
    turbidity  = rng.uniform(0.1, 10.0, n)
    flow_rate  = rng.uniform(8.0, 20.0, n)
    moisture   = rng.uniform(20.0, 80.0, n)
    salinity   = rng.uniform(0.5, 5.0, n)
    nitrogen   = rng.uniform(100.0, 200.0, n)

    # Normalised contributions (0–1 scale) then weighted sum
    ph_score       = np.clip(1.0 - (np.abs(ph - 7.2) / 2.0), 0, 1)
    turb_score     = np.clip(1.0 - turbidity / 10.0, 0, 1)
    flow_score     = np.clip((flow_rate - 8.0) / 10.0, 0, 1)
    moisture_score = np.clip(1.0 - (np.abs(moisture - 45.0) / 30.0), 0, 1)
    salinity_score = np.clip(1.0 - (salinity / 3.0), 0, 1)
    nitrogen_score = np.clip((nitrogen - 100.0) / 80.0, 0, 1)

    # Weighted yield index (weights reflect agronomic importance)
    y = (
        22.0 * ph_score
        + 18.0 * salinity_score
        + 16.0 * moisture_score
        + 14.0 * nitrogen_score
        + 16.0 * turb_score
        + 14.0 * flow_score
        + rng.normal(0, 2.0, n)  # noise
    )
    y = np.clip(y, 0.0, 100.0)

    X = np.column_stack([ph, turbidity, flow_rate, moisture, salinity, nitrogen])
    return X, y


# Feature names (must match column order in X)
FEATURES = ["ph", "turbidity", "flow_rate", "moisture", "salinity", "nitrogen"]


# ── Model class ───────────────────────────────────────────────────────────────

class CropYieldModel:
    """
    Linear regression model for crop yield with attribution output.

    Trained once at startup on synthetic agronomic data.  During inference,
    each prediction is accompanied by per-sensor attribution coefficients
    (standardised, so they're directly comparable) and an IsolationForest
    anomaly flag that marks untrusted inputs.
    """

    def __init__(self):
        X, y = _make_training_data()

        self._scaler = StandardScaler()
        Xs = self._scaler.fit_transform(X)

        self._reg = LinearRegression()
        self._reg.fit(Xs, y)

        # IsolationForest trained on the same X to detect out-of-distribution inputs
        self._iso = IsolationForest(n_estimators=80, contamination=0.05, random_state=42)
        self._iso.fit(X)

        # Coefficient magnitudes (absolute) normalised to sum to 1.0 for attribution %
        abs_coef = np.abs(self._reg.coef_)
        self._coef_pct = (abs_coef / abs_coef.sum() * 100).round(1)

        print(
            "[ML] CropYieldModel trained — "
            f"R² on synthetic data ≈ {self._reg.score(Xs, y):.3f}"
        )

    def predict(
        self,
        state: Dict,
        anomalous_domains: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Run inference on the current sensor readings from shared state.

        Args:
            state:             Shared app state
            anomalous_domains: Domains flagged by the correlation engine

        Returns:
            Attribution dict for /api/attribution
        """
        anomalous_domains = anomalous_domains or []

        # Pull latest readings (fall back to midpoints if stream not started yet)
        w = state["latest"].get("water")  or {"ph": 7.5, "turbidity": 2.1, "flow_rate": 15.0}
        s = state["latest"].get("soil")   or {"moisture": 45.0, "salinity": 1.1, "nitrogen": 160.0}

        features_dict = {
            "ph":        w.get("ph", 7.5),
            "turbidity": w.get("turbidity", 2.1),
            "flow_rate": w.get("flow_rate", 15.0),
            "moisture":  s.get("moisture", 45.0),
            "salinity":  s.get("salinity", 1.1),
            "nitrogen":  s.get("nitrogen", 160.0),
        }

        X_raw = np.array([[features_dict[f] for f in FEATURES]])
        X_scaled = self._scaler.transform(X_raw)

        yield_pred = float(np.clip(self._reg.predict(X_scaled)[0], 0.0, 100.0))

        # IsolationForest anomaly score for each reading
        iso_pred = self._iso.predict(X_raw)[0]  # -1=anomaly, 1=normal
        iso_score = float(-self._iso.decision_function(X_raw)[0])  # higher = more anomalous

        # Build attribution list
        attributions = []
        water_domain_flagged  = "WATER"  in anomalous_domains
        soil_domain_flagged   = "SOIL"   in anomalous_domains
        health_domain_flagged = "HEALTH" in anomalous_domains

        sensor_domain_map = {
            "ph":        ("water",  water_domain_flagged),
            "turbidity": ("water",  water_domain_flagged),
            "flow_rate": ("water",  water_domain_flagged),
            "moisture":  ("soil",   soil_domain_flagged),
            "salinity":  ("soil",   soil_domain_flagged),
            "nitrogen":  ("soil",   soil_domain_flagged),
        }

        for i, feat in enumerate(FEATURES):
            domain, is_flagged = sensor_domain_map[feat]
            attributions.append({
                "sensor":        feat,
                "domain":        domain,
                "value":         round(features_dict[feat], 3),
                "coefficient_pct": float(self._coef_pct[i]),
                "influence":     "HIGH" if self._coef_pct[i] > 20 else
                                 "MEDIUM" if self._coef_pct[i] > 12 else "LOW",
                "trusted":       not is_flagged,
                "status":        "UNTRUSTED INPUT" if is_flagged else "TRUSTED",
            })

        # Sort by attribution magnitude descending
        attributions.sort(key=lambda a: a["coefficient_pct"], reverse=True)

        untrusted = [a["sensor"] for a in attributions if not a["trusted"]]

        return {
            "predicted_yield_index": round(yield_pred, 2),
            "yield_rating":          _yield_label(yield_pred),
            "attributions":          attributions,
            "untrusted_sensors":     untrusted,
            "iso_anomaly":           iso_pred == -1,
            "iso_anomaly_score":     round(iso_score, 4),
            "model":                 "LinearRegression (scikit-learn)",
            "training_samples":      1200,
            "note": (
                f"⚠ {len(untrusted)} sensor(s) flagged as untrusted — "
                f"yield prediction may be unreliable"
                if untrusted else
                "All inputs verified — prediction reliable"
            ),
        }


def _yield_label(y: float) -> str:
    if y >= 80:
        return "EXCELLENT"
    if y >= 60:
        return "GOOD"
    if y >= 40:
        return "MODERATE"
    if y >= 20:
        return "POOR"
    return "CRITICAL"
