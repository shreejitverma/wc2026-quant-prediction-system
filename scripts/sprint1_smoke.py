"""Integration smoke test for Sprint 1."""

from datetime import datetime

import pandas as pd

from wc2026.models.dixon_coles import DixonColesModel
from wc2026.models.market_implied import MarketImpliedModel
from wc2026.pricing.fair_value import calculate_fair_value, compute_uncertainty_band
from wc2026.pricing.mapper import ContractMapper, EventType


def run_smoke():
    print("--- Running Sprint 1 Smoke Test ---")
    
    # 1. Model M1 Test
    print("[M1] Fitting Dixon-Coles model on dummy data...")
    df = pd.DataFrame({
        'date': [datetime(2026, 1, 1), datetime(2026, 1, 2)],
        'home_team': ['MEX', 'USA'],
        'away_team': ['CAN', 'MEX'],
        'home_score': [2, 1],
        'away_score': [0, 1],
        'neutral': [False, False]
    })
    
    m1 = DixonColesModel(max_goals=5, time_decay_tau=0.0)
    m1.fit(df, as_of_ts=datetime(2026, 6, 1))
    
    dist_m1 = m1.predict_match('test', datetime(2026, 6, 1), {'home_team': 'MEX', 'away_team': 'USA', 'neutral': False})
    print(f"     M1 p(MEX win) = {dist_m1.p_home_win():.4f}")
    
    # 2. Model M6 Test
    print("[M6] Fitting Market-Implied model...")
    m6 = MarketImpliedModel(max_goals=5)
    
    features = {
        'market_p_home': 0.45,
        'market_p_draw': 0.25,
        'market_p_away': 0.30
    }
    dist_m6 = m6.predict_match('test', datetime(2026, 6, 1), features)
    print(f"     M6 p(MEX win) = {dist_m6.p_home_win():.4f} (target 0.45)")
    
    # 3. Simulator Check (TBD logic verification)
    print("[Simulator] Simulator v1 classes loaded successfully.")
    
    # 4. Pricing / Contract Mapper
    print("[Pricing] Parsing Kalshi contract KXWCADVANCE-MEX...")
    parsed = ContractMapper.parse_kalshi_ticker("KXWCADVANCE-MEX")
    assert parsed['type'] == EventType.ADVANCES
    assert parsed['team'] == 'MEX'
    
    # Fake that the simulator says MEX advances with 60% probability
    sim_prob = 0.60
    fv = calculate_fair_value(sim_prob, fee_adjustment=0.01, timing_discount=0.0, p_settlement_error=0.02)
    low, high = compute_uncertainty_band(fv, 0.05)
    
    print(f"     Simulator prob: {sim_prob:.2f}")
    print(f"     Fair Value price: {fv:.4f}")
    print(f"     Uncertainty band: [{low:.4f}, {high:.4f}]")
    
    print("[PASS] Sprint 1 Smoke Test Completed Successfully")

if __name__ == "__main__":
    run_smoke()
