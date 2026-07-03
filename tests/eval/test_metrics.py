import numpy as np

from wc2026.eval.metrics import compute_brier_score, compute_log_loss, compute_rps


def test_metrics():
    y_true = np.array([[1, 0, 0]])
    y_pred = np.array([[0.8, 0.1, 0.1]])
    
    ll = compute_log_loss(y_true, y_pred)
    brier = compute_brier_score(y_true, y_pred)
    rps = compute_rps(y_true, y_pred)
    
    assert ll > 0
    assert brier > 0
    assert rps > 0
