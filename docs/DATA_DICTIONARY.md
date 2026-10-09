# AIR KAVACH - Data Dictionary & Schema Specification

This document provides the definitive data dictionary for all raw, processed, derived, and serialized datasets used across the AIR KAVACH platform.

---

## 1. Raw & Processed Environmental Observations

### 1.1 Air Quality Observations (`data/processed/air_quality/air_quality.parquet`)
High-frequency ambient air quality measurements from stationary continuous ambient air quality monitoring stations (CAAQMS).

| Field Name | Type | Nullable | Units | Constraints / Valid Values | Description |
|---|---|---|---|---|---|
| `station` | string | No | N/A | Non-empty string (e.g., `Residency`, `Regional Park`) | Human-readable CAAQMS station identifier |
| `sensor_id` | string | No | N/A | Alphanumeric (e.g., `IND-RES-01`) | Unique physical sensor identifier |
| `timestamp` | timestamp[ns, UTC] | No | ISO 8601 UTC | Continuous, 15-minute sampling interval | Observation timestamp in UTC |
| `parameter` | string | No | N/A | `pm25`, `pm10`, `no2`, `so2`, `co`, `o3` | Atmospheric pollutant parameter |
| `value` | float64 | No | $\mu\text{g/m}^3$ | $\ge 0.0$ (negative readings discarded) | Measured concentration value |
| `unit` | string | No | N/A | `µg/m³` | Physical measurement unit |
| `latitude` | float64 | No | Degrees | $-90.0 \le \phi \le 90.0$ (Indore: $\approx 22.7$) | Station latitude (WGS84 EPSG:4326) |
| `longitude` | float64 | No | Degrees | $-180.0 \le \lambda \le 180.0$ (Indore: $\approx 75.8$) | Station longitude (WGS84 EPSG:4326) |
| `city` | string | No | N/A | e.g., `Indore`, `Delhi`, `Mumbai` | City municipality |
| `state` | string | No | N/A | e.g., `Madhya Pradesh` | State or union territory |
| `country` | string | No | ISO 3166-1 | `IN` | Sovereign nation code |

### 1.2 Meteorological Wind Observations (`data/raw/weather/indore_wind_hourly.parquet`)
Meteorological observations for surface wind speed, direction, and ambient conditions.

| Field Name | Type | Nullable | Units | Constraints / Valid Values | Description |
|---|---|---|---|---|---|
| `timestamp` | timestamp[ns, UTC] | No | ISO 8601 UTC | Hourly or interpolated 15-min | Observation timestamp in UTC |
| `wind_speed_10m` | float64 | No | $\text{m/s}$ | $\ge 0.0$ | Surface horizontal wind speed at 10m AGL |
| `wind_direction_10m` | float64 | No | Degrees | $0.0 \le \theta < 360.0$ | Meteorological wind direction (**FROM** convention: 0°=N, 90°=E, 180°=S, 270°=W) |
| `wind_gusts_10m` | float64 | Yes | $\text{m/s}$ | $\ge 0.0$ | Peak horizontal wind gust at 10m AGL |
| `surface_pressure` | float64 | Yes | $\text{hPa}$ | $800.0 \le P \le 1100.0$ | Atmospheric barometric pressure |
| `temperature_2m` | float64 | Yes | $^\circ\text{C}$ | $-50.0 \le T \le 60.0$ | Ambient surface air temperature at 2m AGL |
| `relative_humidity_2m`| float64 | Yes | $\%$ | $0.0 \le RH \le 100.0$ | Ambient relative humidity at 2m AGL |

---

## 2. Geospatial Assets

### 2.1 Industrial Facilities (`data/raw/facilities/indore_industrial_facilities.parquet`)
Catalog of candidate industrial facilities, factories, power plants, and manufacturing sites extracted from OpenStreetMap Overpass API and regional industrial directories.

| Field Name | Type | Nullable | Units | Constraints / Valid Values | Description |
|---|---|---|---|---|---|
| `factory_id` | string | No | N/A | Alphanumeric (e.g., `FAC-001`, `OSM-WAY-10293`) | Unique facility identifier |
| `factory_name` | string | No | N/A | Non-empty string | Registered enterprise name |
| `latitude` | float64 | No | Degrees | $-90.0 \le \phi \le 90.0$ | Facility centroid latitude (EPSG:4326) |
| `longitude` | float64 | No | Degrees | $-180.0 \le \lambda \le 180.0$ | Facility centroid longitude (EPSG:4326) |
| `facility_category` | string | No | N/A | `industrial_works`, `chemical`, `metal`, `textile`, `food`, `power` | Operational industrial classification |
| `city` | string | No | N/A | e.g., `Indore` | City municipality |
| `state` | string | No | N/A | e.g., `Madhya Pradesh` | State / UT jurisdiction |
| `country` | string | No | N/A | `IN` | Country code |
| `has_continuous_emissions_monitoring` | bool | Yes | N/A | `True` / `False` | Whether online CEMS telemetry exists |

---

## 3. Analytical & Derived Event Datasets

### 3.1 Detected Pollution Events (`data/features/pollution_events.parquet`)
Continuous pollution episodes extracted using 96-reading rolling baseline segmentation and z-score anomaly thresholds.

| Field Name | Type | Nullable | Units | Constraints / Valid Values | Description |
|---|---|---|---|---|---|
| `event_id` | string | No | N/A | Pattern: `^EVT-\d{4}$` | Deterministic event identifier |
| `station` | string | No | N/A | Valid station name | Monitoring station where event was recorded |
| `pollutant` | string | No | N/A | `pm25` | Target elevated pollutant |
| `start_time` | timestamp[ns, UTC] | No | ISO 8601 UTC | $\text{start} < \text{end}$ | Episode onset timestamp |
| `end_time` | timestamp[ns, UTC] | No | ISO 8601 UTC | $\text{duration} \ge 60 \text{ min}$ | Episode termination timestamp |
| `duration_minutes` | float64 | No | Minutes | $\ge 60.0$ (minimum 4 readings) | Total episode duration |
| `peak_pm25` | float64 | No | $\mu\text{g/m}^3$ | Peak measured value | Maximum concentration during episode |
| `baseline_pm25` | float64 | No | $\mu\text{g/m}^3$ | $\ge 0.0$ | 24-hour shifted rolling baseline mean |
| `baseline_std` | float64 | No | $\mu\text{g/m}^3$ | $> 0.0$ | 24-hour shifted rolling standard deviation |
| `peak_z_score` | float64 | No | Unitless | $\ge 2.0$ | Maximum statistical z-score deviation |
| `ml_anomaly_score` | float64 | Yes | Unitless | Range: $[-1.0, 1.0]$ | Isolation Forest anomaly score |
| `num_readings` | int64 | No | Count | $\ge 4$ | Number of continuous 15-min readings |

### 3.2 Wind-Enriched Pollution Events (`data/features/pollution_events_with_wind.parquet`)
Pollution events joined with coincident surface meteorological wind vectors.

| Field Name | Type | Nullable | Units | Constraints / Valid Values | Description |
|---|---|---|---|---|---|
| *(All fields from 3.1)* | ... | ... | ... | ... | Inherited event parameters |
| `wind_speed_mean` | float64 | Yes | $\text{m/s}$ | $\ge 0.0$ | Mean wind speed during event window |
| `wind_direction_mean_deg` | float64 | Yes | Degrees | $0.0 \le \theta < 360.0$ | Circular mean wind direction (FROM convention) |
| `wind_data_coverage_pct` | float64 | No | $\%$ | $0.0 \le P \le 100.0$ | Percentage of event timesteps with valid wind data |
| `wind_reliability` | string | No | N/A | `high`, `moderate`, `low`, `missing` | Categorical wind reliability indicator |

### 3.3 Candidate Source Attribution Records (`data/features/event_factory_attribution.parquet`)
Pairwise cross-product between detected pollution events and geographic candidate facilities within the attribution radius ($r \le 25\text{ km}$).

| Field Name | Type | Nullable | Units | Constraints / Valid Values | Description |
|---|---|---|---|---|---|
| `event_id` | string | No | N/A | Pattern: `^EVT-\d{4}$` | Associated pollution event ID |
| `factory_id` | string | No | N/A | Alphanumeric | Associated candidate facility ID |
| `factory_name` | string | No | N/A | Non-empty string | Name of industrial facility |
| `station` | string | No | N/A | Valid station name | Target monitoring station |
| `distance_km` | float64 | No | km | $0.0 \le d \le 25.0$ | Haversine distance between station and factory |
| `bearing_deg` | float64 | No | Degrees | $0.0 \le \beta < 360.0$ | Forward geodetic bearing from station to factory |
| `wind_direction_deg` | float64 | Yes | Degrees | $0.0 \le \theta < 360.0$ | Mean wind direction during event |
| `angular_diff_deg` | float64 | Yes | Degrees | $0.0 \le |\Delta\theta| \le 180.0$ | Minimal circular angular difference ($|\beta - \theta|$) |
| `wind_alignment_score` | float64 | Yes | Unitless | Range: $[-1.0, 1.0]$ | $\cos(\Delta\theta)$ alignment index |
| `positive_wind_alignment`| float64 | Yes | Unitless | Range: $[0.0, 1.0]$ | $\max(0, \cos(\Delta\theta))$ (zero for downwind) |
| `distance_decay_score` | float64 | No | Unitless | Range: $[0.0, 1.0]$ | $\exp(-d / 5.0)$ exponential proximity score |
| `attribution_score` | float64 | No | Unitless | Range: $[0.0, 1.0]$ | Composite screening score ($0.7 \cdot \text{wind} + 0.3 \cdot \text{dist}$) |
| `evidence_label` | string | No | N/A | `strong_geospatial_wind_evidence`, `upwind_evidence`, `downwind_low_plausibility`, `insufficient_evidence` | Categorical evidence alignment label |

### 3.4 Confidence & Ranking Summary (`data/features/event_factory_confidence.parquet`)
Top candidate rankings per event with normalized score shares and evidentiary status.

| Field Name | Type | Nullable | Units | Constraints / Valid Values | Description |
|---|---|---|---|---|---|
| `event_id` | string | No | N/A | Pattern: `^EVT-\d{4}$` | Event identifier |
| `rank` | int64 | No | Rank | $1 \le \text{rank} \le 3$ | Relative rank within candidate pool for event |
| `factory_id` | string | No | N/A | Alphanumeric | Facility identifier |
| `factory_name` | string | No | N/A | Non-empty string | Facility name |
| `attribution_score` | float64 | No | Unitless | $[0.0, 1.0]$ | Raw composite screening score |
| `relative_likelihood` | float64 | No | Unitless | $[0.0, 1.0]$ ($\sum \text{top} \approx 1.0$) | Normalized screening score fraction |
| `source_identification_status` | string | No | N/A | `candidate_source_found`, `no_reliable_source`, `inconclusive_wind` | Operational attribution status |
| `evidence_summary` | string | No | N/A | Non-empty string | Human-readable evidentiary justification |

---

## 4. Map Layer Data Contract (`backend/map_data.json`)
Pre-computed GeoJSON-compatible structure consumed by the frontend Leaflet vector map.

```json
{
  "stations": [
    {
      "name": "Residency",
      "lat": 22.7126,
      "lng": 75.8753,
      "sensor_id": "IND-RES-01",
      "city": "Indore"
    }
  ],
  "facilities": [
    {
      "factory_id": "FAC-001",
      "factory_name": "Sanwer Industrial Works",
      "lat": 22.8251,
      "lng": 75.8450,
      "category": "industrial_works"
    }
  ],
  "events": [
    {
      "event_id": "EVT-0001",
      "station": "Residency",
      "start_time": "2026-09-02T14:15:00Z",
      "end_time": "2026-09-02T16:30:00Z",
      "duration_minutes": 135.0,
      "peak_pm25": 142.5,
      "peak_z_score": 3.45,
      "wind_direction": 270.0,
      "wind_speed": 3.2,
      "top_candidates": [
        {
          "rank": 1,
          "factory_id": "FAC-001",
          "factory_name": "Sanwer Industrial Works",
          "distance_km": 12.8,
          "bearing_deg": 268.4,
          "attribution_score": 0.78,
          "evidence_label": "strong_geospatial_wind_evidence"
        }
      ]
    }
  ]
}
```

---

## 5. Normalized Provider & Data Intake Schemas

### 5.1 Canonical Normalized Record Schema (`NormalizedRecord`)
All data providers and CSV uploads are normalized into this common intermediate representation prior to validation and storage:

| Field Name | Type | Nullable | Valid Values / Constraints | Description |
|---|---|---|---|---|
| `provider_id` | string | No | `openaq_v3`, `cpcb_datagov`, `openmeteo_weather`, `openmeteo_airquality_model`, `nasa_firms`, `cems_industrial_stack`, `csv_upload` | Identifying slug of provider |
| `data_type` | string | No | `observed`, `modeled`, `satellite`, `cems`, `derived` | Explicit data categorization |
| `timestamp_utc` | string (ISO 8601) | No | Past or current UTC timestamp | Instant of physical observation |
| `retrieval_timestamp_utc` | string (ISO 8601) | No | UTC timestamp | Instant record was retrieved by platform |
| `station_id` | string | Yes | Alphanumeric | Machine station identifier |
| `station_name` | string | Yes | Human-readable string | Station display name |
| `latitude` | float | Yes | $-90.0 \le \phi \le 90.0$ | Geodetic latitude |
| `longitude` | float | Yes | $-180.0 \le \lambda \le 180.0$ | Geodetic longitude |
| `city` | string | Yes | Non-empty string | Target municipality |
| `state_ut` | string | Yes | Non-empty string | State or UT jurisdiction |
| `country` | string | No | `IN` | ISO sovereign code |
| `parameter` | string | No | `pm25`, `pm10`, `no2`, `so2`, `co`, `o3`, `wind_speed_10m`, `wind_direction_10m`, `temperature_2m`, `fire_radiative_power`, `stack_pm` | Measurement parameter |
| `value` | float | No | Physical range bounds | Numerical measured value |
| `unit` | string | No | `µg/m³`, `m/s`, `degrees`, `°C`, `MW`, `mg/Nm³` | Measurement physical unit |
| `quality_flag` | string | No | `valid`, `suspect`, `invalid`, `stale` | Quality status |
| `quality_reason` | string | Yes | Non-empty explanation string | Justification for non-valid flag |
| `record_id` | string | No | SHA-256 16-hex prefix | Deterministic composite hash |
| `provenance` | object | No | Key-value dictionary | Raw metadata and provider snippets |

### 5.2 Persistent Intake Audit Ledger (`data/processed/intake_history.json`)
Ledger recording all ingestion cycles, manual CSV imports, and provider sync executions:

| Field Name | Type | Description |
|---|---|---|
| `job_id` | string | Unique execution ID (`IMP-YYYYMMDDHHMMSS-XXXX`) |
| `timestamp_utc` | string | Job execution timestamp |
| `source` | string | Source provider or uploaded file name |
| `data_type` | string | Ingested data type |
| `region_id` | string | Target geographic region |
| `records_received` | integer | Total records parsed in batch |
| `records_accepted` | integer | Total records passing quality filters |
| `records_rejected` | integer | Total records dropped due to invalid bounds |
| `validation_errors`| object | Breakdown of error reasons and occurrence counts |
| `status` | string | `completed` or `failed` |
| `details` | object | Metadata including net inserted rows and events detected |

