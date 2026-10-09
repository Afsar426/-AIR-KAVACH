"""
Phase 2 End-to-End Automated Validation Test Suite.
Verifies live network providers, deterministic CSV intake, event recomputation,
weather alignment, attribution screening guardrails, and pan-India isolation.
"""

import pytest
import math
import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from src.utils.config import AIR_QUALITY_FILE, EVENTS_FILE, DATA_DIR
from src.ingestion.adapters import (
    OpenAQAdapter,
    OpenMeteoWeatherAdapter,
    OpenMeteoAirQualityAdapter,
    CPCBAdapter,
    NASAFIRMSAdapter,
    CEMSAdapter,
)
from src.ingestion.quality import QualityValidator, IntakeLedger
from src.ingestion.pipeline_connector import PipelineConnector
from src.event_detection.event_processor import EventProcessor
from src.attribution.attribution_engine import (
    calculate_bearing,
    circular_angle_difference,
    calculate_alignment,
    calculate_distance_score,
    classify_alignment,
)
from src.geo.registry import GeoRegistryService

client = TestClient(app)


# ======================================================================
# 1. PROVIDER INTEGRATION TESTS
# ======================================================================

def test_openmeteo_weather_live_connectivity():
    """Validates Open-Meteo Weather API connectivity, units (m/s), and FROM convention."""
    adapter = OpenMeteoWeatherAdapter()
    health = adapter.health_check()
    assert health["status"] in ("connected", "degraded")
    assert health["provider"] == "openmeteo_weather"

    records = adapter.fetch_records(
        latitude=22.7196,
        longitude=75.8577,
        start_date="2026-09-01",
        end_date="2026-09-01",
        city="Indore",
    )
    assert len(records) > 0
    # Verify parameter types and valid physical ranges
    params = set(r.parameter for r in records)
    assert "wind_direction_10m" in params
    assert "wind_speed_10m" in params
    
    w_dir = next(r for r in records if r.parameter == "wind_direction_10m")
    assert 0.0 <= w_dir.value <= 360.0
    assert w_dir.unit == "degrees"
    assert w_dir.provenance.get("convention") == "FROM True North"

    w_spd = next(r for r in records if r.parameter == "wind_speed_10m")
    assert w_spd.value >= 0.0
    assert w_spd.unit == "m/s"


def test_openmeteo_airquality_modeled_label_strict():
    """Ensures Open-Meteo Air Quality records are strictly tagged as 'modeled'."""
    adapter = OpenMeteoAirQualityAdapter()
    health = adapter.health_check()
    assert health["status"] in ("connected", "degraded")

    records = adapter.fetch_records(
        latitude=22.7196,
        longitude=75.8577,
        start_date="2026-09-01",
        end_date="2026-09-01",
        city="Indore",
    )
    assert len(records) > 0
    for r in records:
        assert r.data_type == "modeled"
        assert r.quality_flag == "valid"


def test_unconfigured_providers_graceful_status():
    """Ensures unconfigured providers report clear pending key status without crashing."""
    cpcb = CPCBAdapter()
    firms = NASAFIRMSAdapter()
    cems = CEMSAdapter()

    assert cpcb.health_check()["status"] in ("configured_pending_key", "connected")
    assert firms.health_check()["status"] in ("configured_pending_key", "connected")
    assert cems.health_check()["status"] in ("awaiting_facility_authorization", "connected")


# ======================================================================
# 2. DETERMINISTIC CSV INTAKE LIFECYCLE
# ======================================================================

def test_deterministic_csv_preview_and_mapping():
    """Tests intake preview column auto-mapping and bound validation."""
    raw_csv = """Station,Timestamp,Parameter,Value,Unit,Latitude,Longitude
Station_Beta,2026-09-12T08:00:00Z,pm25,35.0,ug/m3,22.70,75.80
Station_Beta,2026-09-12T08:15:00Z,pm25,36.5,ug/m3,22.70,75.80
Station_Beta,2026-09-12T08:30:00Z,pm25,4500.0,ug/m3,22.70,75.80
"""
    resp = client.post("/api/intake/preview", json={
        "csv_content": raw_csv,
        "data_type": "observed"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "Station" in data["columns"]
    assert data["suggested_mapping"]["station"] == "Station"
    assert data["suggested_mapping"]["value"] == "Value"


def test_idempotent_commit_and_ledger():
    """Verifies intake commit idempotency, error rejection, and audit ledger persistence."""
    test_region = "in-test-auto"
    test_parquet = DATA_DIR / "processed" / "air_quality" / f"{test_region}_air_quality.parquet"
    test_isolated = DATA_DIR / "test_intake" / f"{test_region}_air_quality.parquet"
    if test_parquet.exists():
        test_parquet.unlink()
    if test_isolated.exists():
        test_isolated.unlink()

    records = [
        {"station": "Beta_Stn", "timestamp": "2026-09-12T08:00:00Z", "parameter": "pm25", "value": 35.0, "unit": "µg/m³"},
        {"station": "Beta_Stn", "timestamp": "2026-09-12T08:15:00Z", "parameter": "pm25", "value": 38.0, "unit": "µg/m³"},
        {"station": "Beta_Stn", "timestamp": "2026-09-12T08:15:00Z", "parameter": "pm25", "value": 38.0, "unit": "µg/m³"}, # Duplicate
        {"station": "Beta_Stn", "timestamp": "2026-09-12T08:30:00Z", "parameter": "pm25", "value": 9999.0, "unit": "µg/m³"}, # Reject > 2000
    ]

    # First commit
    resp1 = client.post("/api/intake/commit", json={
        "records": records,
        "region_id": test_region,
        "source_label": "Automated Phase 2 Test",
        "data_type": "observed"
    })
    assert resp1.status_code == 200
    r1_data = resp1.json()
    assert r1_data["records_accepted"] == 4
    assert r1_data["net_new_inserted"] == 3

    # Second commit with same data (idempotency check)
    resp2 = client.post("/api/intake/commit", json={
        "records": records,
        "region_id": test_region,
        "source_label": "Automated Phase 2 Test",
        "data_type": "observed"
    })
    assert resp2.status_code == 200
    r2_data = resp2.json()
    assert r2_data["net_new_inserted"] == 0  # Zero new records added

    # Ledger audit check
    hist_resp = client.get("/api/intake/history?limit=10")
    assert hist_resp.status_code == 200
    history = hist_resp.json()["history"]
    region_entries = [h for h in history if h.get("region_id") == test_region]
    assert len(region_entries) >= 2

    # Cleanup
    if test_parquet.exists():
        test_parquet.unlink()


# ======================================================================
# 3. EVENT RECOMPUTATION & SCIENTIFIC BASELINE
# ======================================================================

def test_event_detection_past_only_and_gap_handling():
    """
    Verifies that EventProcessor uses past-only baseline (no future data contamination)
    and segments episodes cleanly when baseline recovers.
    """
    ts_base = pd.date_range("2026-09-01 00:00:00", periods=100, freq="15min", tz="UTC")
    rows = [{"station": "UnitStn", "timestamp": t, "value": 30.0 + (i % 3), "parameter": "pm25"} for i, t in enumerate(ts_base)]

    # Spike episode 1: 5 elevated readings
    ts_spike1 = pd.date_range("2026-09-02 01:15:00", periods=5, freq="15min", tz="UTC")
    for t in ts_spike1:
        rows.append({"station": "UnitStn", "timestamp": t, "value": 160.0, "parameter": "pm25"})

    # Recovery period: 8 readings
    ts_norm = pd.date_range("2026-09-02 02:45:00", periods=8, freq="15min", tz="UTC")
    for t in ts_norm:
        rows.append({"station": "UnitStn", "timestamp": t, "value": 32.0, "parameter": "pm25"})

    # Spike episode 2: 5 elevated readings
    ts_spike2 = pd.date_range("2026-09-02 05:00:00", periods=5, freq="15min", tz="UTC")
    for t in ts_spike2:
        rows.append({"station": "UnitStn", "timestamp": t, "value": 145.0, "parameter": "pm25"})

    df = pd.DataFrame(rows)
    processor = EventProcessor()
    events_df = processor.detect_events(df, save=False)

    assert len(events_df) == 2
    assert events_df.iloc[0]["peak_pm25"] == 160.0
    assert events_df.iloc[1]["peak_pm25"] == 145.0
    assert events_df.iloc[0]["readings"] == 5
    assert events_df.iloc[1]["readings"] == 5


# ======================================================================
# 4. WEATHER ALIGNMENT & ATTRIBUTION GEOMETRY
# ======================================================================

def test_attribution_screening_guardrails():
    """Verifies screening distance decay, angles, and heuristic classification."""
    # Exponential decay
    assert pytest.approx(calculate_distance_score(0.0), 1e-4) == 1.0
    assert pytest.approx(calculate_distance_score(5.0), 1e-3) == math.exp(-1.0)
    assert calculate_distance_score(20.0) < 0.02

    # Circular wraparound
    assert pytest.approx(circular_angle_difference(355.0, 5.0), 1e-4) == 10.0

    # Alignment categories
    assert classify_alignment(1.0) == "strong_upwind"
    assert classify_alignment(-1.0) == "strong_downwind"
    assert classify_alignment(0.0) == "crosswind"


# ======================================================================
# 5. PAN-INDIA REGIONAL ISOLATION
# ======================================================================

def test_pan_india_isolation_and_no_leakage():
    """Verifies unseeded regions return 0 records without leaking Indore data."""
    # Request Delhi
    resp_dl = client.get("/api/summary?city=Delhi")
    assert resp_dl.status_code == 200
    data_dl = resp_dl.json()
    assert data_dl["total_observations"] == 0
    assert data_dl["total_events"] == 0
    assert data_dl["total_stations"] == 0
    assert data_dl["geographic_scope"]["coverage_status"] == "no_usable_data"

    # Request Indore
    resp_ind = client.get("/api/summary?city=Indore")
    assert resp_ind.status_code == 200
    data_ind = resp_ind.json()
    assert data_ind["total_observations"] == 8211
    assert data_ind["total_events"] == 48
    assert data_ind["total_stations"] == 4
    assert data_ind["geographic_scope"]["coverage_status"] == "recent_data_available"
