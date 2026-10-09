# AIR KAVACH - Final System Audit & Technical Verification

**Date:** October 9, 2026  
**Project Name:** AIR KAVACH  
**Project Type:** Agentic Industrial Pollution Source Attribution and Environmental Intelligence Platform  
**Target Region:** Indore, Madhya Pradesh, India (2024–2026)

---

## 1. Baseline Dataset & File Inventory Audit

The actual files and row counts in the workspace `C:\Users\ayush\Desktop\AIR-KAVACH` were verified empirically:

| Dataset Name | File Path | Format | Verified Row Count | Status & Notes |
|---|---|---|---|---|
| **Primary Air Quality** | `data/processed/air_quality/air_quality.parquet` | Parquet | 8,211 | 15-minute high-frequency PM2.5 readings across 4 Indore stations (Sept 2026) |
| **Historical 2024 AQ** | `data/processed/air_quality/xkdr_daily_2024.parquet` | Parquet | 5,691 | Daily historical readings across 5 Indore stations (kept separate from 15-min feed) |
| **Pollution Events** | `data/processed/events/pollution_events.parquet` | Parquet | 51 | Detected events using rolling 96-window z-score (z ≥ 2.0, min 4 readings) |
| **Industrial Facilities** | `data/processed/factories/factories_clean.parquet` | Parquet | 27 | Clean OpenStreetMap mapped industrial facility records in Indore region |
| **Wind Data** | `data/processed/weather/wind.parquet` | Parquet | 10,012 | Hourly meteorological wind vector observations (FROM convention) |
| **Distance Matrix** | `data/features/sensor_factory_distances.parquet` | Parquet | 104 | 4 stations × 26 factory distance matrix pairs (km) |
| **Attribution Output** | `data/features/event_factory_attribution.parquet` | Parquet | 1,326 | 51 events × 26 factories heuristic screening scores |
| **Confidence Output** | `data/features/event_factory_confidence.parquet` | Parquet | 1,326 | Evidence classification labels and confidence breakdown |
| **ML Anomaly Scores** | `data/features/ml_anomaly_scores.parquet` | Parquet | 8,211 | Isolation Forest decision scores, cyclic time features, past z-scores |
| **Map Feature Data** | `backend/map_data.json` | JSON | 336 KB | Pre-packaged geospatial map features for Leaflet UI rendering |
| **ML Model Artifact** | `models/isolation_forest/isolation_forest_v1.joblib` | Joblib | Verified | Serialized station-specific Isolation Forest model payload |

---

## 2. Confirmed Working Functionality

- **Data Ingestion (`src/ingestion/openaq_ingestion.py`):** OpenAQ API v3 client with rate-limiting, exponential backoff, UTC timestamp normalization, schema validation, deduplication, and persistent history.
- **ML Anomaly Service (`src/ml/isolation_forest_service.py`):** Serialized `IsolationForest` models (300 estimators, contamination=0.02) with continuous segment gap splitting (>15 min) to prevent data leakage.
- **Event Detection (`src/event_detection/event_processor.py`):** Rolling 96-reading window z-score spike detector (`Z_THRESHOLD = 2.0`, `MIN_DURATION = 4`).
- **Attribution Engine (`src/attribution/attribution_engine.py`):** Geometric screening engine combining 30% exponential distance decay ($e^{-d / 5.0}$) and 70% meteorological wind vector alignment ($\cos \theta$, FROM convention).
- **Agentic Orchestrator (`src/agent/orchestrator.py`):** Request classifier and tool execution trace logger with deterministic fallback when paid LLM credentials are unconfigured.
- **FastAPI REST Backend (`backend/main.py`):** REST service exposing all required endpoints with CORS and health monitoring.
- **React Frontend (`frontend/`):** SPA built with React, Vite, Leaflet, and Vanilla CSS enforcing the approved palette (`#F7F8F6`, `#1D3557`, `#3C8D91`, `#DC4545`).
- **Pytest Suite (`tests/`):** 9 automated unit/integration tests passing cleanly.

---

## 3. Confirmed Defects & Required Refinements

1. **Visual & Editorial Polish on Landing Page:**
   - Enhance Landing Page hero section with workflow visualization (monitoring stations, detected spike, wind direction, candidate facilities).
   - Add explicit process workflow (Observation → Detection → Investigation → Evidence), scientific transparency disclaimers, data source catalog, and impact cards.
2. **Scientific Transparency & Caveat Enforcement:**
   - Ensure the UI explicitly distinguishes heuristic screening results from calibrated atmospheric dispersion models (such as AERMOD, HYSPLIT, CAMx, or CMAQ).
   - Ensure `relative_likelihood` is clearly labeled as a normalized score share, **not** a probability of causation or proof of legal guilt.
   - Explicitly disclose the absence of ground-truth labeled stack emissions data (no fabricated precision/recall/F1 metrics).
3. **Data Integrity & Resolution Isolation:**
   - Ensure historical 2024 daily reference observations (`xkdr_daily_2024.parquet`) remain separate from 2026 15-minute high-frequency event data.
4. **Live Ingestion vs Historical Analysis Distinction:**
   - UI must clearly distinguish live provider connectivity, last successful ingestion timestamp, latest observation timestamp, and historical analysis mode.

---

## 4. Scientific Risks & Mitigation Strategy

- **Risk:** Users might misinterpret heuristic attribution scores as proof of illegal factory emissions.
- **Mitigation:** Enforce scientific disclaimers on every UI workspace, API summary endpoint, and generated report. Label scores as screening heuristics, non-probabilistic, and decision-support metrics only.

---

## 5. Verification Baseline

- **Pytest Suite:** 9 passed in 2.74s (`python -m pytest`).
- **Vite Build:** Compiled in 181ms (`dist/assets/index-CiEe8s3Y.js`).
