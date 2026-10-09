from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from src.ingestion.adapters import (
    OpenAQAdapter,
    CPCBAdapter,
    OpenMeteoWeatherAdapter,
    OpenMeteoAirQualityAdapter,
    NASAFIRMSAdapter,
    CEMSAdapter,
    NormalizedRecord,
)
from src.ingestion.quality import QualityValidator, IntakeLedger
from src.ingestion.pipeline_connector import PipelineConnector

client = TestClient(app)


# ----------------------------------------------------------------------
# 1. PROVIDER NORMALIZATION TESTS (WITH MOCKED RESPONSES)
# ----------------------------------------------------------------------

def test_openaq_normalization():
    adapter = OpenAQAdapter()
    mock_payload = {
        "results": [
            {
                "id": 101,
                "period": {
                    "datetimeFrom": {"utc": "2026-09-02T14:15:00Z"},
                    "datetimeTo": {"utc": "2026-09-02T14:30:00Z"}
                },
                "value": 65.4,
                "parameter": {"name": "pm25", "units": "µg/m³"},
            }
        ]
    }

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        records = adapter.fetch_records(sensor_id=12238477, max_pages=1)
        assert len(records) == 1
        rec = records[0]
        assert rec.provider_id == "openaq_v3"
        assert rec.data_type == "observed"
        assert rec.parameter == "pm25"
        assert rec.value == 65.4
        assert rec.unit == "µg/m³"
        assert rec.quality_flag == "valid"
        assert rec.record_id is not None


def test_openmeteo_weather_normalization():
    adapter = OpenMeteoWeatherAdapter()
    mock_payload = {
        "hourly": {
            "time": ["2026-09-02T14:00", "2026-09-02T15:00"],
            "wind_direction_10m": [270.0, 180.0],
            "wind_speed_10m": [10.8, 7.2],  # In km/h (10.8 km/h = 3.0 m/s)
            "temperature_2m": [28.5, 27.9],
        }
    }

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        records = adapter.fetch_records(
            latitude=22.7126,
            longitude=75.8753,
            start_date="2026-09-02",
            end_date="2026-09-02",
        )
        assert len(records) > 0
        w_dir_recs = [r for r in records if r.parameter == "wind_direction_10m"]
        w_spd_recs = [r for r in records if r.parameter == "wind_speed_10m"]

        assert len(w_dir_recs) == 2
        assert w_dir_recs[0].value == 270.0  # FROM convention
        assert w_spd_recs[0].value == 3.0  # 10.8 km/h / 3.6 = 3.0 m/s
        assert w_spd_recs[0].unit == "m/s"


def test_openmeteo_airquality_modeled_label():
    adapter = OpenMeteoAirQualityAdapter()
    mock_payload = {
        "hourly": {
            "time": ["2026-09-02T14:00"],
            "pm2_5": [42.1],
            "pm10": [85.0],
            "nitrogen_dioxide": [22.4],
        }
    }

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        records = adapter.fetch_records(
            latitude=22.7126,
            longitude=75.8753,
            start_date="2026-09-02",
            end_date="2026-09-02",
        )
        assert len(records) == 3
        # Strict requirement: all records MUST be explicitly labeled 'modeled'
        for rec in records:
            assert rec.data_type == "modeled"


def test_cpcb_normalization():
    adapter = CPCBAdapter(api_key="TEST_KEY")
    mock_payload = {
        "records": [
            {
                "country": "India",
                "state": "Madhya Pradesh",
                "city": "Indore",
                "station": "Residency Area",
                "last_update": "02-09-2026 14:15:00",
                "pollutant_id": "PM2.5",
                "pollutant_avg": "58.0",
            }
        ]
    }

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        records = adapter.fetch_records(city="Indore")
        assert len(records) == 1
        rec = records[0]
        assert rec.parameter == "pm25"
        assert rec.value == 58.0
        assert rec.data_type == "observed"


def test_nasa_firms_normalization():
    adapter = NASAFIRMSAdapter(map_key="TEST_MAP_KEY")
    mock_csv_text = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight\n"
        "22.75,75.88,340.5,0.4,0.4,2026-09-02,1415,N,nominal,2.0NRT,295.2,14.5,D\n"
    )

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.text = mock_csv_text
        mock_get.return_value = mock_resp

        records = adapter.fetch_records(bounding_box=(75.0, 22.0, 76.0, 23.0))
        assert len(records) == 1
        rec = records[0]
        assert rec.data_type == "satellite"
        assert rec.parameter == "fire_radiative_power"
        assert rec.value == 14.5
        assert rec.unit == "MW"


def test_cems_normalization_and_exceedance():
    adapter = CEMSAdapter()
    raw_payload = [
        {
            "facility_id": "FAC-001",
            "stack_id": "STK-A",
            "timestamp": "2026-09-02T14:15:00Z",
            "parameter": "pm",
            "concentration_mg_nm3": 75.0,  # Exceeds limit 50.0
            "compliance_limit_mg_nm3": 50.0,
            "flue_gas_velocity_mps": 14.2,
        }
    ]
    records = adapter.normalize_cems_payload(raw_payload)
    assert len(records) == 1
    rec = records[0]
    assert rec.data_type == "cems"
    assert rec.parameter == "stack_pm"
    assert rec.value == 75.0
    assert rec.quality_flag == "suspect"  # Flagged because exceedance occurred
    assert "exceeds" in rec.quality_reason


# ----------------------------------------------------------------------
# 2. QUALITY VALIDATION & FRESHNESS ENGINE TESTS
# ----------------------------------------------------------------------

def test_quality_validator_bounds_and_invalid():
    # Negative PM2.5 concentration -> invalid
    neg_rec = NormalizedRecord(
        provider_id="test",
        data_type="observed",
        timestamp_utc="2026-09-02T14:15:00Z",
        parameter="pm25",
        value=-15.0,
        unit="µg/m³",
    )
    v_rec = QualityValidator.validate_record(neg_rec)
    assert v_rec.quality_flag == "invalid"
    assert "below physical minimum" in v_rec.quality_reason

    # Out of bounds coordinates -> invalid
    bad_coords_rec = NormalizedRecord(
        provider_id="test",
        data_type="observed",
        timestamp_utc="2026-09-02T14:15:00Z",
        latitude=125.0,  # > 90
        parameter="pm25",
        value=50.0,
        unit="µg/m³",
    )
    v_rec2 = QualityValidator.validate_record(bad_coords_rec)
    assert v_rec2.quality_flag == "invalid"
    assert "Latitude out of bounds" in v_rec2.quality_reason


def test_quality_validator_staleness():
    now_utc = datetime.now(timezone.utc)
    old_ts = (now_utc - timedelta(hours=100)).isoformat()

    stale_rec = NormalizedRecord(
        provider_id="test",
        data_type="observed",
        timestamp_utc=old_ts,
        retrieval_timestamp_utc=now_utc.isoformat(),
        parameter="pm25",
        value=45.0,
        unit="µg/m³",
    )
    v_rec = QualityValidator.validate_record(stale_rec, max_staleness_hours=72.0)
    assert v_rec.quality_flag == "stale"
    assert "hours old" in v_rec.quality_reason


# ----------------------------------------------------------------------
# 3. IDEMPOTENT INGESTION & PIPELINE CONNECTOR TESTS
# ----------------------------------------------------------------------

def test_idempotent_deduplication():
    connector = PipelineConnector()
    rec = NormalizedRecord(
        provider_id="unit_test",
        data_type="observed",
        timestamp_utc="2026-09-30T12:00:00Z",
        station_name="Residency",
        station_id="IND-RES-01",
        parameter="pm25",
        value=35.0,
        unit="µg/m³",
    )

    # Ingest once
    res1 = connector.ingest_and_process_air_quality([rec], region_id="in-dl-delhi")
    assert res1["status"] == "success"

    # Ingest identical record again
    res2 = connector.ingest_and_process_air_quality([rec], region_id="in-dl-delhi")
    assert res2["status"] == "success"
    # Net new inserted must be 0 because of deduplication
    assert res2["net_new_inserted"] == 0

    # Cleanup test file
    from pathlib import Path
    delhi_f = Path("data/processed/air_quality/in-dl-delhi_air_quality.parquet")
    if delhi_f.exists():
        delhi_f.unlink()


def test_provider_failure_resilience():
    adapter = OpenAQAdapter()
    with patch("requests.get", side_effect=Exception("Connection timed out")):
        status = adapter.health_check()
        assert status["status"] == "unavailable"
        assert "timed out" in status["error"]

        records = adapter.fetch_records(sensor_id=12238477)
        # Must return empty list gracefully without crashing
        assert records == []


# ----------------------------------------------------------------------
# 4. DATA INTAKE & PROVIDER REST API ENDPOINT TESTS
# ----------------------------------------------------------------------

def test_providers_status_endpoint():
    resp = client.get("/api/providers/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert len(data["providers"]) == 6
    provider_ids = [p["provider_id"] for p in data["providers"]]
    assert "openaq_v3" in provider_ids
    assert "openmeteo_weather" in provider_ids
    assert "nasa_firms" in provider_ids


def test_intake_preview_endpoint():
    sample_csv = (
        "time,site,reading,pollutant\n"
        "2026-09-02T14:15:00Z,Residency,48.5,pm25\n"
        "2026-09-02T14:30:00Z,Residency,52.1,pm25\n"
    )
    resp = client.post("/api/intake/preview", json={"csv_content": sample_csv})
    assert resp.status_code == 200
    data = resp.json()
    assert "columns" in data
    assert "time" in data["columns"]
    assert "reading" in data["columns"]
    assert data["suggested_mapping"]["timestamp"] == "time"
    assert data["suggested_mapping"]["value"] == "reading"
    assert data["validation_preview"]["counts"]["valid"] == 2


def test_intake_commit_endpoint():
    from pathlib import Path
    sample_records = [
        {
            "timestamp": "2026-09-02T14:15:00Z",
            "station": "Anand_Vihar",
            "value": 144.0,
            "parameter": "pm25",
            "unit": "µg/m³",
            "city": "Delhi",
        }
    ]
    resp = client.post(
        "/api/intake/commit",
        json={
            "records": sample_records,
            "region_id": "in-dl-delhi",
            "source_label": "Unit Test Delhi CSV",
            "data_type": "observed",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["records_accepted"] == 1

    # Cleanup temporary test parquet
    delhi_file = Path("data/processed/air_quality/in-dl-delhi_air_quality.parquet")
    if delhi_file.exists():
        delhi_file.unlink()


def test_intake_history_endpoint():
    resp = client.get("/api/intake/history?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "history" in data
    assert isinstance(data["history"], list)
    if data["history"]:
        first = data["history"][0]
        assert "job_id" in first
        assert "records_accepted" in first
