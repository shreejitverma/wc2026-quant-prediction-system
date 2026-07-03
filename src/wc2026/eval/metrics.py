"""Scoring Rules and Evaluation Metrics."""

import numpy as np
from sklearn.metrics import log_loss


def compute_log_loss(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Computes Log Loss (cross-entropy) for multi-class or binary predictions.
    y_true: (N, C) one-hot encoded or (N,) class indices.
    y_pred: (N, C) probabilities.
    """
    # scikit-learn log_loss handles small epsilon automatically
    return float(log_loss(y_true, y_pred))

def compute_brier_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Computes Brier Score (mean squared error of probabilities).
    y_true: (N, C) one-hot encoded
    y_pred: (N, C) probabilities
    """
    return float(np.mean(np.sum((y_pred - y_true)**2, axis=1)))

def compute_rps(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Ranked Probability Score (RPS) for ordinal outcomes (Away, Draw, Home).
    y_true: (N, 3) one-hot encoded
    y_pred: (N, 3) probabilities
    """
    # Cumulative sums
    cum_pred = np.cumsum(y_pred, axis=1)
    cum_true = np.cumsum(y_true, axis=1)
    
    # RPS is the mean of the sum of squared differences of the CDFs
    return float(np.mean(np.sum((cum_pred - cum_true)**2, axis=1)))


# --- Per-observation losses, bootstrap CIs, Diebold-Mariano (Phase 5) --------
# These are real pipeline statistics: the terminal's model-race page and the
# backtest harness share them. Every aggregate the UI shows must be able to
# name its n and its interval; these functions are where that honesty is made.

_EPS = 1e-12


def pointwise_log_loss(y_true: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Binary per-observation log loss. y_true in {0,1}, p = P(y=1)."""
    p = np.clip(p, _EPS, 1 - _EPS)
    return -(y_true * np.log(p) + (1 - y_true) * np.log(1 - p))


def pointwise_brier(y_true: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Binary per-observation Brier score."""
    return (p - y_true) ** 2


def bootstrap_ci(
    losses: np.ndarray, n_resamples: int = 1000, alpha: float = 0.05, seed: int = 0
) -> tuple[float, float]:
    """Percentile bootstrap CI for the MEAN of per-observation losses.
    Deterministic per seed - the UI must not show a CI that changes on reload."""
    rng = np.random.default_rng(seed)
    n = len(losses)
    idx = rng.integers(0, n, size=(n_resamples, n))
    means = losses[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


def diebold_mariano(loss_a: np.ndarray, loss_b: np.ndarray) -> tuple[float, bool]:
    """DM test on the loss differential d = loss_a - loss_b (same observations).

    Returns (dm_statistic, significant_at_5pct). Negative statistic means A's
    losses are lower (A better). Uses the large-sample normal approximation
    with the plain variance of d - adequate for exchangeable per-event
    forecasts; swap in a HAC variance if serial correlation ever matters.
    """
    d = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    n = len(d)
    var = d.var(ddof=1)
    if n < 2 or var <= _EPS:
        return 0.0, False
    stat = float(d.mean() / np.sqrt(var / n))
    return stat, abs(stat) > 1.959964
