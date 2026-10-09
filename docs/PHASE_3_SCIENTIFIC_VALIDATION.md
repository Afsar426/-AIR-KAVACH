# AIR KAVACH (एयर कवच) — Phase 3 Scientific Validation & Attribution Reliability Report

**Document Version:** 3.0.0  
**Date:** October 9, 2026  
**System:** AIR KAVACH Pan-India Environmental Intelligence Platform  
**Target Environment:** FastAPI (Python 3.13) + React / Vite Production Build  
**Validation Region:** Indore, Madhya Pradesh (`in-mp-indore`) + Pan-India Scope  

---

## 1. Executive Summary & Audit Baseline

Phase 3 of the AIR KAVACH platform focused on transitioning the platform from an experimental multi-provider prototype into an empirically truthful, scientifically defensible, and legally guardrailed environmental intelligence system. 

Previous delivery reports claimed:
1. Six provider adapters operating uniformly.
2. Pan-India event detection and attribution.
3. 37 automated passing tests.
4. Functional agentic reports and investigation dossiers.

### Verified Audit Findings & Discrepancies
During our rigorous forensic audit of the repository, the following critical scientific and engineering gaps were identified and remediated:

| Audit Item | Previous State | Scientific Issue | Remediated Phase 3 State |
| :--- | :--- | :--- | :--- |
| **Provider Status** | Generic boolean `connected` for all reachable endpoints | Obscured whether data was actually persisted, its age, or if it was modeled simulation vs ground sensor readings. | Truthful status reporting `last_successful_retrieval_utc`, `latest_observation_utc`, `records_persisted`, `data_age_hours`, and `freshness_state`. Modeled Copernicus CAMS explicitly labeled as `modeled`. |
| **Event Lifecycle** | Events from Sept 2026 flagged as active spikes in some UI views | Historical episodes (> 30 days old) were not temporally isolated from live ongoing events. | Formal 5-state `EventLifecycleManager` (`active`, `resolved`, `recent`, `historical`, `insufficient_data`). Archival events are strictly marked `historical` / `recent`. |
| **Attribution Language** | Labels included `strong_geospatial_wind_evidence` | Risked misleading non-expert or regulatory users into assuming verified legal industrial causation. | Guardrailed to `GEOSPATIAL SCREENING SUPPORT`, `WIND ALIGNMENT SUPPORT`, `INSUFFICIENT METEOROLOGICAL EVIDENCE`, and `NEARBY BUT WIND MISALIGNED`. Score renamed to `screening_score_share`. |
| **CEMS Guardrail** | CEMS absence noted only in general markdown | Facility ranking tables did not explicitly warn of missing stack telemetry. | Mandatory banner and field: `"DIRECT EMISSIONS EVIDENCE UNAVAILABLE (CEMS UNCONNECTED)"`. |
| **Data Isolation** | Test CSV uploads risked mutating production Parquet tables | Automated test runs or trial uploads could corrupt the 8,211 verified Indore observation store. | Strict test isolation routing (`is_test=True` or `environment='test'`) to `data/test_intake/` with ledger tagging. Production stores completely immutable to tests. |
| **Agentic Reports** | Freeform markdown summary | Obscured distinction between measured facts and model inferences. | Disaggregated top-level report schema: `observed_facts`, `modeled_estimates`, `candidate_rankings`, `missing_evidence`, `limitations`, `provenance`. |

---

## 2. Scientific Principles & Methodological Enhancements

### 2.1 Event Lifecycle Architecture (`src/event_detection/lifecycle.py`)
Environmental events have distinct operational lifecycles. An elevation recorded 35 days ago cannot be treated with the same urgency as a spike occurring within the last 60 minutes.

The system enforces five definitive temporal states evaluated against server UTC time:
1. **`active`**: The event's elevation window concluded $\le 6$ hours ago AND the station's latest continuous observation remains within or at the elevated event boundary.
2. **`resolved`**: The event concluded $\le 72$ hours ago AND subsequent baseline readings below the threshold have been recorded.
3. **`recent`**: The event concluded between 72 hours and 30 days ago.
4. **`historical`**: The event concluded $> 30$ days ago (e.g., all 48 validation events from September 2026).
5. **`insufficient_data`**: Fewer than 4 continuous readings ($< 1$ hour of 15-minute observations) or broken timestamp boundaries.

### 2.2 Leakage-Free Past-Only Rolling Baseline
To prevent look-ahead bias and data leakage, statistical anomaly detection uses past observations strictly:
$$\text{Baseline Mean}_t = \frac{1}{K} \sum_{i=1}^{K} x_{t-i} = \text{shift}(1).\text{rolling}(96).\text{mean}()$$
$$\text{Baseline Std}_t = \sqrt{\frac{1}{K-1} \sum_{i=1}^{K} (x_{t-i} - \text{Baseline Mean}_t)^2} = \text{shift}(1).\text{rolling}(96).\text{std}()$$
- Any time gap exceeding 30 minutes initiates a new independent monitoring segment (`segment_id += 1`).
- Inside each segment, a minimum warmup period of 24 observations (6 hours) is required before anomalies can be triggered, preventing noisy threshold artifacts after sensor downtime.

### 2.3 Defensible Attribution & Screening Score Share
Industrial source attribution in AIR KAVACH is explicitly defined as a **heuristic screening index**, NOT a calibrated atmospheric dispersion probability.

#### Heuristic Formula
For monitoring station sensor $S$ and candidate industrial facility $F$:
1. **Bearing Angle**: $\theta_{S \to F} = \text{bearing}(\text{lat}_S, \text{lon}_S, \text{lat}_F, \text{lon}_F)$
2. **Angular Difference**: $\Delta \theta = |(\theta_{S \to F} - \text{Wind Direction From} + 180^\circ) \pmod{360^\circ} - 180^\circ|$
3. **Wind Alignment**: $W = \max(0, \cos(\Delta \theta))$
4. **Distance Proximity Decay**: $D = \exp\left(-\frac{d(S, F)}{d_0}\right)$, where $d_0 = 5.0\text{ km}$
5. **Raw Attribution Score**: $A_{\text{raw}} = 0.7 \cdot W + 0.3 \cdot D$
6. **Screening Score Share**:
   $$\text{Screening Score Share}_i = \frac{A_{\text{raw}, i}}{\sum_{j=1}^{M} A_{\text{raw}, j}}$$

#### Scientific Guardrails & Categorical Rules
- If top score $< 0.35$ or wind vector coverage $< 25\%$, the evidence is classified as `INSUFFICIENT METEOROLOGICAL EVIDENCE`.
- If facility is geographically upwind ($W \ge 0.25$), it receives `WIND ALIGNMENT SUPPORT` or `GEOSPATIAL SCREENING SUPPORT`.
- If facility is downwind ($W < 0.25$), it is labeled `NEARBY BUT WIND MISALIGNED`.
- Every candidate record carries the mandatory field:
  ```json
  "direct_emissions_evidence": "DIRECT EMISSIONS EVIDENCE UNAVAILABLE (CEMS UNCONNECTED)"
  ```

---

## 3. Disaggregated Investigation Reports

Reports exported via `POST /api/reports` and natural-language investigations executed by `AgenticOrchestrator` (`POST /api/assistant/investigate`) are partitioned into explicit, non-overlapping sections to prevent conflating observed ground facts with mathematical estimates:

```json
{
  "report_id": "REP-EVT-0001-1773079800",
  "event_id": "EVT-0001",
  "generated_at": "2026-10-09T18:05:00Z",
  "observed_facts": {
    "station": "Residency",
    "city": "Indore",
    "state_ut": "Madhya Pradesh",
    "start_time": "2026-09-01T12:00:00Z",
    "end_time": "2026-09-01T14:30:00Z",
    "duration_minutes": 150,
    "peak_pm25": 142.5,
    "wind_direction_mean_deg": 242.1,
    "wind_speed_mean_mps": 2.45,
    "wind_coverage": 1.0
  },
  "modeled_estimates": {
    "peak_z_score": 3.42,
    "anomaly_score": 0.045,
    "temporal_lifecycle_status": "historical",
    "dispersion_scale_km": 5.0,
    "baseline_method": "past-only rolling 24h baseline (shift(1).rolling(96))"
  },
  "candidate_rankings": [
    {
      "factory_rank": 1,
      "factory_name": "Sanwer Road Metal Casting Works",
      "distance_km": 4.12,
      "wind_relationship": "upwind_aligned",
      "attribution_score": 0.824,
      "screening_score_share": 0.384,
      "evidence_label": "GEOSPATIAL SCREENING SUPPORT",
      "direct_emissions_evidence": "DIRECT EMISSIONS EVIDENCE UNAVAILABLE (CEMS UNCONNECTED)"
    }
  ],
  "missing_evidence": [
    "Direct continuous emissions monitoring system (CEMS) telemetry is unavailable for candidate facilities.",
    "Planetary boundary layer mixing height and vertical wind shear observations are unrecorded."
  ],
  "limitations": [
    "Attribution scores reflect heuristic geospatial and meteorological screening index, NOT verified legal causation or calibrated dispersion probability.",
    "AERMOD or HYSPLIT dispersion modeling is required for regulatory enforcement or legal action."
  ],
  "provenance": {
    "system": "AIR KAVACH Pan-India Environmental Intelligence Platform",
    "version": "2.1.0",
    "attribution_methodology": "Heuristic distance decay (30%) + wind alignment (70%)",
    "event_detection_engine": "Past-only rolling baseline (shift(1)) + Z-score thresholding"
  }
}
```

---

## 4. Test vs Production Data Isolation

To protect real scientific observations from synthetic or test-suite pollution:
1. `NormalizedRecord` includes typed `is_test: bool = False` and `environment: str = "production"`.
2. `PipelineConnector` inspects each batch:
   - Any commit where `is_test == True` or `environment == "test"` or `region_id.startswith("in-test-")` is directed to `data/test_intake/`.
   - Downstream event detection and attribution recomputations are blocked for test batches.
   - The verified production store (`data/processed/air_quality/air_quality.parquet`, 8,211 rows) is completely protected.
3. `IntakeLedger` logs environment flags and provides filtered access via `GET /api/intake/history?environment=test` and `GET /api/intake/history?environment=production`.

---

## 5. Automated Verification Results

### 5.1 Python Test Suite (`pytest`)
All 51 automated tests passed with 100% success rate:

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
collected 51 items

tests/test_attribution.py::test_geospatial_calculations PASSED           [  1%]
tests/test_backend_api.py::test_root_and_health PASSED                   [  3%]
tests/test_backend_api.py::test_summary_endpoint PASSED                  [  5%]
tests/test_backend_api.py::test_events_endpoint PASSED                   [  7%]
tests/test_backend_api.py::test_attribution_endpoint PASSED              [  9%]
tests/test_backend_api.py::test_assistant_endpoint PASSED                [ 11%]
tests/test_end_to_end_investigation.py::test_complete_end_to_end_investigation_workflow PASSED [ 13%]
tests/test_event_detection.py::test_event_processor PASSED               [ 15%]
tests/test_ingestion.py::test_ingestion_status PASSED                    [ 17%]
tests/test_ml_model.py::test_isolation_forest_lifecycle PASSED           [ 19%]
tests/test_phase2_validation.py::test_openmeteo_weather_live_connectivity PASSED [ 21%]
tests/test_phase2_validation.py::test_openmeteo_airquality_modeled_label_strict PASSED [ 23%]
tests/test_phase2_validation.py::test_unconfigured_providers_graceful_status PASSED [ 25%]
tests/test_phase2_validation.py::test_deterministic_csv_preview_and_mapping PASSED [ 27%]
tests/test_phase2_validation.py::test_idempotent_commit_and_ledger PASSED [ 29%]
tests/test_phase2_validation.py::test_event_detection_past_only_and_gap_handling PASSED [ 31%]
tests/test_phase2_validation.py::test_attribution_screening_guardrails PASSED [ 33%]
tests/test_phase2_validation.py::test_pan_india_isolation_and_no_leakage PASSED [ 35%]
tests/test_phase3_scientific_validation.py::test_event_lifecycle_manager_five_states PASSED [ 37%]
tests/test_phase3_scientific_validation.py::test_backend_events_lifecycle_enrichment PASSED [ 39%]
tests/test_phase3_scientific_validation.py::test_test_vs_prod_isolation_strict PASSED [ 41%]
tests/test_phase3_scientific_validation.py::test_providers_status_truthful_metrics PASSED [ 43%]
tests/test_phase3_scientific_validation.py::test_attribution_defensible_labels_and_share PASSED [ 45%]
tests/test_phase3_scientific_validation.py::test_agentic_report_disaggregation PASSED [ 47%]
tests/test_real_data_integration.py::test_openaq_normalization PASSED    [ 49%]
tests/test_real_data_integration.py::test_openmeteo_weather_normalization PASSED [ 50%]
tests/test_real_data_integration.py::test_openmeteo_airquality_modeled_label PASSED [ 52%]
tests/test_real_data_integration.py::test_cpcb_normalization PASSED      [ 54%]
tests/test_real_data_integration.py::test_nasa_firms_normalization PASSED [ 56%]
tests/test_real_data_integration.py::test_cems_normalization_and_exceedance PASSED [ 58%]
tests/test_real_data_integration.py::test_quality_validator_bounds_and_invalid PASSED [ 60%]
tests/test_real_data_integration.py::test_quality_validator_staleness PASSED [ 62%]
tests/test_real_data_integration.py::test_idempotent_deduplication PASSED [ 64%]
tests/test_real_data_integration.py::test_provider_failure_resilience PASSED [ 66%]
tests/test_real_data_integration.py::test_providers_status_endpoint PASSED [ 68%]
tests/test_real_data_integration.py::test_intake_preview_endpoint PASSED [ 70%]
tests/test_real_data_integration.py::test_intake_commit_endpoint PASSED  [ 72%]
tests/test_real_data_integration.py::test_intake_history_endpoint PASSED [ 74%]
tests/test_scientific_and_pan_india.py::test_bearing_cardinal_directions PASSED [ 76%]
tests/test_scientific_and_pan_india.py::test_circular_angle_difference_wraparound PASSED [ 78%]
tests/test_scientific_and_pan_india.py::test_wind_from_convention_alignment PASSED [ 80%]
tests/test_scientific_and_pan_india.py::test_distance_decay_exponential PASSED [ 82%]
tests/test_scientific_and_pan_india.py::test_pan_india_region_registry PASSED [ 84%]
tests/test_scientific_and_pan_india.py::test_no_indore_leakage_on_unrelated_region PASSED [ 86%]
tests/test_scientific_and_pan_india.py::test_indore_validation_region_returns_data PASSED [ 88%]
tests/test_scientific_and_pan_india.py::test_ready_endpoint PASSED       [ 90%]
tests/test_scientific_and_pan_india.py::test_stations_endpoint PASSED    [ 92%]
tests/test_scientific_and_pan_india.py::test_coverage_endpoint PASSED    [ 94%]
tests/test_scientific_and_pan_india.py::test_system_status_endpoint PASSED [ 96%]
tests/test_scientific_and_pan_india.py::test_ingestion_jobs_endpoint PASSED [ 98%]
tests/test_scientific_and_pan_india.py::test_reports_lifecycle_endpoint PASSED [100%]

======================= 51 passed, 1 warning in 25.76s ========================
```

### 5.2 Frontend Production Build (`npm run build`)
```
> frontend@0.0.0 build
> vite build

vite v8.3.4 building client environment for production...
transforming...
✓ 1956 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.45 kB │ gzip:   0.29 kB
dist/assets/index-XfXACP9R.css   20.06 kB │ gzip:   7.78 kB
dist/assets/index-DcbxXM-Q.js   512.59 kB │ gzip: 143.19 kB
✓ built in 194ms
```

---

## 6. Scientific Limitations & Regulatory Use Policy

1. **Non-Causative Nature of Geometric Screening**: AIR KAVACH rankings indicate geographic and meteorological consistency between an observed station elevation and candidate facilities. They do **not** constitute proof of emissions, operational violation, or legal liability.
2. **Absence of Real-Time In-Stack CEMS Telemetry**: Facilities are registered via statutory industrial registries. Until direct continuous emission monitoring system (CEMS) interfaces are authorized and connected, stack status during event hours is unverified.
3. **Two-Dimensional Surface Wind Limitation**: Wind vectors are evaluated using surface horizontal observations (10m). Atmospheric dispersion parameters such as boundary layer mixing height, convective turbulence, vertical wind shear, and building downwash require formal Gaussian plume or Lagrangian particle dispersion models (e.g., US EPA AERMOD or NOAA HYSPLIT).
4. **Regulatory Usage**: These findings are intended to assist regulatory officers, environmental researchers, and inspection teams in prioritizing physical inspections and ground sampling; they must not be used as standalone evidence for penal enforcement.
