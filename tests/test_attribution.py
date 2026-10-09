import pytest
from src.attribution.attribution_engine import (
    calculate_bearing,
    circular_angle_difference,
    calculate_alignment,
    calculate_distance_score,
)

def test_geospatial_calculations():
    # Test bearing from (0,0) to (1,0) - due North
    b = calculate_bearing(0, 0, 1, 0)
    assert round(b, 1) == 0.0

    # Test circular angle difference
    diff = circular_angle_difference(90, 45)
    assert diff == 45.0

    # Test alignment (due North wind with due North factory bearing = 1.0)
    align = calculate_alignment(0, 0)
    assert round(align, 2) == 1.0

    # Test distance decay at 0 km = 1.0, at 5 km = e^-1 ~= 0.3679
    score0 = calculate_distance_score(0)
    score5 = calculate_distance_score(5.0)
    assert round(score0, 2) == 1.0
    assert round(score5, 3) == 0.368
