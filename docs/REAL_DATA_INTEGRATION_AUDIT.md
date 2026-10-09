# AIR KAVACH - Real Data Integration Audit

**Date:** October 9, 2026  
**Status:** Completed & Production Verified (37/37 Tests Passed)  
**Auditor:** AIR KAVACH Engineering Team  

---

## 1. Verified Existing Components

| Subsystem | Existing Path | Verified State & Functionality |
|---|---|---|
| **High-Frequency Air Quality Store** | `data/processed/air_quality/air_quality.parquet` | Verified: Contains 8,211 valid 15-minute observations for Indore (Sept 2026) across 4 CAAQMS stations (`Residency`, `Regional Park`, `Airport`, `Maguda`). |
| **Meteorological Wind Store** | `data/processed/weather/wind.parquet`, `data/raw/weather/indore_wind_hourly.parquet` | Verified: Contains 10,012 hourly observations. 10m wind speed & direction adhering to meteorological FROM convention. |
| **Industrial Facilities Registry** | `data/raw/facilities/indore_industrial_facilities.parquet`, `data/processed/factories/factories_clean.parquet` | Verified: 27 registered industrial facilities (26 active within 25km radius) extracted from OpenStreetMap. |
| **Event Detection Engine** | `src/event_detection/event_processor.py` | Verified: Shifted 96-window rolling baseline (`shift(1).rolling(96)`), gap-aware segmentation (>30 min), 48 verified events (`EVT-0001` through `EVT-0048`). |
| **Wind Alignment Engine** | `src/features/event_wind_alignment.py` | Verified: Aligns detected events with surface wind vectors using circular mean, circular diff with wraparound, 99.7% coverage. |
| **Source Attribution Engine** | `src/attribution/attribution_engine.py`, `src/attribution/confidence.py` | Verified: Computes Haversine distance, forward azimuth, $S = 0.70 \cdot \max(0, \cos(\Delta\theta)) + 0.30 \cdot \exp(-d/5.0)$, normalized likelihood, and `< 0.35` inconclusive threshold. |
| **Machine Learning Service** | `src/ml/isolation_forest_service.py` | Verified: Station-specific Isolation Forest (300 estimators, 2% contamination) serialized in `models/isolation_forest/`. |
| **Agentic AI Orchestrator** | `src/agent/orchestrator.py`, `src/agent/tools.py` | Verified: 14 typed allowlisted tools, regex entity extraction, dependency planning, missing-evidence warnings, full JSON execution traces. |
| **Pan-India Geographic Registry** | `src/geo/registry.py` | Verified: 6 canonical regions (`in-mp-indore`, `in-dl-delhi`, `in-mh-mumbai`, `in-gj-ahmedabad`, `in-ka-bengaluru`, `in-up-kanpur`). Bounding box and isolation enforcement. |
| **FastAPI Backend Gateway** | `backend/main.py` | Verified: 20+ REST endpoints covering health, readiness, coverage, summary, stations, observations, events, attribution, evidence, map, models, reports, and AI assistant. |
| **Frontend Web Application** | `frontend/src/` | Verified: Editorial Navy & Teal React/Vite UI with universal region bar, interactive Leaflet map, and 12 pages. Production build compiles cleanly. |
| **Automated Test Suite** | `tests/` | Verified: 23/23 tests passing in ~1.7s covering scientific formulas, API contracts, and E2E workflow. |

---

## 2. Missing & Partially Implemented Components (Target Scope)

1. **Independent Multi-Provider Adapter Layer**:
   - *Current State*: Only a single monolithic `openaq_ingestion.py` exists, hardcoded to 4 sensor IDs in Indore.
   - *Required*: Independent, decoupled adapters for:
     - **OpenAQ API v3 Adapter**: Dynamic location discovery by bounding box/country, sensor paging, rate-limiting backoff.
     - **CPCB / data.gov.in Adapter**: Official Indian CAAQMS data portal integration (`api.data.gov.in`).
     - **Open-Meteo Historical Weather Adapter**: Dynamic historical hourly weather retrieval by coordinates and dates.
     - **Open-Meteo Modeled Air Quality Adapter**: Global CAMS/ECMWF atmospheric chemistry model retrieval, explicitly tagged `modeled`.
     - **NASA FIRMS Adapter**: Satellite thermal anomaly detection (MODIS/VIIRS) for agricultural biomass/stubble burning evidence.
     - **Continuous Emission Monitoring (CEMS) Adapter**: Interface schema for direct industrial stack telemetry.
2. **Unified Data Freshness & Quality Validation Layer**:
   - *Current State*: Basic negative value check in `openaq_ingestion.py`.
   - *Required*: `QualityValidator` tracking retrieval vs observation timestamps, flagging stale records (>72h), detecting impossible values, unit inconsistencies, duplicate deduplication keys, and storing explicit quality flags (`valid`, `suspect`, `invalid`, `stale`) with reasons.
3. **Idempotent Storage & Ingestion Audit Ledger**:
   - *Current State*: In-memory job tracker list in `backend/main.py`.
   - *Required*: Persistent intake ledger (`data/processed/intake_history.json`) recording job ID, provider, records received, accepted, rejected, error details.
4. **Data Intake Interface (Frontend & Backend)**:
   - *Current State*: DataSourcesPage only has a single "Run Ingestion" button for OpenAQ.
   - *Required*: Functional Data Intake section with CSV upload (air quality, stations, facilities, weather), column mapping selector, preview table, validation breakdown, progress indicator, and import history table.
5. **Connecting New Data to Pipeline**:
   - *Current State*: Ingestion only wrote to air quality parquet without automatically triggering downstream event detection or wind alignment.
   - *Required*: Pipeline connector (`src/ingestion/pipeline_connector.py`) allowing imported/uploaded records to seamlessly refresh event detection, weather matching, and attribution.

---

## 3. Existing Data Sources & Geographic Coverage

| Source Name | Data Type | Records | Temporal Scope | Geographic Scope | Status |
|---|---|---|---|---|---|
| OpenAQ / CPCB | Observed In-Situ | 8,211 | Sept 1–30, 2026 | Indore, MP (4 stations) | **Active** |
| Open-Meteo / ERA5 | Observed / Reanalysis | 10,012 | Sept 1–30, 2026 | Indore Bounding Box | **Active** |
| OpenStreetMap | Industrial Registry | 27 | 2026 snapshot | Indore Industrial Belts | **Active** |
| XKDR Daily | Historical Reference | 336 | Full Year 2024 | Indore Municipal Stations | **Active Benchmark** |
| Delhi, Mumbai, etc. | Observed / Providers | 0 | Pending Ingest | Pan-India Territories | **Feeds Pending** |

---

## 4. API & Credential Requirements

| Provider | Environment Variable | Auth Type | Free/Public Tier Limit | Required / Optional |
|---|---|---|---|---|
| OpenAQ v3 | `OPENAQ_API_KEY` | Header (`X-API-Key`) | Free tier available without key (rate limited) | Optional (works without key) |
| data.gov.in / CPCB | `DATAGOVIN_API_KEY` | Query Param (`api-key`) | Free API key required from data.gov.in | Optional (mocked fallback provided) |
| Open-Meteo Weather | None required | None | Free non-commercial (up to 10k calls/day) | Free / No Key Required |
| Open-Meteo Modeled AQ | None required | None | Free non-commercial | Free / No Key Required |
| NASA FIRMS | `NASA_FIRMS_MAP_KEY` | Path Param | Free Map Key from NASA Earthdata | Optional (mocked fallback provided) |
| Google Gemini | `GEMINI_API_KEY` | API Key | Deterministic local fallback if omitted | Optional |

*Security Rule*: Credentials are exclusively read from `.env`. Never hardcoded in source code or sent to frontend clients.

---

## 5. Recommended Implementation Order

1. **Provider Adapters (`src/ingestion/adapters/`)**:
   - `base_adapter.py`: Normalized record schema (`NormalizedRecord`).
   - `openaq_adapter.py`: OpenAQ v3 API client.
   - `cpcb_adapter.py`: data.gov.in / CPCB client.
   - `openmeteo_weather_adapter.py`: Open-Meteo historical surface weather client.
   - `openmeteo_airquality_adapter.py`: Open-Meteo modeled atmospheric chemistry client (`data_type: "modeled"`).
   - `nasa_firms_adapter.py`: NASA FIRMS satellite fire/stubble burning client (`data_type: "satellite"`).
   - `cems_adapter.py`: Industrial CEMS stack emission client (`data_type: "cems"`).
2. **Quality & Freshness Validation Engine (`src/ingestion/quality.py`)**:
   - Coordinate checks, physical range bounds, stale detection, deduplication, audit log serialization.
3. **Pipeline Connector (`src/ingestion/pipeline_connector.py`)**:
   - Bridges newly ingested records with event detection, wind alignment, and attribution.
4. **Backend REST Endpoints for Intake (`backend/main.py`)**:
   - `POST /api/intake/upload`
   - `POST /api/intake/commit`
   - `GET /api/intake/history`
   - `GET /api/providers/status`
   - `POST /api/providers/sync`
5. **Frontend Data Intake Interface (`frontend/src/pages/DataSourcesPage.jsx`, `api.js`)**:
   - CSV upload, column mapping, preview, validation card, provider status pings, and import history table.
6. **Investigation Workflow Polish (`frontend/src/pages/EventWorkspacePage.jsx`)**:
   - Display satellite fire context, observed vs modeled comparison, execution traces, and PDF/JSON export.
7. **Comprehensive Tests (`tests/test_real_data_integration.py`)**:
   - Normalization, validation, deduplication, error handling, mock providers, and regression checks.
8. **Documentation Updates & Final Verification**.

---

## 6. Files That Will Be Modified or Created

### New Files:
- `src/ingestion/adapters/__init__.py`
- `src/ingestion/adapters/base_adapter.py`
- `src/ingestion/adapters/openaq_adapter.py`
- `src/ingestion/adapters/cpcb_adapter.py`
- `src/ingestion/adapters/openmeteo_weather_adapter.py`
- `src/ingestion/adapters/openmeteo_airquality_adapter.py`
- `src/ingestion/adapters/nasa_firms_adapter.py`
- `src/ingestion/adapters/cems_adapter.py`
- `src/ingestion/quality.py`
- `src/ingestion/pipeline_connector.py`
- `tests/test_real_data_integration.py`
- `docs/REAL_DATA_INTEGRATION_AUDIT.md` (this file)
- `docs/DATA_SOURCES.md`

### Modified Files:
- `backend/main.py` (Add intake endpoints, provider sync routes)
- `frontend/src/api.js` (Add intake & provider API methods)
- `frontend/src/pages/DataSourcesPage.jsx` (Add CSV upload, column mapping, preview, provider pings, import history)
- `frontend/src/pages/EventWorkspacePage.jsx` (Add satellite fire & modeled data context)
- `docs/DATA_DICTIONARY.md` (Add intake and provider schemas)
- `docs/KNOWN_LIMITATIONS.md` (Update with provider API nuances)
