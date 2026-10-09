# AIR KAVACH - Model Card: Isolation Forest Anomaly Detection

## Model Overview

- **Model Name:** Station-Specific Isolation Forest Baseline
- **Model Version:** 1.0.0
- **Artifact Path:** `models/isolation_forest/isolation_forest_v1.joblib`
- **Metadata Path:** `models/isolation_forest/metadata.json`
- **Framework:** `scikit-learn` (`sklearn.ensemble.IsolationForest`)

## Intended Use

- **Task:** Identify statistical and temporal air quality anomalies in PM2.5 time series.
- **Input Features:** `value`, `deviation` (value - past_mean), `past_std`, `hour_sin`, `hour_cos`.
- **Pre-processing:** Continuous 15-minute time segmentation (gaps >15 min split into separate segments) to prevent temporal data leakage across missing intervals.

## Model Hyperparameters

- `n_estimators`: 300
- `contamination`: 0.02
- `random_state`: 42
- `n_jobs`: -1

## Evaluation & Findings

- **Unsupervised Model:** Trained without ground-truth anomaly labels.
- **Agreement with Statistical Detector:** Exhibited ~82% agreement with rolling z-score baseline on non-anomalous background points.
- **Chronological Stability:** Chronological holdout tests indicated potential distribution drift over multi-month observation windows, recommending periodic retrains via `/api/models/train`.
