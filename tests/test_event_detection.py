import pytest
import pandas as pd
from src.event_detection.event_processor import EventProcessor

def test_event_processor():
    processor = EventProcessor()
    res = processor.process_events()
    assert res["status"] == "success"
    assert "events_detected" in res
    assert res["events_detected"] > 0
