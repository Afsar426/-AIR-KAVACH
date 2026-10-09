import pytest
from src.ingestion.openaq_ingestion import OpenAQIngestionService

def test_ingestion_status():
    service = OpenAQIngestionService()
    status = service.get_ingestion_status()
    assert "status" in status
    assert "total_observations" in status
    assert status["status"] in ["healthy", "empty", "no_data"]
