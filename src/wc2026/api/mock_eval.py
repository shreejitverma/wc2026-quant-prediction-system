"""Mock resolved-events table for the evaluation pages (Phase 5).

Same discipline as mock_tournament.py: REAL metric machinery (eval.metrics -
per-observation losses, bootstrap CIs, Diebold-Mariano) over FAKE resolved
events. ~400 settled binary contracts with per-model probabilities, a
de-vigged market probability, entry/close prices, and the realized outcome.
The generator gives models genuinely different skill (noise around the latent
truth) so the race page shows real statistical separation, not decoration.
Swaps for the backtest's persisted artifacts; the statistics carry over.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

N_EVENTS = 400
MARKET_CLASSES = ["1X2", "totals", "btts"]

# (model, noise_sigma, miscalibration): lower sigma = closer to latent truth.
# market_implied tracks the market; the ensemble is built from the others.
MODEL_SKILL = [
    ("dixon_coles", 0.06, 1.00),
    ("hierarchical", 0.07, 0.97),
    ("state_space", 0.09, 1.05),
    ("player_agg", 0.11, 0.93),
    ("gbm", 0.10, 1.08),
    ("market_implied", 0.05, 1.00),
]
ENSEMBLE_W = np.array([0.35, 0.25, 0.15, 0.10, 0.10, 0.05])


def _shrink(p: np.ndarray, factor: np.ndarray | float) -> np.ndarray:
    """Miscalibrate in log-odds space (factor>1 = overconfident)."""
    logit = np.log(p / (1 - p))
    return 1 / (1 + np.exp(-logit * factor))


@dataclass(frozen=True)
class EvalTable:
    ts_epoch: np.ndarray          # (N,) event resolution times, ascending
    market_class: np.ndarray      # (N,) str
    outcome: np.ndarray           # (N,) {0,1}
    market_p: np.ndarray          # (N,) de-vigged market prob at entry
    close_p: np.ndarray           # (N,) market prob at close (for CLV)
    entry_p: np.ndarray           # (N,) our entry price
    model_p: dict[str, np.ndarray]  # per model incl. "ensemble"
    weights_over_time: list[dict]   # [{ts_epoch, weights: {model: w}}]

    @property
    def n(self) -> int:
        return int(len(self.outcome))


@lru_cache(maxsize=2)
def eval_table(seed: int, n_events: int = N_EVENTS) -> EvalTable:
    rng = np.random.default_rng(seed + 555)
    true_p = np.clip(rng.beta(2.2, 2.2, n_events), 0.03, 0.97)
    outcome = (rng.random(n_events) < true_p).astype(float)
    market_class = rng.choice(MARKET_CLASSES, size=n_events, p=[0.5, 0.3, 0.2])

    model_p: dict[str, np.ndarray] = {}
    for name, sigma, miscal in MODEL_SKILL:
        noisy = np.clip(true_p + rng.normal(0, sigma, n_events), 0.01, 0.99)
        model_p[name] = _shrink(noisy, miscal)
    stacked = np.stack([model_p[m] for m, _, _ in MODEL_SKILL])
    model_p["ensemble"] = ENSEMBLE_W @ stacked

    # Market: skilled but slightly biased; close converges toward truth
    # (the market learns by close - that is what CLV measures against).
    market_p = np.clip(true_p + rng.normal(0, 0.055, n_events) + 0.012, 0.01, 0.99)
    close_p = np.clip(0.4 * market_p + 0.6 * true_p + rng.normal(0, 0.02, n_events), 0.01, 0.99)
    # Our entries: at market plus a slice of our model's disagreement.
    entry_p = np.clip(market_p + 0.3 * (model_p["ensemble"] - market_p), 0.01, 0.99)

    # Resolution times: spread over the 21 days before "now-ish" anchor.
    t0 = 1_782_000_000  # fixed epoch anchor: deterministic, reload-stable
    ts = np.sort(t0 + rng.uniform(0, 21 * 86_400, n_events))

    # Ensemble weights drift slowly over the window (for the evolution chart).
    weights_over_time = []
    for k in range(8):
        drift = rng.normal(0, 0.02, len(ENSEMBLE_W))
        w = np.clip(ENSEMBLE_W + drift * k / 8, 0.01, None)
        w = w / w.sum()
        weights_over_time.append(
            {
                "ts_epoch": float(t0 + k * 21 * 86_400 / 8),
                "weights": {m: float(w[i]) for i, (m, _, _) in enumerate(MODEL_SKILL)},
            }
        )

    return EvalTable(
        ts_epoch=ts,
        market_class=market_class,
        outcome=outcome,
        market_p=market_p,
        close_p=close_p,
        entry_p=entry_p,
        model_p=model_p,
        weights_over_time=weights_over_time,
    )
