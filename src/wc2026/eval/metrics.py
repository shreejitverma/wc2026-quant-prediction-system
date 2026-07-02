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
