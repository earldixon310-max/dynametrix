"""Unit tests for the verification engine.

Focused on pure functions (haversine, tier mapping). Database-coupled
functions (find_matching_events, evaluate_prediction, backfill) are
deferred to integration testing via the manual backfill run.
"""

import math

from app.services.verification_engine import (
    EARTH_RADIUS_KM,
    _tier_for,
    haversine_km,
)


# ---------- haversine_km ----------


def test_haversine_zero_distance():
    assert haversine_km(40.7357, -74.1724, 40.7357, -74.1724) == 0.0


def test_haversine_known_short_distance():
    # Newark, NJ (40.7357, -74.1724) to Manhattan / NYC (40.7128, -74.0060)
    # Real-world ~13.5 km
    d = haversine_km(40.7357, -74.1724, 40.7128, -74.0060)
    assert 13.0 < d < 14.5


def test_haversine_known_long_distance():
    # NYC (40.7128, -74.0060) to Los Angeles (34.0522, -118.2437)
    # Real-world ~3935 km
    d = haversine_km(40.7128, -74.0060, 34.0522, -118.2437)
    assert 3900 < d < 3970


def test_haversine_symmetric():
    # haversine(a, b) == haversine(b, a)
    a = haversine_km(40.0, -74.0, 35.0, -118.0)
    b = haversine_km(35.0, -118.0, 40.0, -74.0)
    assert math.isclose(a, b, rel_tol=1e-9)


def test_haversine_across_equator():
    # 10 degrees of latitude apart, straddling the equator: ~1110 km.
    d = haversine_km(5.0, 0.0, -5.0, 0.0)
    assert 1100 < d < 1115


def test_haversine_antipodes():
    # Maximum great-circle distance on Earth is half the circumference.
    d = haversine_km(0.0, 0.0, 0.0, 180.0)
    expected = math.pi * EARTH_RADIUS_KM
    assert math.isclose(d, expected, rel_tol=1e-3)


def test_haversine_pole_to_equator():
    # North pole to equator at the same longitude: quarter circumference.
    d = haversine_km(90.0, 0.0, 0.0, 0.0)
    expected = (math.pi / 2.0) * EARTH_RADIUS_KM
    assert math.isclose(d, expected, rel_tol=1e-3)


def test_haversine_one_degree_latitude_is_about_111km():
    d = haversine_km(40.0, -74.0, 41.0, -74.0)
    assert 110.0 < d < 112.0


# ---------- _tier_for ----------


def test_tier_none_returns_quiet():
    assert _tier_for(None) == "QUIET"


def test_tier_below_30_is_quiet():
    assert _tier_for(0.0) == "QUIET"
    assert _tier_for(0.29) == "QUIET"


def test_tier_30_to_50_is_monitor():
    assert _tier_for(0.30) == "MONITOR"
    assert _tier_for(0.49) == "MONITOR"


def test_tier_50_to_70_is_elevated():
    assert _tier_for(0.50) == "ELEVATED"
    assert _tier_for(0.69) == "ELEVATED"


def test_tier_at_or_above_70_is_imminent():
    assert _tier_for(0.70) == "IMMINENT"
    assert _tier_for(1.00) == "IMMINENT"