# AIR KAVACH - Data Provenance & Asset Registry

## 1. Provenance Statement & Integrity Guarantees

AIR KAVACH strictly adheres to the principle of **Scientific Honesty and Provenance Integrity**.
- **No Fabricated Data**: No sensor readings, meteorological measurements, industrial facility coordinates, or anomaly records are simulated or randomly generated in production.
- **Explicit Coverage States**: Datasets are tagged with explicit temporal bounds, geographic bounding boxes, and ingestion origins. Regions without ingested data truthfully report `FEEDS_PENDING`.
- **Reproducibility**: Every processed feature dataset in `data/` originates from an auditable raw or authoritative source file.

---

## 2. Ingested Datasets Inventory

### 2.1 High-Frequency Ambient Air Quality Observations
- **File Location**: `data/processed/air_quality/air_quality.parquet` (and `data/raw/openaq/indore_air_quality_clean.parquet`)
- **Source**: Central Pollution Control Board (CPCB) India via OpenAQ API v3.
- **Geographic Coverage**: Indore, Madhya Pradesh, India.
  - Station 1: Residency Area (`IND-RES-01`, 22.7126° N, 75.8753° E)
  - Station 2: Regional Park (`IND-REG-02`, 22.6841° N, 75.8398° E)
  - Station 3: Devi Ahilya Bai Holkar Airport (`IND-AIR-03`, 22.7231° N, 75.8035° E)
  - Station 4: Maguda Area (`IND-MAG-04`, 22.7500° N, 75.8900° E)
- **Temporal Range**: September 1, 2026 to September 30, 2026.
- **Sampling Frequency**: 15-minute continuous observations.
- **Record Count**: 8,211 verified records.
- **Parameters**: `pm25` ($\mu\text{g/m}^3$).
- **License**: Open Data Commons Attribution License (ODC-BY) via OpenAQ / CPCB Open Data Policy.

### 2.2 Surface Meteorological Wind Observations
- **File Location**: `data/raw/weather/indore_wind_hourly.parquet`
- **Source**: Open-Meteo Historical Weather API / ECMWF ERA5 Atmospheric Reanalysis.
- **Geographic Coverage**: Bounding Box [22.50° N, 75.60° E] to [22.90° N, 76.10° E].
- **Temporal Range**: Hourly continuous records aligned with September 2026 air quality telemetry.
- **Record Count**: 10,012 hourly observations.
- **Parameters**: 10-meter wind speed ($U_{10}$, m/s), 10-meter wind direction ($\theta_{10}$, degrees FROM True North), surface temperature ($T_{2m}$), surface pressure ($P$).
- **License**: Copernicus Climate Change Service (C3S) / Creative Commons Attribution 4.0 International (CC-BY 4.0).

### 2.3 Industrial Facilities Catalog
- **File Location**: `data/raw/facilities/indore_industrial_facilities.parquet`
- **Source**: OpenStreetMap (OSM) Overpass API via query tags `landuse=industrial`, `man_made=works`, `industrial=*`.
- **Geographic Coverage**: Indore industrial belts (Sanwer Road Industrial Area, Pithampur Industrial Estate, Dewas Naka, Polo Ground).
- **Facility Count**: 27 verified industrial facilities (26 active facilities within the 25km attribution boundary).
- **Key Categories**: Industrial works, metal casting, textile finishing, pharmaceutical synthesis, chemical processing, food processing.
- **License**: Open Database License (ODbL) 1.0 (OpenStreetMap contributors).

### 2.4 Multi-Station Daily Air Quality Benchmark
- **File Location**: `data/raw/xkdr/indore_daily_2024.parquet`
- **Source**: XKDR Forum Clean Air Project (cross-verified against CPCB official daily bulletins).
- **Geographic Coverage**: Indore municipal stations.
- **Temporal Range**: January 1, 2024 to December 31, 2024.
- **Record Count**: 336 daily consolidated records.
- **Parameters**: Daily mean PM2.5, PM10, AQI sub-indices.
- **Use Case**: Used as an independent long-term seasonal benchmark and baseline validation set for seasonal anomaly comparisons.
- **License**: Research Public Use / XKDR Academic Release.

---

## 3. Data Processing Lineage

| Dataset Output | Input Datasets | Processing Pipeline Script | Output Verification Check |
|---|---|---|---|
| `data/processed/air_quality/air_quality.parquet` | Raw OpenAQ JSON / Parquet | `src/ingestion/openaq_client.py` | 8,211 rows, UTC timestamps, no negative PM2.5 |
| `data/features/pollution_events.parquet` | `air_quality.parquet` | `src/event_detection/event_processor.py` | 48 events, 96-window shifted rolling baseline |
| `data/features/pollution_events_with_wind.parquet` | `pollution_events.parquet` + `indore_wind_hourly.parquet` | `src/features/event_wind_alignment.py` | 48 events, 99.7% wind coverage, circular mean |
| `data/features/event_factory_attribution.parquet` | `pollution_events_with_wind.parquet` + `indore_industrial_facilities.parquet` | `src/attribution/attribution_engine.py` | 1,248 candidate records (48 events × 26 facilities) |
| `data/features/event_factory_confidence.parquet` | `event_factory_attribution.parquet` | `src/attribution/confidence.py` | 48 events, top-3 ranked candidates, normalized likelihoods |
| `backend/map_data.json` | All derived feature Parquet files | `src/evidence/map_data.py` | GeoJSON structure, 4 stations, 26 facilities, 48 events |
| `models/isolation_forest/isolation_forest_v1.joblib` | `air_quality.parquet` | `src/ml/isolation_forest.py` | 300 estimators, 4-feature vector, joblib serialized |

---

## 4. Pan-India Coverage Matrix

| Region Identifier | State / UT | Air Quality Status | Weather Status | Facilities Status | Attribution Readiness |
|---|---|---|---|---|---|
| `in-mp-indore` | Madhya Pradesh | **ACTIVE** (8,211 high-frequency records) | **ACTIVE** (10,012 hourly records) | **ACTIVE** (27 mapped plants) | **READY** (48 analyzed events) |
| `in-dl-delhi` | National Capital Territory | FEEDS_PENDING (Ingestion Adapter ready) | FEEDS_PENDING | FEEDS_PENDING | Awaiting Regional Data Ingestion |
| `in-mh-mumbai` | Maharashtra | FEEDS_PENDING | FEEDS_PENDING | FEEDS_PENDING | Awaiting Regional Data Ingestion |
| `in-gj-ahmedabad` | Gujarat | FEEDS_PENDING | FEEDS_PENDING | FEEDS_PENDING | Awaiting Regional Data Ingestion |
| `in-ka-bengaluru` | Karnataka | FEEDS_PENDING | FEEDS_PENDING | FEEDS_PENDING | Awaiting Regional Data Ingestion |
| `in-up-kanpur` | Uttar Pradesh | FEEDS_PENDING | FEEDS_PENDING | FEEDS_PENDING | Awaiting Regional Data Ingestion |
