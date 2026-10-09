# AIR KAVACH - Environmental Data Providers & Ingestion Directory

This document details the multi-provider adapter layer integrated into the AIR KAVACH platform.

---

## 1. Provider Adapter Architecture

All providers implement `BaseProviderAdapter` (`src/ingestion/adapters/base_adapter.py`) and emit strictly normalized records (`NormalizedRecord`).
Data types are explicitly disaggregated to guarantee scientific honesty:
- `observed`: In-situ physical ground sensor measurements (CAAQMS).
- `modeled`: Atmospheric fluid dynamics or chemical transport models (CAMS/ECMWF).
- `satellite`: Spaceborne radiometer detections (MODIS/VIIRS).
- `cems`: Direct industrial facility continuous stack emissions.
- `derived`: Rolling statistical baselines, anomaly scores, and attribution indices.

---

## 2. Integrated Data Providers Catalog

### 2.1 OpenAQ API v3 (`openaq_v3`)
- **Category**: In-Situ Continuous Ambient Air Quality Monitoring (CAAQMS)
- **Data Type**: `observed`
- **Official Documentation**: `https://docs.openaq.org/docs/`
- **Base Endpoint**: `https://api.openaq.org/v3`
- **Key Resources**:
  - `/v3/sensors/{sensor_id}/measurements`
  - `/v3/locations` (geographic queries across India)
- **Parameters Supported**: `pm25`, `pm10`, `no2`, `so2`, `co`, `o3`
- **Authentication**: Optional header `X-API-Key` configured via `OPENAQ_API_KEY`. Operates on public unauthenticated tier if key omitted.
- **Rate Limits & Backoff**: Standard tier 5 req/s. Built-in HTTP 429 exponential backoff in `src/ingestion/adapters/openaq_adapter.py`.
- **Status in Platform**: **ACTIVE** (verified live & historical data in Indore).

---

### 2.2 Central Pollution Control Board / data.gov.in (`cpcb_datagov`)
- **Category**: Official National Air Quality Monitoring Network
- **Data Type**: `observed`
- **Official Documentation**: `https://data.gov.in/resource/real-time-air-quality-index`
- **Base Endpoint**: `https://api.data.gov.in/resource/3b0139f6-f772-47fa-8232-3228577ac712`
- **Parameters Supported**: `PM2.5`, `PM10`, `NO2`, `SO2`, `CO`, `Ozone`
- **Authentication**: Query parameter `api-key` configured via `DATAGOVIN_API_KEY`.
- **Normalization**: Formats Indian local datetime (`DD-MM-YYYY HH:MM:SS`) to ISO 8601 UTC.
- **Status in Platform**: **CONFIGURED** (adapter ready, offline/mock verified in test suite).

---

### 2.3 Open-Meteo Historical Weather API (`openmeteo_weather`)
- **Category**: Surface Meteorology & Planetary Boundary Layer
- **Data Type**: `observed` / `reanalysis`
- **Official Documentation**: `https://open-meteo.com/en/docs/historical-weather-api`
- **Base Endpoint**: `https://archive-api.open-meteo.com/v1/archive`
- **Parameters Supported**:
  - `wind_direction_10m` (Degrees clockwise from True North, strictly following meteorological **FROM** convention)
  - `wind_speed_10m` (converted from km/h to m/s)
  - `temperature_2m` (°C)
  - `relative_humidity_2m` (%)
- **Authentication**: None required (Free public open tier up to 10,000 requests/day).
- **Status in Platform**: **ACTIVE** (10,012 hourly observations in local store, live API adapter verified).

---

### 2.4 Open-Meteo Modeled Air Quality API (`openmeteo_airquality_model`)
- **Category**: Numerical Atmospheric Chemistry Grid Simulations
- **Data Type**: `modeled` *(Strictly segregated from observed sensor data)*
- **Model Source**: Copernicus Atmosphere Monitoring Service (CAMS) & ECMWF Atmospheric Chemical Reanalysis
- **Official Documentation**: `https://open-meteo.com/en/docs/air-quality-api`
- **Base Endpoint**: `https://air-quality-api.open-meteo.com/v1/air-quality`
- **Parameters Supported**: `pm2_5`, `pm10`, `nitrogen_dioxide`, `sulphur_dioxide`, `ozone`
- **Authentication**: None required.
- **Scientific Guardrail**: Used strictly for spatial comparison and background reference. Never substituted for sensor ground truth.
- **Status in Platform**: **ACTIVE** (live API adapter verified).

---

### 2.5 NASA FIRMS (`nasa_firms`)
- **Category**: Satellite Thermal Anomaly & Active Fire Detections
- **Data Type**: `satellite`
- **Sensors**: VIIRS (SNPP/NOAA-20/NOAA-21) and MODIS (Terra/Aqua)
- **Official Documentation**: `https://firms.modaps.eosdis.nasa.gov/api/`
- **Base Endpoint**: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/`
- **Parameters Supported**:
  - `fire_radiative_power` (FRP in Megawatts)
  - `bright_ti4` / `bright_ti5` (Brightness temperature in Kelvin)
  - `confidence`
- **Authentication**: Path parameter `MAP_KEY` via `NASA_FIRMS_MAP_KEY` (Free registration at EOSDIS).
- **Operational Utility**: Evaluates whether regional elevated particulate events coincide with agricultural stubble burning or forest fires rather than point-source industrial stacks.
- **Status in Platform**: **CONFIGURED** (adapter ready, offline/mock verified in test suite).

---

### 2.6 Authorized Continuous Emission Monitoring Systems (`cems_industrial_stack`)
- **Category**: Regulated In-Stack Industrial Telemetry
- **Data Type**: `cems`
- **Interface Schema**:
  - `facility_id`, `stack_id`, `timestamp`, `parameter` (`stack_pm`, `stack_so2`, `stack_nox`)
  - `concentration_mg_nm3`, `compliance_limit_mg_nm3`, `flue_gas_velocity_mps`, `flue_gas_temp_c`
- **Authentication**: Bearer token via `CEMS_AUTH_TOKEN`.
- **Status in Platform**: **INTERFACE READY** (adapter parses CEMS payloads and flags compliance exceedances).

---

### 2.7 Manual CSV & File Intake Layer (`csv_upload`)
- **Category**: User-Supplied Environmental Datasets
- **Supported Formats**: CSV with header row
- **Capabilities**:
  - Client-side and server-side preview (`POST /api/intake/preview`)
  - Dynamic column mapping (mapping custom names to `timestamp`, `value`, `station`, `parameter`, `latitude`, `longitude`, `unit`)
  - Quality validation card with error classification
  - Direct atomic persistence to Parquet lake (`POST /api/intake/commit`)
  - Automatic triggering of downstream event detection, wind alignment, and attribution scoring.
