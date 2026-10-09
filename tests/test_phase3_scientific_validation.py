import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from src.utils.config import (
    DATA_DIR,
    AIR_QUALITY_FILE,
    EVENTS_FILE,
    ATTRIBUTION_FILE,
    CONFIDENCE_FILE,
    REPORTS_DIR,
)
from src.event_detection.lifecycle import EventLifecycleManager, EventLifecycleState

client = TestClient(app)


def test_event_lifecycle_manager_five_states():
    """Validates that EventLifecycleManager accurately classifies all 5 lifecycle states."""
    ref_now = datetime(2026, 10, 9, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Insufficient data: < 4 readings
    st1, meta1 = EventLifecycleManager.evaluate_lifecycle(
        start_time=ref_now - timedelta(hours=2),
        end_time=ref_now - timedelta(hours=1),
        reading_count=2,
        reference_time=ref_now,
    )
    assert st1 == EventLifecycleState.INSUFFICIENT_DATA.value
    assert meta1["reading_count"] == 2

    # 2. Historical: ended > 30 days ago
    st2, meta2 = EventLifecycleManager.evaluate_lifecycle(
        start_time=ref_now - timedelta(days=45),
        end_time=ref_now - timedelta(days=40),
        reading_count=16,
        reference_time=ref_now,
    )
    assert st2 == EventLifecycleState.HISTORICAL.value
    assert meta2["hours_since_end"] > 30 * 24

    # 3. Recent: ended between 72h and 30 days ago
    st3, meta3 = EventLifecycleManager.evaluate_lifecycle(
        start_time=ref_now - timedelta(days=5),
        end_time=ref_now - timedelta(days=4),
        reading_count=12,
        reference_time=ref_now,
    )
    assert st3 == EventLifecycleState.RECENT.value

    # 4. Active: ended <= 6 hours ago and latest reading is still at end_time
    st4, meta4 = EventLifecycleManager.evaluate_lifecycle(
        start_time=ref_now - timedelta(hours=4),
        end_time=ref_now - timedelta(hours=1),
        reading_count=12,
        latest_observation=ref_now - timedelta(hours=1),
        reference_time=ref_now,
    )
    assert st4 == EventLifecycleState.ACTIVE.value

    # 5. Resolved: ended <= 72 hours ago and subsequent baseline readings received
    st5, meta5 = EventLifecycleManager.evaluate_lifecycle(
        start_time=ref_now - timedelta(hours=20),
        end_time=ref_now - timedelta(hours=15),
        reading_count=16,
        latest_observation=ref_now - timedelta(hours=1),
        reference_time=ref_now,
    )
    assert st5 == EventLifecycleState.RESOLVED.value


def test_backend_events_lifecycle_enrichment():
    """Ensures backend events endpoint provides lifecycle enrichment and labels historical events."""
    resp = client.get("/api/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0

    events = data["events"]
    for evt in events:
        assert "temporal_status" in evt
        assert evt["temporal_status"] in [
            "active", "resolved", "recent", "historical", "insufficient_data"
        ]
        assert "hours_since_end" in evt
        assert "latest_station_observation" in evt
        # In-archive events from September 2026 are either recent or historical, never falsely active
        assert evt["temporal_status"] in ["historical", "recent"]
        assert evt["temporal_status"] != "active"

    # Single event lookup: EVT-0001 ended > 35 days ago, strictly historical
    single_resp = client.get("/api/events/EVT-0001")
    assert single_resp.status_code == 200
    single_evt = single_resp.json()["event"]
    assert single_evt["event_id"] == "EVT-0001"
    assert single_evt["temporal_status"] == "historical"


def test_test_vs_prod_isolation_strict():
    """Verifies that test imports with is_test=True never mutate production parquet stores."""
    prod_parquet = AIR_QUALITY_FILE
    assert prod_parquet.exists()
    prod_before_len = len(pd.read_parquet(prod_parquet))

    test_region = "in-phase3-test-isolation"
    test_isolated_parquet = DATA_DIR / "test_intake" / f"{test_region}_air_quality.parquet"
    if test_isolated_parquet.exists():
        test_isolated_parquet.unlink()

    test_records = [
        {"station": "Test_Sensor", "timestamp": "2026-10-09T10:00:00Z", "parameter": "pm25", "value": 45.0, "unit": "µg/m³"},
        {"station": "Test_Sensor", "timestamp": "2026-10-09T10:15:00Z", "parameter": "pm25", "value": 52.0, "unit": "µg/m³"},
        {"station": "Test_Sensor", "timestamp": "2026-10-09T10:30:00Z", "parameter": "pm25", "value": 58.0, "unit": "µg/m³"},
    ]

    # Commit with is_test=True and environment="test"
    resp = client.post("/api/intake/commit", json={
        "records": test_records,
        "region_id": test_region,
        "source_label": "Phase 3 Isolation Test",
        "data_type": "observed",
        "is_test": True,
        "environment": "test",
    })
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["is_test"] is True
    assert res_data["environment"] == "test"
    assert "test_intake" in res_data.get("isolated_store", "")

    # Assert production parquet row count is strictly unchanged
    prod_after_len = len(pd.read_parquet(prod_parquet))
    assert prod_after_len == prod_before_len

    # Assert test data was saved to isolated directory
    assert test_isolated_parquet.exists()
    test_df = pd.read_parquet(test_isolated_parquet)
    assert len(test_df) == 3

    # Clean up test isolated file
    test_isolated_parquet.unlink()

    # Verify audit ledger environment filtering
    hist_test_resp = client.get("/api/intake/history?environment=test&limit=10")
    assert hist_test_resp.status_code == 200
    test_history = hist_test_resp.json()["history"]
    assert any(h.get("is_test") is True for h in test_history)

    hist_prod_resp = client.get("/api/intake/history?environment=production&limit=10")
    assert hist_prod_resp.status_code == 200
    prod_history = hist_prod_resp.json()["history"]
    assert all(h.get("environment") == "production" for h in prod_history)


def test_providers_status_truthful_metrics():
    """Verifies that provider status exposes real persistence metrics, data age, and honest coverage."""
    resp = client.get("/api/providers/status")
    assert resp.status_code == 200
    data = resp.json()
    providers = data["providers"]
    assert len(providers) >= 6

    prov_map = {p["provider_id"]: p for p in providers}

    # OpenAQ v3
    openaq = prov_map["openaq_v3"]
    assert openaq["records_persisted"] == 8211
    assert openaq["latest_observation_utc"] is not None
    assert openaq["data_age_hours"] is not None
    assert openaq["freshness_state"] in ["historical_archive", "fresh", "stale"]
    assert openaq["downstream_pipeline_status"] == "integrated"

    # Open-Meteo Weather
    meteo = prov_map["openmeteo_weather"]
    assert meteo["records_persisted"] == 10012
    assert meteo["latest_observation_utc"] is not None
    assert meteo["data_age_hours"] is not None

    # Modeled Copernicus Air Quality (must be explicitly labeled as modeled CAMS)
    cams = prov_map["openmeteo_airquality_model"]
    assert cams["status"] == "connected"
    assert cams["data_type"] == "modeled"
    assert cams["freshness_state"] == "modeled_cams_ready"
    assert "modeled" in cams["message"].lower() or "cams" in cams["message"].lower()

    # Unconfigured adapters (must not claim active connectivity)
    cpcb = prov_map["cpcb_datagov"]
    assert cpcb["status"] == "configured_pending_key"

    cems = prov_map["cems_industrial_stack"]
    assert cems["status"] == "awaiting_facility_authorization"
    assert cems["records_persisted"] == 0


def test_attribution_defensible_labels_and_share():
    """Verifies that attribution rankings contain defensible screening labels and screening score shares."""
    resp = client.get("/api/attribution/EVT-0001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_id"] == "EVT-0001"
    assert len(data["candidates"]) > 0

    candidates = data["candidates"]
    for c in candidates:
        # Must have screening score share
        assert "screening_score_share" in c
        assert 0.0 <= c["screening_score_share"] <= 1.0

        # Must have explicit CEMS absence guardrail
        assert "direct_emissions_evidence" in c
        assert "CEMS UNCONNECTED" in c["direct_emissions_evidence"]

        # Must NOT claim strong legal causation
        evidence_label = c.get("evidence_label", "")
        assert "strong_geospatial_wind_evidence" not in evidence_label
        assert evidence_label in [
            "GEOSPATIAL SCREENING SUPPORT",
            "WIND ALIGNMENT SUPPORT",
            "INSUFFICIENT METEOROLOGICAL EVIDENCE",
            "NEARBY BUT WIND MISALIGNED",
        ]


def test_agentic_report_disaggregation():
    """Verifies that investigation reports are disaggregated into explicit top-level sections."""
    # Test via POST /api/reports
    resp = client.post("/api/reports", json={"event_id": "EVT-0001", "include_trace": True})
    assert resp.status_code == 200
    rep = resp.json()

    # Validate explicit top-level sections
    assert "observed_facts" in rep
    assert "modeled_estimates" in rep
    assert "candidate_rankings" in rep
    assert "missing_evidence" in rep
    assert "limitations" in rep
    assert "provenance" in rep

    # Verify observed_facts fields
    obs = rep["observed_facts"]
    assert obs["station"] is not None
    assert obs["peak_pm25"] is not None
    assert obs["duration_minutes"] is not None

    # Verify modeled_estimates fields
    est = rep["modeled_estimates"]
    assert est["peak_z_score"] is not None
    assert "past-only" in est["baseline_method"]
    assert est["dispersion_scale_km"] == 5.0

    # Verify missing_evidence contents
    missing = rep["missing_evidence"]
    assert any("CEMS" in m for m in missing)

    # Verify limitations contents
    limitations = rep["limitations"]
    assert any("heuristic" in l.lower() for l in limitations)
    assert any("AERMOD" in l or "HYSPLIT" in l for l in limitations)

    # Verify persistent report file on disk
    report_id = rep["report_id"]
    report_file = REPORTS_DIR / "investigations" / f"{report_id}.json"
    assert report_file.exists()

    with report_file.open("r", encoding="utf-8") as rf:
        saved_data = json.load(rf)
        assert saved_data["report_id"] == report_id
        assert "observed_facts" in saved_data
        assert "modeled_estimates" in saved_data
        assert "candidate_rankings" in saved_data

    # Test via POST /api/assistant/investigate
    assist_resp = client.post("/api/assistant/investigate", json={
        "query": "Investigate event EVT-0001",
        "event_id": "EVT-0001"
    })
    assert assist_resp.status_code == 200
    assist_data = assist_resp.json()
    assert "observed_facts" in assist_data
    assert "modeled_estimates" in assist_data
    assert "candidate_rankings" in assist_data
    assert "missing_evidence" in assist_data
    assert "limitations" in assist_data
    assert "provenance" in assist_data
