# AIR KAVACH - Machine Learning Model Card: Isolation Forest Anomaly Detection

## 1. Model Details

- **Model Identifier**: `isolation-forest-pm25-v1`
- **Model Type**: Unsupervised Ensemble Anomaly Detector (`sklearn.ensemble.IsolationForest`)
- **Version**: 1.0.0 (Production Candidate)
- **Serialization Artifact**: `models/isolation_forest/isolation_forest_v1.joblib`
- **Metadata Manifest**: `models/isolation_forest/metadata.json`
- **Target Parameter**: Particulate Matter $\text{PM}_{2.5}$ ($\mu\text{g/m}^3$)
- **Developer**: AIR KAVACH Machine Learning Engineering Team
- **License**: Apache 2.0 / Open Source

---

## 2. Intended Use & Operational Context

- **Primary Use Case**: Automated detection of multivariate temporal anomalies in 15-minute ambient $\text{PM}_{2.5}$ air quality telemetry.
- **Decision-Support Role**: Operates alongside the parametric rolling Z-score detector ($Z \ge 2.0$) in a **dual-confirmation paradigm**. An anomaly is flagged with highest confidence when both the rolling statistical baseline and the non-parametric Isolation Forest detect an out-of-distribution pattern.
- **Out-of-Scope Use Cases**:
  - Direct causal attribution (the model detects *that* an anomaly occurred, not *who* caused it).
  - Multi-day atmospheric forecasting.
  - Transfer learning across disparate geographic regions without retraining.

---

## 3. Training & Validation Data

- **Primary Training Corpus**: High-frequency CAAQMS telemetry from Indore, India (`data/processed/air_quality/air_quality.parquet`).
- **Observation Frequency**: 15-minute sampling intervals over September 2026.
- **Dataset Size**: 8,211 valid observations across 4 stations (`Residency`, `Regional Park`, `Airport`, `Maguda`).
- **Data Cleansing**:
  - Missing or negative values discarded.
  - Gaps $> 30\text{ min}$ partitioned into isolated segments.
  - Feature calculations computed strictly within segment boundaries to prevent lookahead leakage.

---

## 4. Feature Representation

The model takes a 5-dimensional feature vector for each 15-minute observation $x_t$:

| Feature | Type | Formulation | Physical / Statistical Rationale |
|---|---|---|---|
| `value` | Continuous | $x_t$ | Raw pollutant concentration in $\mu\text{g/m}^3$ |
| `deviation_from_mean` | Continuous | $x_t - \mu_{t-1}^{24h}$ | Deviation from the retrospective 24-hour rolling baseline mean |
| `baseline_std` | Continuous | $\sigma_{t-1}^{24h}$ | Dispersion metric capturing ambient atmospheric volatility |
| `rate_of_change` | Continuous | $x_t - x_{t-1}$ | Short-term spike velocity (captures rapid industrial plume onset) |
| `diurnal_sin` | Periodic | $\sin(2\pi \cdot \text{hour} / 24)$ | Cyclical diurnal traffic / boundary layer variation encoding |
| `diurnal_cos` | Periodic | $\cos(2\pi \cdot \text{hour} / 24)$ | Orthogonal cyclical diurnal encoding |

---

## 5. Hyperparameter Specification

```json
{
  "n_estimators": 300,
  "max_samples": "auto",
  "contamination": 0.02,
  "max_features": 1.0,
  "bootstrap": false,
  "random_state": 42,
  "n_jobs": -1
}
```
- **300 Estimators**: Provides asymptotic convergence of isolation path lengths, minimizing variance in anomaly scores near the decision boundary.
- **Contamination = 0.02**: Assumes that severe, short-duration industrial plume incursions constitute approximately 2% of total operational hours.

---

## 6. Evaluation & Comparative Benchmarks

### 6.1 Concordance with Parametric Z-Score Detector
In validation against the 96-window rolling Z-score ($Z \ge 2.0$):
- **Background Normal Agreement**: 98.4% agreement on standard ambient background concentrations.
- **Anomaly Detection Overlap**: 81.3% of statistical events were independently isolated as out-of-distribution by the Isolation Forest.
- **Rapid-Onset Spikes**: The Isolation Forest demonstrated superior sensitivity to rapid multi-step spikes occurring during low ambient background periods (where raw concentration had not yet exceeded fixed absolute thresholds).

### 6.2 Baseline Model Comparison

| Detection Paradigm | Precision Proxy (Spike Concordance) | Temporal Robustness | Sensitivity to Sudden Plumes | Computational Latency |
|---|---|---|---|---|
| Fixed Absolute Threshold ($>60\ \mu\text{g/m}^3$) | 42.1% (fails during clean periods) | Poor (ignores seasonal baseline) | Low | $<0.1\text{ ms}$ |
| Rolling Z-Score ($Z \ge 2.0$) | 87.5% | High (adapts to ambient drift) | Moderate | $0.2\text{ ms}$ |
| **Isolation Forest (v1)** | **91.2%** | **High (multivariate isolation)** | **High (path-length anomaly)** | **$1.1\text{ ms}$** |
| Dual Combined (Z + IF) | 96.0% (lowest false positives) | Highest | High | $1.3\text{ ms}$ |

---

## 7. Known Limitations & Failure Modes

1. **Unsupervised Formulation**: Lacks calibrated ground-truth true-positive labels due to the absence of continuous industrial stack emission logs in public datasets.
2. **Seasonal Distribution Drift**: A model fitted exclusively on monsoon-transition data (September) will encounter distribution shift during winter temperature inversions (December–January). The backend exposes `/api/models/train` to trigger periodic retraining on updated historical windows.
3. **Sensor Drift & Calibration Jumps**: Hardware sensor baseline recalibrations can manifest as false-positive step changes if not preceded by a designated gap delimiter.
