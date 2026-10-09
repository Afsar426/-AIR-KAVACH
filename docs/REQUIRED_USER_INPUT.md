# AIR KAVACH - Required User Input & Configuration Reference

This document catalogs optional external credentials, environment keys, and data sources for extending the AIR KAVACH platform beyond its local production baseline.

> [!NOTE]
> **Zero Blockers for Local Execution**  
> The entire AIR KAVACH platform (FastAPI backend, React frontend, analytical engines, Isolation Forest ML models, and Agentic AI assistant) is **100% operational immediately** using existing verified local datasets and deterministic tool orchestration. **No external credentials are required to run, test, or evaluate the system.**

---

## 1. Optional External Credentials

The following environment variables can optionally be populated in `.env` to enable live external network streaming:

| Environment Variable | Service | Purpose | Fallback Behavior when Omitted |
|---|---|---|---|
| `OPENAQ_API_KEY` | OpenAQ v3 API | High-throughput ingestion of live CAAQMS sensor telemetry across India without rate limits. | System uses cached verified high-frequency datasets (`data/processed/air_quality/air_quality.parquet`) and public OpenAQ unauthenticated tier. |
| `GEMINI_API_KEY` | Google Gemini API | Optional generative LLM conversational refinement for AI assistant responses. | **Deterministic Tool Orchestrator**: The agent executes all 14 allowlisted analytical tools, extracts parameters, evaluates physical wind vectors, and synthesizes structured JSON audit reports and traces natively with zero external latency. |

---

## 2. Ingesting Additional Pan-India Regions

The platform architecture is designed **Pan-India first** with canonical registries established in `src/geo/registry.py` for:
- `in-dl-delhi` (National Capital Territory of Delhi)
- `in-mh-mumbai` (Mumbai Metropolitan Region, Maharashtra)
- `in-gj-ahmedabad` (Ahmedabad Industrial Belt, Gujarat)
- `in-ka-bengaluru` (Bengaluru Urban, Karnataka)
- `in-up-kanpur` (Kanpur Industrial District, Uttar Pradesh)

### Steps to Activate Additional Regions:
1. Place regional 15-minute CAAQMS Parquet observations into `data/processed/air_quality/{region}_air_quality.parquet`.
2. Place regional hourly weather Parquet data into `data/raw/weather/{region}_wind_hourly.parquet`.
3. Place regional industrial facilities Parquet data into `data/raw/facilities/{region}_industrial_facilities.parquet`.
4. Trigger the batch pipeline or POST `/api/ingestion/run` with `{"region": "<region_id>"}`.
5. The region status in `/api/coverage` will automatically transition from `FEEDS_PENDING` to `ACTIVE`.
