"""Fair value pricing."""

def calculate_fair_value(
    model_prob: float, 
    fee_adjustment: float = 0.0, 
    timing_discount: float = 0.0, 
    p_settlement_error: float = 0.0
) -> float:
    """
    Computes fair value price for binary options.
    
    Args:
        model_prob: Raw probability from model/simulator.
        fee_adjustment: Expected exchange fee friction.
        timing_discount: Capital lockup discount.
        p_settlement_error: Probability of UMA/resolution error mismatch.
        
    Returns:
        float bounded in [0.01, 0.99]
    """
    adjusted_prob = model_prob * (1 - p_settlement_error)
    fv = adjusted_prob - fee_adjustment - timing_discount
    return max(0.01, min(0.99, fv))

def compute_uncertainty_band(model_prob: float, std_dev: float = 0.05) -> tuple[float, float]:
    """
    Returns a symmetric uncertainty band. 
    In a full Bayesian model (Phase 3), this comes from the posterior predictive distribution.
    """
    return max(0.01, model_prob - std_dev), min(0.99, model_prob + std_dev)
