# AIR KAVACH - Testing & Verification Specification

## 1. Testing Philosophy & Quality Principles

In accordance with Rule 5 (*Test implementations, not file existence*) and Rule 6 (*Scientific honesty*), AIR KAVACH enforces a multi-tiered automated test suite covering:
- Exact mathematical and trigonometric implementations (Haversine, azimuth, angular difference).
- Atmospheric physics conventions (meteorological wind **FROM** standard).
- Temporal data hygiene (strictly shifted baselines preventing lookahead leakage).
- Strict geographic boundaries (ensuring non-Indore regions return zero Indore records).
- REST API contracts (20+ endpoints, HTTP status codes, Pydantic model validation).
- Full end-to-end investigation journeys (from user prompt to tool execution traces and persisted report).
- Frontend production bundle integrity (Vite zero-error compilation).

---

## 2. Test Suite Inventory

| Test Module | Test Name | Target Functionality / Assertion | Category | Status |
|---|---|---|---|---|
| `tests/test_scientific_and_pan_india.py` | `test_bearing_cardinal_directions` | Cardinal forward bearings (0° N, 90° E, 180° S, 270° W) within 0.1° | Scientific Unit | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_circular_angle_difference_wraparound` | Minimal angular difference across 0°/360° discontinuity (350° to 10° = 20°) | Scientific Unit | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_wind_from_convention_alignment` | Meteorological FROM convention: Wind from 270° aligning with factory at 270° bearing (+1.0) vs 90° bearing (0.0) | Scientific Unit | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_distance_decay_exponential` | Exponential decay formula: $d=0 \implies 1.0$, $d=5\text{km} \approx 0.368$, monotonic decrease | Scientific Unit | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_pan_india_region_registry` | Registry contains 6 canonical Indian regions with valid bounding boxes | Geospatial Unit | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_no_indore_leakage_on_unrelated_region` | Querying `in-dl-delhi` returns 0 Indore records and truthful `FEEDS_PENDING` | Regional Isolation | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_indore_validation_region_returns_data` | Querying `in-mp-indore` returns active status and real observations | Regional Integration | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_ready_endpoint` | `GET /ready` returns 200 OK and validates core Parquet and ML artifacts | API Contract | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_stations_endpoint` | `GET /api/stations` returns valid station list with coordinates and status | API Contract | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_coverage_endpoint` | `GET /api/coverage` accurately reflects temporal bounds and record counts | API Contract | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_system_status_endpoint` | `GET /api/system/status` reports operational health and cache counters | API Contract | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_ingestion_jobs_endpoint` | `GET /api/ingestion/jobs` reports job history | API Contract | **PASSED** |
| `tests/test_scientific_and_pan_india.py` | `test_reports_lifecycle_endpoint` | `POST /api/reports` creates report, `GET /api/reports/{id}` retrieves it | Lifecycle Integration | **PASSED** |
| `tests/test_attribution.py` | `test_geospatial_calculations` | Verifies Haversine formula and distance bounds against known ground coordinates | Geospatial Unit | **PASSED** |
| `tests/test_event_detection.py` | `test_event_processor` | 96-window shifted rolling baseline and spike clustering into `EVT-XXXX` | Temporal Pipeline | **PASSED** |
| `tests/test_ml_model.py` | `test_isolation_forest_lifecycle` | Feature engineering, joblib serialization, inference, and metadata schema | ML Unit | **PASSED** |
| `tests/test_ingestion.py` | `test_ingestion_status` | OpenAQ ingestion job verification | Data Pipeline | **PASSED** |
| `tests/test_backend_api.py` | `test_root_and_health` | `GET /` and `GET /health` liveness checks | API Unit | **PASSED** |
| `tests/test_backend_api.py` | `test_summary_endpoint` | `GET /api/summary` aggregate counts and scientific caveats | API Unit | **PASSED** |
| `tests/test_backend_api.py` | `test_events_endpoint` | `GET /api/events` pagination and threshold filtering | API Unit | **PASSED** |
| `tests/test_backend_api.py` | `test_attribution_endpoint` | `GET /api/attribution/{id}` candidate rankings and confidence | API Unit | **PASSED** |
| `tests/test_backend_api.py` | `test_assistant_endpoint` | `POST /api/assistant/investigate` tool execution and JSON traces | Agentic AI | **PASSED** |
| `tests/test_end_to_end_investigation.py`| `test_complete_end_to_end_investigation_workflow` | Complete 12-step investigation pipeline executing all system layers | End-to-End System | **PASSED** |

---

## 3. Test Execution Commands

### 3.1 Backend & Pipeline Test Suite (Pytest)
```powershell
# Run complete test suite with verbose reporting
.\.venv\Scripts\pytest.exe -v

# Run only scientific and Pan-India tests
.\.venv\Scripts\pytest.exe -v tests/test_scientific_and_pan_india.py

# Run end-to-end integration test
.\.venv\Scripts\pytest.exe -v tests/test_end_to_end_investigation.py
```

### 3.2 Frontend Build & Lint Verification
```powershell
cd frontend
npm run build
```

---

## 4. Test Results Summary

- **Total Test Cases Collected**: 23
- **Total Test Cases Passed**: 23 (100.0%)
- **Total Test Failures**: 0
- **Total Test Warnings**: 1 (deprecated Starlette test client helper alias, non-breaking)
- **Execution Time**: ~1.85 seconds
- **Frontend Build Status**: Vite production bundle compiled in ~197 ms (`dist/index.html`, `dist/assets/index-*.css`, `dist/assets/index-*.js`).
