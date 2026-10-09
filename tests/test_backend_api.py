import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root_and_health():
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json()["project"] == "AIR KAVACH"

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert "status" in res_health.json()

def test_summary_endpoint():
    res = client.get("/api/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_observations"] > 0
    assert data["total_events"] > 0
    assert len(data["stations"]) == 4

def test_events_endpoint():
    res = client.get("/api/events")
    assert res.status_code == 200
    data = res.json()
    assert "events" in data
    assert len(data["events"]) > 0

def test_attribution_endpoint():
    res = client.get("/api/attribution/EVT-0001")
    assert res.status_code == 200
    data = res.json()
    assert data["event_id"] == "EVT-0001"
    assert len(data["candidates"]) > 0

def test_assistant_endpoint():
    res = client.post("/api/assistant/investigate", json={"query": "Investigate event EVT-0001", "event_id": "EVT-0001"})
    assert res.status_code == 200
    data = res.json()
    assert "request_id" in data
    assert "execution_trace" in data
