import pytest
from src.ml.isolation_forest_service import IsolationForestService

def test_isolation_forest_lifecycle():
    service = IsolationForestService()
    status = service.get_status()
    assert status["status"] in ["active", "unavailable"]
    if status["status"] == "active":
        assert status["model_loaded"] is True
        assert "feature_schema" in status["metadata"]
