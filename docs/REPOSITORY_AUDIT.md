# AIR KAVACH - REPOSITORY AUDIT REPORT
**Date**: October 2026  
**Auditor**: Principal Architecture & Environmental Engineering Team  
**System**: Pan-India Industrial Pollution Source Attribution and Environmental Intelligence Platform  
**Target Geographical Scope**: Pan-India First (Initial Validation: Indore, MP)

---

## 1. Executive Summary

A comprehensive, ground-truth audit of the AIR KAVACH repository was conducted at `c:\Users\ayush\Desktop\AIR-KAVACH`. 
The repository contains substantial analytical foundations for environmental investigation in the Indore, Madhya Pradesh region, including 8,211 high-frequency 15-minute PM2.5 readings, 10,012 meteorological observations, 27 mapped industrial facilities (26 active source candidates), 51 detected pollution events, an Isolation Forest anomaly detection model artifact, and preliminary FastAPI and React-Vite dashboards.

However, several critical structural and scientific gaps were identified:
1. **Geographical Scope Hardcoding**: The application logic, map centers, API routes, and frontend dropdowns were tightly coupled to 4 Indore stations (`Airport`, `Maguda`, `Regional Park`, `Residency`), lacking Pan-India geographical hierarchies, state/city filters, and regional data coverage indicators.
2. **Event Detection Baseline Leakage**: The rolling window in `event_processor.py` included the current observation in its own baseline mean and std (`x.rolling()` instead of `shift(1)`), risking baseline contamination during sustained spikes.
3. **Agentic AI Orchestration**: `src/agent/orchestrator.py` utilized basic keyword matching without a formalized typed tool registry, input validation, tool timeouts, or transparent multi-step tool execution traces.
4. **API Completeness**: Endpoints for regional coverage (`/api/coverage`), stations metadata (`/api/stations`), system readiness (`/ready`), ingestion jobs (`/api/ingestion/jobs`), and persistent reports history were incomplete or missing.
5. **Frontend Status Realism**: Settings and landing page metrics had static hardcoded fallback text rather than real-time binding to dynamic backend responses.

All valid existing datasets and analytical models have been preserved. This audit outlines the current state and guides the full production refactor.

---

## 2. Existing Architecture & Components

```
AIR-KAVACH/
├── backend/
│   ├── main.py                     # FastAPI application (v2.0.0)
│   ├── map_data.json               # Serialized GeoJSON/map cache (51 events, 153 candidate pairs)
│   └── Dockerfile                  # Python 3.11-slim containerfile
├── frontend/
│   ├── src/
│   │   ├── api.js                  # Frontend API client
│   │   ├── App.jsx                 # Main navigation & shell
│   │   ├── index.css               # Exact approved brand palette & design tokens
│   │   └── pages/                  # 12 React views (Landing, Dashboard, Monitoring, etc.)
│   ├── package.json                # React 18, Vite 8.3, Leaflet, Lucide icons
│   └── dist/                       # Vite production build output
├── src/
│   ├── agent/orchestrator.py       # Agentic investigation orchestrator
│   ├── attribution/                # Attribution scoring & confidence calculation
│   ├── event_detection/            # Statistical rolling z-score detector
│   ├── features/                   # Haversine distance, wind vectors, ML feature pipelines
│   ├── ingestion/                  # OpenAQ v3 ingestion service
│   ├── ml/                         # Isolation Forest training, evaluation, holdout scripts
│   ├── preprocessing/              # Parquet preparation utilities
│   ├── reference_data/             # XKDR 2024 daily reference scripts
│   └── utils/                      # Config, logging, schemas
├── data/
│   ├── processed/                  # Canonical Parquet datasets
│   └── features/                   # Derived feature & confidence Parquets
├── models/
│   └── isolation_forest/           # isolation_forest_v1.joblib (22.6 MB) & metadata.json
├── reports/generated/              # Statistical evaluations, drift diagnostics, sensitivity reports
└── tests/                          # 5 initial test suites (9 passing with PYTHONPATH=.)
```

---

## 3. Data Assets Verification

Every parquet asset was inspected directly via Pandas for schema, row counts, and timestamp integrity:

| Asset Path | Row Count | Columns / Schema | Status |
|:---|:---:|:---|:---:|
| `data/processed/air_quality/air_quality.parquet` | 8,211 | `station`, `sensor_id`, `timestamp`, `parameter`, `value`, `unit` | Verified (Sept 2026, 4 Indore stations, 15-min PM2.5) |
| `data/processed/air_quality/xkdr_daily_2024.parquet` | 5,691 | `station_id`, `parameter_name`, `unit`, `period_start`, `mean`, `min`, `max`, `n`, etc. | Verified (Full year 2024 daily reference data) |
| `data/processed/events/pollution_events.parquet` | 51 | `event_id`, `station`, `start_time`, `end_time`, `duration_minutes`, `peak_pm25`, `peak_time`, `peak_z_score`, `mean_pm25`, `baseline_mean`, `max_z_score`, `readings` | Verified (Detected spikes z >= 2.0) |
| `data/processed/factories/factories_clean.parquet` | 27 | `factory_id`, `factory_name`, `industry_type`, `latitude`, `longitude`, `operator`, `source`, `facility_category`, `source_candidate` | Verified (26 active candidate facilities, 1 non-candidate) |
| `data/processed/weather/wind.parquet` | 10,012 | `timestamp`, `wind_direction_deg`, `wind_speed_mps`, `station` | Verified (Direction: 10,012 valid; Speed: 7,868 valid) |
| `data/features/sensor_factory_distances.parquet` | 104 | `sensor`, `sensor_latitude`, `sensor_longitude`, `factory_id`, `factory_name`, `facility_category`, `factory_latitude`, `factory_longitude`, `distance_km` | Verified (4 stations × 26 facilities) |
| `data/features/event_factory_attribution.parquet` | 1,326 | `event_id`, `station`, `factory_id`, `factory_name`, `facility_category`, `peak_pm25`, `distance_km`, `distance_score`, `wind_direction_mean_deg`, `wind_speed_mean_mps`, `wind_coverage`, `bearing_sensor_to_factory_deg`, `bearing_factory_to_sensor_deg`, `wind_angle_difference_deg`, `wind_alignment`, `attribution_score`, `relative_likelihood`, `factory_rank`, `source_identification_status`, `evidence_label` | Verified (51 events × 26 facilities) |
| `data/features/event_factory_confidence.parquet` | 1,326 | Subset of attribution featuring confidence & uncertainty indices | Verified |
| `data/features/pollution_events_with_wind.parquet` | 51 | 51 events merged with aligned meteorological observations | Verified |
| `data/features/ml_anomaly_scores.parquet` | 8,211 | Rolling features, cyclic hours, Isolation Forest scores & flags | Verified |
| `backend/map_data.json` | 51 events | Top 3 candidates per event (153 records total), stations, sensors | Verified |

---

## 4. Machine Learning & Model Verification

- **Artifact**: `models/isolation_forest/isolation_forest_v1.joblib` exists, size ~22.6 MB.
- **Metadata**: `metadata.json` confirms:
  - Architecture: Station-specific Isolation Forest + Unified global fallback.
  - Hyperparameters: 300 estimators, contamination = 0.02, `random_state=42`.
  - Feature Schema: `['value', 'deviation', 'past_std', 'hour_sin', 'hour_cos']`.
  - Samples: 7,810 usable training observations.
- **Historical Feature Rigor**: `IsolationForestService.prepare_features` uses `s.shift(1).rolling(96, min_periods=24)` and segment gap detection (`gap_minutes > 15`), ensuring strict historical-only rolling windows without future data leakage.

---

## 5. Broken or Incomplete Functionality Identified

1. **Geographic Rigidness**:
   - Hardcoded stations in `backend/main.py` summary endpoint.
   - Frontend components lacked region filters (Country, State/UT, City, District).
   - Ingestion service hardcoded to 4 OpenAQ sensor IDs.
2. **Baseline Contamination in Event Processor**:
   - `src/event_detection/event_processor.py` called `.rolling(96)` on current observation instead of `.shift(1).rolling(96)`.
3. **Agentic Orchestrator**:
   - Lacked a formalized, typed Tool Registry.
   - Did not provide granular execution traces for individual tool runs, parameters, and outputs.
   - Lacked explicit handling for queries spanning other states or unknown regions.
4. **Missing API Endpoints**:
   - `GET /ready` (readiness probe).
   - `GET /api/stations` (stations metadata and coordinates).
   - `GET /api/coverage` (state/city data coverage statuses across India).
   - `GET /api/system/status` (unified backend and storage health).
   - `GET /api/ingestion/jobs` (historical job runs).
   - `GET /api/models/versions` (model registry history).
5. **Frontend State Handling**:
   - Settings page rendered hardcoded static badges.
   - Map page had hardcoded Indore coordinates without auto-centering or Pan-India exploration.

---

## 6. Implementation Sequence

1. **Phase 1: Geographic Domain Architecture & Registry**
   - Create `src/geo/registry.py` with normalized entities (`GeographicRegion`, `MonitoringStation`, `CoverageStatus`).
   - Define multi-region coverage matrix across India (Madhya Pradesh/Indore active; Delhi, Maharashtra, Gujarat, etc. with truthful coverage states).
2. **Phase 2: Analytics & Scientific Corrections**
   - Fix `event_processor.py` past-only rolling window (`shift(1)`) and consecutive temporal gap handling.
   - Refactor `attribution_engine.py` and `distance.py` to use dynamic geographic station and facility metadata.
   - Verify circular angular math and wind "FROM" vector convention with dedicated tests.
3. **Phase 3: Agentic Tool Registry & Orchestration**
   - Implement `src/agent/tools.py` with 14 typed, allowlisted tools.
   - Refactor `src/agent/orchestrator.py` to execute tools sequentially with typed arguments, validation, timeout guards, and comprehensive execution traces.
4. **Phase 4: Backend API Contract Completion**
   - Implement all required Section 14 endpoints in `backend/main.py`.
   - Add input validation, query filters (country, state, city, district, station, pollutant), and structured error responses.
5. **Phase 5: Frontend Transformation**
   - Update `api.js` with all endpoints.
   - Add a global Pan-India Region Selector component.
   - Align `LandingPage.jsx` with Section 17 editorial specifications.
   - Update `InteractiveMapPage.jsx` with dynamic region centering, layer toggles, and coverage warnings.
   - Connect `MainDashboard.jsx`, `SettingsPage.jsx`, `DataSourcesPage.jsx`, and `ReportsPage.jsx` to live APIs.
6. **Phase 6: Testing & Scientific Verification**
   - Write comprehensive unit, integration, API, and scientific tests.
   - Validate that unrelated regions return honest empty/coverage states without Indore leakage.
7. **Phase 7: Deployment & Documentation**
   - Verify Dockerfiles, docker-compose, and generate final verification reports.
