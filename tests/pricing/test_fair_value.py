import pytest

from wc2026.pricing.fair_value import calculate_fair_value, compute_uncertainty_band


def test_fair_value():
    assert calculate_fair_value(0.50) == 0.50
    assert calculate_fair_value(0.50, fee_adjustment=0.01) == 0.49
    assert calculate_fair_value(0.50, p_settlement_error=0.1) == 0.45
    
    # bounds checking
    assert calculate_fair_value(0.999) == 0.99
    assert calculate_fair_value(0.001) == 0.01

def test_uncertainty_band():
    low, high = compute_uncertainty_band(0.50, 0.05)
    assert pytest.approx(low) == 0.45
    assert pytest.approx(high) == 0.55
    
    # bounds checking
    low, high = compute_uncertainty_band(0.98, 0.05)
    assert pytest.approx(low) == 0.93
    assert pytest.approx(high) == 0.99
    
    low, high = compute_uncertainty_band(0.02, 0.05)
    assert pytest.approx(low) == 0.01
    assert pytest.approx(high) == 0.07
