import math
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from src.attribution.attribution_engine import (
    calculate_bearing,
    circular_angle_difference,
    calculate_alignment,
    calculate_distance_score,
    classify_alignment,
)
from src.geo.registry import GeoRegistryService, CoverageStatus
from src.agent.tools import AgentToolRegistry

client = TestClient(app)


# =====================================================================
# 1. SCIENTIFIC TESTS: METEOROLOGICAL CONVENTION & ANGULAR CALCULATIONS
# =====================================================================

def test_bearing_cardinal_directions():
    # Due North: lat increases, lon constant -> 0 degrees
    b_north = calculate_bearing(20.0, 75.0, 21.0, 75.0)
    assert pytest.approx(b_north, abs=0.1) == 0.0 or pytest.approx(b_north, abs=0.1) == 360.0

    # Due East: lat constant, lon increases -> 90 degrees
    b_east = calculate_bearing(20.0, 75.0, 20.0, 76.0)
    assert pytest.approx(b_east, abs=0.5) == 90.0

    # Due South: lat decreases, lon constant -> 180 degrees
    b_south = calculate_bearing(20.0, 75.0, 19.0, 75.0)
    assert pytest.approx(b_south, abs=0.1) == 180.0

    # Due West: lat constant, lon decreases -> 270 degrees
    b_west = calculate_bearing(20.0, 75.0, 20.0, 74.0)
    assert pytest.approx(b_west, abs=0.5) == 270.0


def test_circular_angle_difference_wraparound():
    # 0 deg and 360 deg equivalence
    assert pytest.approx(circular_angle_difference(0.0, 360.0), abs=1e-5) == 0.0
    assert pytest.approx(circular_angle_difference(10.0, 350.0), abs=1e-5) == 20.0

    # Opposite directions
    assert pytest.approx(circular_angle_difference(90.0, 270.0), abs=1e-5) == 180.0
    assert pytest.approx(circular_angle_difference(0.0, 180.0), abs=1e-5) == 180.0

    # Quadrant angles
    assert pytest.approx(circular_angle_difference(0.0, 90.0), abs=1e-5) == 90.0
    assert pytest.approx(circular_angle_difference(45.0, 315.0), abs=1e-5) == 90.0


def test_wind_from_convention_alignment():
    """
    Meteorological wind direction describes where wind comes FROM.
    If sensor is at origin, factory is to the West (bearing 270 deg),
    and wind is reported as 270 deg (FROM West, blowing East),
    then factory is directly UPWIND -> alignment +1.0.
    """
    # Factory is at 270 deg (West of sensor). Wind is FROM 270 deg (Westerly wind blowing toward East).
    alignment_upwind = calculate_alignment(270.0, 270.0)
    assert pytest.approx(alignment_upwind, abs=1e-5) == 1.0
    assert classify_alignment(alignment_upwind) == "strong_upwind"

    # Factory is at 270 deg. Wind is FROM 90 deg (Easterly wind blowing toward West).
    # Plume blows away from sensor -> DOWNWIND (-1.0).
    alignment_downwind = calculate_alignment(270.0, 90.0)
    assert pytest.approx(alignment_downwind, abs=1e-5) == -1.0
    assert classify_alignment(alignment_downwind) == "strong_downwind"

    # Factory is at 270 deg. Wind is FROM 0 deg (Northerly wind blowing South).
    # Crosswind -> alignment 0.0.
    alignment_crosswind = calculate_alignment(270.0, 0.0)
    assert pytest.approx(alignment_crosswind, abs=1e-5) == 0.0
    assert classify_alignment(alignment_crosswind) == "crosswind"


def test_distance_decay_exponential():
    # Distance 0 km -> score 1.0
    assert pytest.approx(calculate_distance_score(0.0), abs=1e-5) == 1.0

    # Distance 5 km (scale factor) -> score exp(-1) ~ 0.3678
    assert pytest.approx(calculate_distance_score(5.0), abs=1e-3) == math.exp(-1)

    # Distance 15 km -> significantly decayed
    assert calculate_distance_score(15.0) < 0.05

    # Negative distance guard
    assert calculate_distance_score(-1.0) == 0.0


# =====================================================================
# 2. PAN-INDIA ARCHITECTURE & GEOGRAPHIC ISOLATION TESTS
# =====================================================================

def test_pan_india_region_registry():
    regions = GeoRegistryService.get_all_regions()
    region_ids = [r["id"] for r in regions]
    assert "in-mp-indore" in region_ids
    assert "in-dl-delhi" in region_ids
    assert "in-mh-mumbai" in region_ids


def test_no_indore_leakage_on_unrelated_region():
    """
    Mandatory Acceptance Criterion:
    When an unrelated region (e.g. Delhi) is queried, the API must NOT
    return Indore observations or events.
    """
    # 1. Summary endpoint for Delhi
    res_delhi = client.get("/api/summary?city=Delhi")
    assert res_delhi.status_code == 200
    data_delhi = res_delhi.json()
    assert data_delhi["total_observations"] == 0
    assert data_delhi["total_events"] == 0
    assert data_delhi["total_stations"] == 0
    assert data_delhi["geographic_scope"]["coverage_status"] == "no_usable_data"

    # 2. Observations endpoint for Delhi
    res_obs = client.get("/api/observations?city=Delhi")
    assert res_obs.status_code == 200
    assert res_obs.json()["total"] == 0
    assert len(res_obs.json()["observations"]) == 0

    # 3. Events endpoint for Delhi
    res_evts = client.get("/api/events?city=Delhi")
    assert res_evts.status_code == 200
    assert res_evts.json()["total"] == 0
    assert len(res_evts.json()["events"]) == 0


def test_indore_validation_region_returns_data():
    res = client.get("/api/summary?city=Indore")
    assert res.status_code == 200
    data = res.json()
    assert data["total_observations"] > 8000
    assert data["total_events"] > 40
    assert data["total_stations"] == 4
    assert data["geographic_scope"]["coverage_status"] == "recent_data_available"


# =====================================================================
# 3. API SYSTEM & EXTENDED ENDPOINTS TESTS
# =====================================================================

def test_ready_endpoint():
    res = client.get("/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ready", "degraded")
    assert "files" in data
    assert data["geographic_regions_registered"] >= 6


def test_stations_endpoint():
    res = client.get("/api/stations")
    assert res.status_code == 200
    stations = res.json()["stations"]
    assert len(stations) == 4
    st_names = [s["station_name"] for s in stations]
    assert "Residency" in st_names
    assert "Maguda" in st_names


def test_coverage_endpoint():
    res = client.get("/api/coverage")
    assert res.status_code == 200
    data = res.json()
    assert data["national_scope"] == "Pan-India"
    assert len(data["regions"]) >= 6


def test_system_status_endpoint():
    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["backend"]["status"] == "online"
    assert data["storage"]["air_quality_dataset"] == "verified"
    assert data["models"]["isolation_forest"] == "active"
    assert data["geographic_readiness"]["pan_india_scope"] is True


def test_ingestion_jobs_endpoint():
    res = client.get("/api/ingestion/jobs")
    assert res.status_code == 200
    data = res.json()
    assert "jobs" in data
    assert len(data["jobs"]) >= 1


def test_reports_lifecycle_endpoint():
    # 1. Compile report
    res_gen = client.post("/api/reports", json={"event_id": "EVT-0001", "include_trace": True})
    assert res_gen.status_code == 200
    report_data = res_gen.json()
    report_id = report_data["report_id"]
    assert report_id.startswith("REP-")
    assert "investigation_summary" in report_data

    # 2. List reports
    res_list = client.get("/api/reports")
    assert res_list.status_code == 200
    reports = res_list.json()["reports"]
    assert isinstance(reports, list)

    # 3. Retrieve report by ID
    res_get = client.get(f"/api/reports/{report_id}")
    assert res_get.status_code == 200
    assert res_get.json()["report_id"] == report_id
