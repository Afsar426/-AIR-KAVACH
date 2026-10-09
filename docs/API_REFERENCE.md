# AIR KAVACH - Complete REST API Reference & Specification

FastAPI Backend runs on `http://localhost:8000`. Interactive Swagger UI is accessible at `/docs` and ReDoc at `/redoc`.

---

## 1. System Health & Readiness

### 1.1 Root Info
- **Endpoint**: `GET /`
- **Description**: Basic service metadata, version, and documentation links.
- **Response**:
```json
{
  "service": "AIR KAVACH Environmental Intelligence API",
  "version": "1.0.0",
  "status": "operational",
  "documentation": "/docs",
  "default_region": "in-mp-indore"
}
```

### 1.2 Health Probe
- **Endpoint**: `GET /health`
- **Description**: Liveness probe verifying service uptime and disk storage availability.
- **Status Code**: `200 OK`
- **Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-10-09T14:30:00Z",
  "storage": "mounted",
  "uptime_seconds": 1420.5
}
```

### 1.3 Readiness Probe
- **Endpoint**: `GET /ready`
- **Description**: Readiness probe verifying database mounts, Parquet feature file availability, and ML model availability.
- **Status Code**: `200 OK` (or `503 Service Unavailable` if core files missing)
- **Response**:
```json
{
  "status": "ready",
  "components": {
    "air_quality_data": true,
    "weather_data": true,
    "facilities_data": true,
    "events_data": true,
    "attribution_data": true,
    "ml_models": true
  }
}
```

### 1.4 System Operational Status
- **Endpoint**: `GET /api/system/status`
- **Description**: Detailed telemetry on memory, data record counts, cache status, and active regions.
- **Response**:
```json
{
  "status": "operational",
  "environment": "production",
  "active_region": "in-mp-indore",
  "data_records": {
    "air_quality_observations": 8211,
    "weather_observations": 10012,
    "industrial_facilities": 27,
    "pollution_events": 48
  },
  "cache": {"enabled": true, "size_items": 128}
}
```

---

## 2. Geographical Scoping & Monitoring

### 2.1 Geographic Coverage & Status
- **Endpoint**: `GET /api/coverage`
- **Query Parameters**:
  - `region` (string, optional, default: `in-mp-indore`): Region identifier.
- **Description**: Truthful inventory of active sensors, temporal data bounds, and data availability state for the selected geographic region.
- **Response**:
```json
{
  "region": "in-mp-indore",
  "region_name": "Indore, Madhya Pradesh",
  "status": "active_historical",
  "coverage_status": "ACTIVE",
  "observations_count": 8211,
  "events_count": 48,
  "stations_count": 4,
  "earliest_timestamp": "2026-09-01T00:00:00Z",
  "latest_timestamp": "2026-09-30T23:45:00Z",
  "message": "Complete historical observations and attribution evidence available."
}
```

### 2.2 System & Regional Summary
- **Endpoint**: `GET /api/summary`
- **Query Parameters**:
  - `region` (string, optional, default: `in-mp-indore`)
- **Description**: High-level statistical aggregates for the region (total readings, detected events, active facilities, top pollutants).
- **Response**:
```json
{
  "region": "in-mp-indore",
  "total_observations": 8211,
  "total_events": 48,
  "active_facilities": 27,
  "active_stations": 4,
  "stations": ["Residency", "Regional Park", "Airport", "Maguda"],
  "pollutants_tracked": ["pm25"],
  "scientific_caveat": "Source attribution indicates geometric screening likelihood and does not constitute certified legal causation."
}
```

### 2.3 Monitoring Stations
- **Endpoint**: `GET /api/stations`
- **Query Parameters**:
  - `region` (string, optional, default: `in-mp-indore`)
- **Description**: Metadata, coordinates, and operational parameters for all monitoring stations within region.
- **Response**:
```json
[
  {
    "station_id": "IND-RES-01",
    "name": "Residency",
    "latitude": 22.7126,
    "longitude": 75.8753,
    "city": "Indore",
    "state": "Madhya Pradesh",
    "country": "IN",
    "active": true
  }
]
```

### 2.4 Ambient Observations Feed
- **Endpoint**: `GET /api/observations`
- **Query Parameters**:
  - `region` (string, optional): Region code
  - `station` (string, optional): Station name filter
  - `parameter` (string, optional, default: `pm25`): Target pollutant
  - `limit` (integer, optional, default: 100, max: 1000): Number of records
  - `offset` (integer, optional, default: 0): Pagination offset
- **Response**:
```json
{
  "total": 8211,
  "limit": 100,
  "offset": 0,
  "data": [
    {
      "timestamp": "2026-09-01T00:15:00Z",
      "station": "Residency",
      "sensor_id": "IND-RES-01",
      "parameter": "pm25",
      "value": 48.2,
      "unit": "µg/m³"
    }
  ]
}
```

---

## 3. Pollution Events & Source Attribution

### 3.1 List Pollution Events
- **Endpoint**: `GET /api/events`
- **Query Parameters**:
  - `region` (string, optional): Region code
  - `station` (string, optional): Station filter
  - `min_z_score` (float, optional, default: 2.0): Minimum anomaly threshold
  - `limit` (integer, optional, default: 50)
  - `offset` (integer, optional, default: 0)
- **Response**:
```json
{
  "total": 48,
  "limit": 50,
  "offset": 0,
  "data": [
    {
      "event_id": "EVT-0001",
      "station": "Residency",
      "pollutant": "pm25",
      "start_time": "2026-09-02T14:15:00Z",
      "end_time": "2026-09-02T16:30:00Z",
      "duration_minutes": 135.0,
      "peak_pm25": 142.5,
      "baseline_pm25": 38.2,
      "peak_z_score": 3.45,
      "ml_anomaly_score": -0.32,
      "num_readings": 9
    }
  ]
}
```

### 3.2 Event Detail
- **Endpoint**: `GET /api/events/{event_id}`
- **Path Parameters**:
  - `event_id` (string, required): e.g., `EVT-0001`
- **Response**: Full metadata for the specified event, including time series profile and meteorological context.

### 3.3 Source Attribution Rankings
- **Endpoint**: `GET /api/attribution/{event_id}`
- **Path Parameters**:
  - `event_id` (string, required)
- **Query Parameters**:
  - `top_n` (integer, optional, default: 5): Number of candidates
- **Description**: Returns top ranked candidate industrial facilities evaluated using Haversine distance, forward bearing, and wind vector alignment.
- **Response**:
```json
{
  "event_id": "EVT-0001",
  "station": "Residency",
  "candidates": [
    {
      "rank": 1,
      "factory_id": "FAC-001",
      "factory_name": "Sanwer Industrial Works",
      "distance_km": 12.8,
      "bearing_deg": 268.4,
      "wind_direction_deg": 270.0,
      "angular_diff_deg": 1.6,
      "attribution_score": 0.78,
      "relative_likelihood": 0.44,
      "evidence_label": "strong_geospatial_wind_evidence"
    }
  ],
  "caveat": "Heuristic screening ranking only. Does not prove causal emission."
}
```

### 3.4 Evidentiary Chain
- **Endpoint**: `GET /api/evidence/{event_id}`
- **Path Parameters**:
  - `event_id` (string, required)
- **Description**: Hierarchical evidence tree displaying baseline statistics, wind vector stability, distance decay curves, and data completeness scores.

---

## 4. Geospatial Vector Mapping

### 4.1 Global Map Data Layer
- **Endpoint**: `GET /api/map`
- **Query Parameters**:
  - `region` (string, optional, default: `in-mp-indore`)
- **Description**: Returns all station coordinates, candidate facility markers, and event centroids for Leaflet rendering.

### 4.2 Event Vector Layer
- **Endpoint**: `GET /api/map/events/{event_id}`
- **Path Parameters**:
  - `event_id` (string, required)
- **Description**: Returns wind transport vectors, dispersion cones, and direct geometry vectors connecting the recording station to candidate facilities.

---

## 5. Agentic AI Assistant

### 5.1 Investigate Incident
- **Endpoint**: `POST /api/assistant/investigate`
- **Request Body**:
```json
{
  "query": "Investigate event EVT-0001 and identify the most likely industrial candidates.",
  "region": "in-mp-indore"
}
```
- **Response**:
```json
{
  "investigation_id": "INV-20261009-001",
  "task": "EVENT_INVESTIGATION",
  "target_event": "EVT-0001",
  "response": "Detailed natural language investigation summary...",
  "findings": {
    "event_summary": "...",
    "wind_conditions": "...",
    "top_candidates": [...]
  },
  "execution_trace": [
    {
      "step": 1,
      "tool_name": "get_event_details",
      "arguments": {"event_id": "EVT-0001"},
      "status": "SUCCESS",
      "execution_time_ms": 3.8
    }
  ],
  "warnings": [
    "Attribution score is a heuristic screening indicator and does not prove legal causation."
  ]
}
```

---

## 6. Investigation Reports Lifecycle

### 6.1 Generate Report
- **Endpoint**: `POST /api/reports`
- **Request Body**:
```json
{
  "event_id": "EVT-0001",
  "title": "Industrial Screening Audit - Event EVT-0001",
  "investigator": "Air Quality Directorate",
  "notes": "Triggered by sustained PM2.5 spike >140 µg/m³"
}
```
- **Response**: Serializes and returns report metadata including `report_id`, created timestamp, and download link.

### 6.2 List Reports
- **Endpoint**: `GET /api/reports`
- **Response**: List of saved investigation reports.

### 6.3 Retrieve Report Detail
- **Endpoint**: `GET /api/reports/{report_id}`
- **Path Parameters**:
  - `report_id` (string, required)
- **Response**: Complete stored report payload.

---

## 7. Ingestion & Model Lifecycle Operations

### 7.1 Ingestion Jobs Status
- **Endpoint**: `GET /api/ingestion/status`
- **Endpoint**: `GET /api/ingestion/jobs`
- **Response**: Returns history of ingestion jobs, last executed sync, records ingested, and errors.

### 7.2 Trigger Ingestion Run
- **Endpoint**: `POST /api/ingestion/run`
- **Request Body**:
```json
{
  "region": "in-mp-indore",
  "incremental": true
}
```
- **Response**: Job ID and queued status.

### 7.3 Model Status & Versions
- **Endpoint**: `GET /api/models/status`
- **Endpoint**: `GET /api/models/versions`
- **Response**: Active Isolation Forest version, training date, hyperparameters, and feature schema.

### 7.4 Trigger Model Training
- **Endpoint**: `POST /api/models/train`
- **Request Body**:
```json
{
  "model_type": "isolation_forest",
  "n_estimators": 300,
  "contamination": 0.02
}
```
- **Response**: Training execution result, trained estimators count, and artifact save path.
