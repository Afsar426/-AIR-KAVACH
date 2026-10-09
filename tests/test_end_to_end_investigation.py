import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_complete_end_to_end_investigation_workflow():
    """
    Executes mandatory acceptance E2E test workflow:
    1. Check system readiness & health
    2. Query Pan-India coverage matrix
    3. Select active validation region (Indore)
    4. Fetch real 15-min observations
    5. List confirmed pollution events
    6. Select an event (EVT-0001) and fetch details
    7. Fetch aligned meteorological wind context & evidence
    8. Retrieve candidate industrial facility rankings
    9. Run Agentic AI natural language investigation
    10. Inspect multi-step tool execution trace
    11. Compile and persist investigation report
    12. Query an unavailable region (Delhi) to confirm graceful coverage alert & zero leakage
    """
    # Step 1: Readiness
    ready_res = client.get("/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] in ("ready", "degraded")

    # Step 2: Coverage
    cov_res = client.get("/api/coverage")
    assert cov_res.status_code == 200
    regions = cov_res.json()["regions"]
    assert len(regions) >= 6

    # Step 3 & 4: Select Indore and fetch observations
    obs_res = client.get("/api/observations?city=Indore&limit=10")
    assert obs_res.status_code == 200
    obs_data = obs_res.json()
    assert obs_data["total"] > 8000
    assert len(obs_data["observations"]) == 10

    # Step 5: List confirmed events
    evts_res = client.get("/api/events?city=Indore&limit=5")
    assert evts_res.status_code == 200
    evts_data = evts_res.json()
    assert evts_data["total"] >= 40
    assert len(evts_data["events"]) >= 1

    first_event = evts_data["events"][0]
    target_event_id = first_event["event_id"]

    # Step 6: Fetch event details
    evt_detail_res = client.get(f"/api/events/{target_event_id}")
    assert evt_detail_res.status_code == 200
    assert evt_detail_res.json()["event"]["event_id"] == target_event_id

    # Step 7: Fetch evidence chain
    evidence_res = client.get(f"/api/evidence/{target_event_id}")
    assert evidence_res.status_code == 200
    ev_data = evidence_res.json()
    assert "event" in ev_data
    assert "limitations" in ev_data
    assert len(ev_data["limitations"]) >= 3

    # Step 8: Fetch candidate source rankings
    attr_res = client.get(f"/api/attribution/{target_event_id}?limit=5")
    assert attr_res.status_code == 200
    attr_data = attr_res.json()
    assert attr_data["event_id"] == target_event_id
    assert len(attr_data["candidates"]) >= 1
    top_cand = attr_data["candidates"][0]
    assert "factory_rank" in top_cand
    assert "attribution_score" in top_cand
    assert "wind_relationship" in top_cand

    # Step 9 & 10: Agentic AI investigation & trace verification
    agent_res = client.post("/api/assistant/investigate", json={
        "query": f"Investigate event {target_event_id} and screen candidate facilities",
        "event_id": target_event_id
    })
    assert agent_res.status_code == 200
    agent_data = agent_res.json()
    assert "summary" in agent_data
    assert "execution_trace" in agent_data
    trace = agent_data["execution_trace"]
    assert trace["status"] == "success"
    tool_names = [t["tool"] for t in trace["executed_tools"]]
    assert "get_event_details" in tool_names
    assert "rank_source_candidates" in tool_names

    # Step 11: Compile and persist report
    report_res = client.post("/api/reports", json={
        "event_id": target_event_id,
        "include_trace": True
    })
    assert report_res.status_code == 200
    rep_payload = report_res.json()
    assert rep_payload["event_id"] == target_event_id
    assert rep_payload["report_id"].startswith("REP-")
    assert "disclaimer" in rep_payload

    # Step 12: Verify unavailable region returns truthful coverage state
    delhi_summary = client.get("/api/summary?city=Delhi")
    assert delhi_summary.status_code == 200
    delhi_data = delhi_summary.json()
    assert delhi_data["total_observations"] == 0
    assert delhi_data["total_events"] == 0
    assert delhi_data["geographic_scope"]["coverage_status"] == "no_usable_data"
