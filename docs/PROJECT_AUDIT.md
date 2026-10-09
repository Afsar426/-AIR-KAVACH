# AIR KAVACH - System & Repository Audit

**Date:** October 9, 2026  
**Project Name:** AIR KAVACH  
**Project Type:** Agentic Industrial Pollution Source Attribution and Environmental Intelligence Platform  
**Target Region / Case Study:** Indore, Madhya Pradesh, India (2024–2026)

---

## 1. Existing Architecture

AIR KAVACH is structured as a Python-based analytical engine with a preliminary FastAPI backend. The repository currently contains:
- **Data Pipelines:** Ingestion scripts for OpenAQ, OpenStreetMap (factories), and Era5/OpenAQ wind observations (`src/ingestion/`, `src/preprocessing/`, `src/reference_data/`).
- **Data Storage:** Preprocessed Parquet analytical storage files (`data/processed/`, `data/features/`, `data/raw/`).
- **Event Detection:** Statistical baseline rolling z-score detector (`src/event_detection/detector.py`).
- **Feature Engineering:** Distance calculation (`src/features/distance.py`), wind alignment (`src/features/wind_alignment.py`), and temporal features (`src/features/prepare_ml_features.py`).
- **Isolation Forest Baseline:** Station-specific Isolation Forest model experiment script (`src/ml/anomaly_baseline.py`).
- **Attribution & Confidence Engine:** Heuristic source candidate ranking (`src/attribution/scoring.py`) and confidence evaluation (`src/attribution/confidence.py`).
- **Evidence & Map Data Generation:** Evidence chain builder (`src/evidence/evidence_chain.py`) and static map JSON export (`src/evidence/map_data.py`).
- **FastAPI Backend:** Endpoint API service (`backend/main.py`) exposing summary stats, event lists, event detail, heuristic attribution, confidence evidence, and map data.

---

## 2. Existing Datasets

The repository contains the following datasets in `data/`:

| Dataset Name | File Path | Format | Records | Key Fields / Details |
|---|---|---|---|---|
| **Air Quality (Primary)** | `data/processed/air_quality/air_quality.parquet` | Parquet | 8,211 | `station`, `sensor_id`, `timestamp`, `parameter`, `value`, `unit` (15-min interval, 2026) |
| **Historical 2024 AQ (XKDR)** | `data/processed/air_quality/xkdr_daily_2024.parquet` / `.csv` | Parquet/CSV | 5,691 | Daily station readings for 5 Indore stations across 4 pollutants (`pm25`, `pm10`, `no2`, `so2`) |
| **Pollution Events** | `data/processed/events/pollution_events.parquet` | Parquet | 51 | `event_id`, `station`, `start_time`, `end_time`, `duration_minutes`, `peak_pm25`, `peak_z_score` |
| **Industrial Facilities** | `data/processed/factories/factories_clean.parquet` | Parquet | 26 | `factory_id`, `factory_name`, `facility_category`, `latitude`, `longitude` (Indore region) |
| **Wind Data** | `data/processed/weather/wind.parquet` | Parquet | 10,012 | `timestamp`, `station`, `wind_direction_deg`, `wind_speed_mps` |
| **Sensor-Factory Distances** | `data/features/sensor_factory_distances.parquet` | Parquet | 104 | 4 stations × 26 candidate factories distance matrix |
| **Attribution Output** | `data/features/event_factory_attribution.parquet` | Parquet | 1,326 | 51 events × 26 candidate factories heuristic attribution scores |
| **Confidence Output** | `data/features/event_factory_confidence.parquet` | Parquet | 1,326 | Heuristic confidence and evidence classifications |
| **ML Anomaly Scores** | `data/features/ml_anomaly_scores.parquet` | Parquet | 8,211 | Isolation Forest decision scores, past z-scores, cyclic time features |
| **Map Data** | `backend/map_data.json` | JSON | 336 KB | Pre-packaged geospatial map records for frontend rendering |

---

## 3. Data Source Coverage

1. **Air Quality Stations (4 active stations in 2026 dataset):**
   - `Residency`: 2,625 readings
   - `Regional Park`: 2,571 readings
   - `Maguda`: 2,064 readings
   - `Airport`: 951 readings
   *Note:* The sampling periods and lengths differ across stations. Coverage is non-uniform.
2. **Industrial Facilities (26 clean facilities):**
   - Mapped facilities in and around the Indore industrial belts (Sanwer Road Industrial Area, Pithampur, Dewas Road).
3. **Wind Data Coverage:**
   - 10,012 observations. Station `Maguda` has wind direction observations but lacks wind speed data in certain intervals.

---

## 4. Existing ML Implementation

- **Script:** `src/ml/anomaly_baseline.py`
- **Algorithm:** Station-specific `IsolationForest` from `scikit-learn` (300 trees, contamination=0.02, random_state=42).
- **Features Used:** `value` (PM2.5), `deviation` (value - past_mean), `past_std`, `hour_sin`, `hour_cos`.
- **Segmentation & Gap Handling:** 96-observation rolling window (24 hours at 15-min sampling). Data is split into continuous segments when gaps exceed 15 minutes to prevent leakage across missing periods.
- **Outputs generated:** `data/features/ml_anomaly_scores.parquet` and CSV/JSON reports under `reports/generated/`.
- **Findings:** Statistical baseline (rolling z-score >= 2.0) and Isolation Forest exhibit partial disagreement (~82% agreement on unflagged non-anomalous points, but lower overlap on peak anomalies).

---

## 5. Existing Model Artifacts

- Currently, `models/isolation_forest/` contains no saved `.joblib` model artifacts. Models are trained on-the-fly inside execution scripts and not serialized for persistent deployment.
- **Requirement:** Implement robust model serialization (`joblib`), versioning metadata, schema validation, and safe inference loading.

---

## 6. Event Detection Logic

- **Module:** `src/event_detection/detector.py`
- **Methodology:** 
  - Rolling mean & rolling standard deviation over 96 observations (min periods = 24).
  - Calculates z-score: $(x - \mu) / \sigma$.
  - Flagged as spike if `z_score >= 2.0` AND `value > rolling_mean`.
  - Groups consecutive spike readings per station.
  - Requires minimum 4 consecutive 15-minute readings (1 hour minimum duration).
  - Summary stats: `start_time`, `end_time`, `peak_pm25`, `peak_z_score`, `mean_pm25`, `baseline_mean`.
- **Baseline Result:** 51 historical events detected across the 4 stations in the 2026 dataset.

---

## 7. Source Attribution Logic

- **Modules:** `src/attribution/scoring.py` and `src/attribution/confidence.py`
- **Methodology:**
  - **Distance Decay:** Exponential decay $e^{-d / 5.0}$ where $d$ is station-to-factory distance in kilometers.
  - **Wind Alignment:** Compares meteorological wind direction (FROM convention) with station-to-factory bearing angle $\theta$:
    $$\text{alignment} = \cos(\theta_{\text{sensor}\to\text{factory}} - \text{wind\_dir\_from})$$
  - **Attribution Score:** $0.70 \times \max(0, \text{alignment}) + 0.30 \times \text{distance\_score}$.
  - **Relative Likelihood:** Share of score among all 26 candidate factories for a given event ($\text{score} / \sum \text{scores}$).
  - **No-Reliable-Source Threshold:** If max score $< 0.35$ or wind data is unavailable, status is set to `no_reliable_source`.
- **Caveat:** Heuristic screening score, NOT a calibrated probability or proof of legal guilt.

---

## 8. Existing Backend APIs

- **Framework:** FastAPI (`backend/main.py`)
- **Endpoints Available:**
  - `GET /` - API Root status
  - `GET /health` - System file health check
  - `GET /api/summary` - Aggregated observation/event/station summary
  - `GET /api/events` - Paginated & filtered pollution event list
  - `GET /api/events/{event_id}` - Event details
  - `GET /api/attribution/{event_id}` - Top candidate factories for an event
  - `GET /api/evidence/{event_id}` - Event evidence chain & confidence breakdown
  - `GET /api/map` - Entire geospatial map dataset
  - `GET /api/map/events/{event_id}` - GeoJSON/JSON features for a specific event
- **Status:** Functional for reading static pre-generated Parquet files. Lacks ingestion triggering, live inference, LLM/Agentic tool orchestration, model status/retraining endpoints, or report generation.

---

## 9. Existing Frontend Functionality

- `frontend/` directory is currently **empty**. No React/Vite app or HTML UI is currently implemented in `frontend/`.
- **Requirement:** Build a modern, high-grade Web UI using React + Vite + Vanilla CSS matching the exact approved color palette (#F7F8F6 background, #1D3557 primary, #3C8D91 accent, etc.) with Leaflet maps, Interactive Dashboards, Event Workspaces, AI Assistant, Model Monitoring, and Data Ingestion status.

---

## 10. Existing Test Coverage

- `tests/` directory is currently **empty**. No automated `pytest` test suite exists for unit/integration validation.
- **Requirement:** Build comprehensive unit, integration, data consistency, and failure test suites in `tests/`.

---

## 11. Data-Quality Limitations

- Station data coverage varies (residency has ~2.6k points vs airport with <1k).
- Missing wind speed and direction in certain intervals (especially Maguda station).
- Missing live continuous feed (currently relying on historical batch parquet data).
- Lack of verified stack emissions data for industrial facilities (attribution relies purely on spatial proximity and meteorological wind direction).

---

## 12. Scientific Limitations

- Screening heuristic is **not** an atmospheric dispersion model (e.g. AERMOD, HYSPLIT, CAMx).
- Does not account for stack height, plume rise, terrain topology, ambient temperature lapse rates, atmospheric stability class, or chemical transformations.
- Relative likelihood shares are heuristic weights, not calibrated posterior probabilities.
- Absence of ground-truth labeled pollution events or verified industrial emission logs.

---

## 13. Security Issues

- CORS configuration in `backend/main.py` currently allows localhost origins without API token authorization.
- Missing credentials verification in OpenAQ downloader.
- Sensitive environment configurations should be externalized via `.env`. `.env.example` must be provided without secret exposure.

---

## 14. Deployment Readiness

- No Dockerfile or `docker-compose.yml` present in `backend/` or `frontend/`.
- Backend lacks automated background task execution for ingestion or retraining.
- Frontend build assets need production compilation via Vite.

---

## 15. Missing Features & Integration Gaps

1. **Frontend UI:** Complete lack of UI in `frontend/`. All 12 required pages/views need to be built.
2. **Model Lifecycle:** Missing serialized model artifacts (`.joblib`) and automated inference runtime.
3. **Incremental Ingestion & Event Processing:** Missing live/incremental ingestion worker that detects new events upon fresh data arrival.
4. **Agentic Task Orchestration:** Missing natural language investigation assistant and tool registry trace system.
5. **Report Generator:** Missing automated PDF/JSON report compilation system.
6. **Automated Test Suite:** Missing unit, integration, and data validation test cases.

---

## 16. Implementation Priorities

1. **Phase 1:** Complete System Audit & Implementation Plan (`docs/PROJECT_AUDIT.md`, `docs/IMPLEMENTATION_PLAN.md`).
2. **Phase 2:** Core backend refactoring, schema definitions, environment config, and logging.
3. **Phase 3:** OpenAQ live ingestion module with incremental fetching, rate-limiting, and idempotency.
4. **Phase 4:** Isolation Forest model training, joblib serialization, and versioned inference pipeline (`models/isolation_forest/`).
5. **Phase 5:** Incremental event detection engine and live event record pipeline.
6. **Phase 6:** Wind alignment and heuristic source candidate ranking engine integration.
7. **Phase 7:** Agentic tool orchestration system (`src/agent/`) with deterministic routing fallback and execution traces.
8. **Phase 8:** Complete FastAPI backend endpoints (adding model status, ingestion triggers, investigation agent, report generation).
9. **Phase 9:** Build React + Vite + Leaflet frontend app in `frontend/` matching approved AIR KAVACH styling and design system.
10. **Phase 10:** Evidence report generation engine (JSON/Markdown/HTML export).
11. **Phase 11:** Pytest automated test suite execution and verification.
12. **Phase 12:** Production build configuration (Docker, scripts, deployment documentation).
