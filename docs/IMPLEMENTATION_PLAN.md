# AIR KAVACH - Master Implementation Plan

**Project:** AIR KAVACH (Agentic Industrial Pollution Source Attribution and Environmental Intelligence Platform)  
**Target Execution:** Comprehensive, Integrated, Real-Data Driven, Deployment-Ready Engine  

---

## 1. Architectural Overview

AIR KAVACH is organized as a modular analytical platform combining real air quality observations, meteorological wind vectors, industrial facility spatial mapping, statistical & ML anomaly detection, heuristic source attribution, an agentic analytical assistant, and an interactive decision-support UI.

```
+-----------------------------------------------------------------------------------+
|                                 AIR KAVACH UI                                     |
|    (React + Vite + Leaflet Maps + Vanilla CSS Design System #F7F8F6 / #1D3557)    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                                FastAPI BACKEND                                    |
|   (Endpoints: Summary, Events, Attribution, Models, Ingestion, Agent, Reports)   |
+-----------------------------------------------------------------------------------+
       |                    |                    |                   |
       v                    v                    v                   v
+--------------+    +--------------+    +----------------+   +-------------------+
|  Ingestion   |    | ML Isolation |    | Event Detector |   | Agentic Tool      |
|  & Freshness |    | Forest Engine|    | & Incremental  |   | Orchestration     |
|  (OpenAQ)    |    | (Joblib/v1)  |    | Processing     |   | (Trace & Routing) |
+--------------+    +--------------+    +----------------+   +-------------------+
       |                    |                    |                   |
       +--------------------+--------------------+-------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                               ANALYTICAL STORAGE                                  |
|         Parquet Datasets / Stored Models / Evidence JSON / PDF Reports            |
+-----------------------------------------------------------------------------------+
```

---

## 2. Approved Color Palette & Visual Guidelines

AIR KAVACH strictly adheres to the approved brand palette:

- **Background (`#F7F8F6`):** Warm neutral main app background.
- **Surface (`#FFFFFF`):** Cards, panels, modal dialogs, data tables, map controls.
- **Primary (`#1D3557`):** Primary navigation headers, main CTAs, core titles.
- **Primary Hover (`#29486F`):** Interactive button/link hover states.
- **Primary Text (`#24313D`):** High-contrast body typography and headers.
- **Secondary Text (`#64748B`):** Subtitles, meta tags, table headers, captions.
- **Border (`#E1E6E5`):** Subtle card borders, grid dividers, table row strokes.
- **Accent (`#3C8D91`):** Environmental highlights, selected map nodes, active tabs.
- **Critical (`#DC4545`):** High pollution spikes, severe z-scores, critical alerts.
- **Warning (`#D99526`):** Elevated readings, missing wind vector warnings.
- **Success (`#27845B`):** Data freshness OK, normal background levels, healthy services.

---

## 3. Phased Execution Roadmap

### Phase 1: Repository Audit & Planning (COMPLETE)
- Audit existing files, datasets, scripts, backend endpoints.
- Generate `docs/PROJECT_AUDIT.md` and `docs/IMPLEMENTATION_PLAN.md`.

### Phase 2: System Architecture & Data Schema Standardization
- Create `.env.example` with clean placeholders.
- Establish Python logger module (`src/utils/logger.py`).
- Define core data models (Pydantic / Dataclasses) for Observations, Events, Facilities, Wind, Attribution, Evidence, and Execution Traces.

### Phase 3: Real-Data Ingestion Pipeline
- Build `src/ingestion/openaq_ingestion.py` for live/incremental fetching from OpenAQ API v3.
- Implement rate-limit retry with exponential backoff, request timeout, timestamp normalization (UTC), deduplication, and ingestion history tracking.

### Phase 4: Machine Learning Lifecycle & Artifact Management
- Refactor `src/ml/isolation_forest_service.py` to support training, joblib serialization, loading, and inference.
- Store artifacts under `models/isolation_forest/model_v1.joblib` with `metadata.json`.
- Implement safe fallback when model artifact is missing or dataset is insufficient.

### Phase 5: Incremental Pollution Event Processing
- Modularize `src/event_detection/event_processor.py` to ingest new observations, compute 96-reading rolling baselines, execute z-score spike detection, and merge consecutive spike periods into event records.
- Preserve 51 baseline events while supporting incremental updates.

### Phase 6: Geospatial & Wind Alignment Attribution Engine
- Refactor `src/attribution/attribution_engine.py` for real-time and batch scoring.
- Calculate circular angle difference between station-to-factory bearing and meteorological wind direction (FROM convention).
- Calculate exponential distance score ($e^{-d / 5.0}$).
- Evaluate relative attribution score share and assign confidence/evidence labels (`strong_geospatial_wind_evidence`, `no_reliable_source`, etc.).

### Phase 7: Agentic Tool Orchestration & Execution Traces
- Build `src/agent/orchestrator.py` with structured tool registry (`air_quality_query`, `station_lookup`, `event_investigation`, `isolation_forest_inference`, `attribution_scoring`, `report_generation`).
- Implement deterministic task classifier and fallback execution when LLM API keys are unconfigured.
- Expose complete JSON execution traces containing Request ID, Task Type, Selected Tools, Validation Results, and Outcome.

### Phase 8: FastAPI Backend Enhancement
- Extend `backend/main.py` with modular routers:
  - `/api/summary` (enhanced with system status & freshness)
  - `/api/events` & `/api/events/{event_id}`
  - `/api/attribution/{event_id}` & `/api/evidence/{event_id}`
  - `/api/map` & `/api/map/events/{event_id}`
  - `/api/models/status` & `/api/models/train`
  - `/api/ingestion/status` & `/api/ingestion/run`
  - `/api/assistant/investigate` (Agentic API)
  - `/api/reports` (PDF/JSON Export API)

### Phase 9: Frontend Web Application (React + Vite + Leaflet)
- Initialize React app in `frontend/` using Vite + TypeScript / JS.
- Implement CSS design system tokens in `frontend/src/index.css` matching approved palette (#F7F8F6, #1D3557, #3C8D91, etc.).
- Build all 12 required interactive pages/views:
  - **Landing Page:** Hero, methodology breakdown, station summary stats, quick launch.
  - **Main Dashboard:** Key platform metrics, data freshness, active events, quick actions.
  - **Monitoring:** Station selection, parameter selection, interactive concentration timeline chart.
  - **Pollution Events:** Paginated event list, peak concentration filters, z-score indicators.
  - **Event Workspace:** Deep-dive investigation workspace, station details, wind vector, candidate table.
  - **Interactive Map:** Leaflet map with station markers, event epicenters, industrial facility icons, wind vectors, and distance lines.
  - **Source Attribution:** Detailed breakdown of candidate factories, distance vs wind alignment, evidence labels.
  - **AI Assistant:** Interactive query UI for natural language investigations with tool trace viewer.
  - **Model Monitoring:** Isolation Forest model status, feature schemas, score distributions, statistical vs ML agreement.
  - **Data Sources & Quality:** Live ingestion status, raw observation counts, rejected record counts, data dictionary.
  - **Reports & History:** Exportable investigation reports (JSON/HTML/PDF view).
  - **Settings & System Status:** Service health, API configuration, dataset retention policy.

### Phase 10: Report Generation Engine
- Build `src/reports/report_generator.py` for exporting structured PDF & JSON report artifacts.
- Include data provenance, peak readings, wind observations, top candidate rankings, evidence caveats, and agent execution trace.

### Phase 11: Automated Pytest Suite
- Build comprehensive unit and integration tests in `tests/`:
  - `test_ingestion.py`
  - `test_event_detection.py`
  - `test_ml_model.py`
  - `test_attribution.py`
  - `test_backend_api.py`
  - `test_agent_orchestrator.py`
- Execute pytest and verify 100% pass rate.

### Phase 12: Production Deployment & Containerization
- Create `backend/Dockerfile` and `frontend/Dockerfile`.
- Create `docker-compose.yml` for unified execution.
- Create `docs/DEPLOYMENT.md`, `docs/API.md`, `docs/DATA_DICTIONARY.md`, `docs/SCIENTIFIC_LIMITATIONS.md`, `docs/USER_GUIDE.md`.

### Phase 13: Final End-to-End Verification & Engineering Report
- Conduct runtime verification of backend services and frontend UI.
- Write final engineering report summarizing completed features, test results, and startup instructions.
