"""De-vigged market prices as features (M6 baseline) with admissibility guard.

Three de-vigging methods are computed for every Kalshi snapshot:
  1. Proportional (simplest): p_yes = yes_mid / (yes_mid + no_mid)
  2. Power (Forrest-Goddard-Simmons 2005): solve p^n + (1-p)^n = 1
  3. Shin (1993): corrects for favourite-longshot bias via insider-trading model

When to use each:
  - Proportional: default; robust; slight favourite-longshot bias remaining
  - Power: better calibration at the extremes; assumes symmetric overround
  - Shin: theoretically best for binary contracts where insiders exist; numerically
    fragile when spread is near zero (clamp inputs)

Admissibility rule (leakage guard):
  A market price snapshot is admissible as a FEATURE for match M if:
    snapshot_ts <= kickoff_ts - MIN_HORIZON
  where MIN_HORIZON = 24 hours for training data (avoids lineup-timing leakage)
  and = 0 seconds for live prediction (the current price is always admissible now).

This module computes and returns all three de-vigged probabilities; Phase 5
(fair value pricer) decides which to use for each market type. The M6 model
simply returns the proportional de-vigged price as its base prediction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from scipy.optimize import brentq

MIN_TRAINING_HORIZON = timedelta(hours=24)

# Numerical safeguards for extreme prices
_MIN_PRICE = 0.001
_MAX_PRICE = 0.999


@dataclass(frozen=True)
class DeViggedPrice:
    """All three de-vigged probability estimates from one market snapshot."""

    ticker: str
    snapshot_ts: str          # ISO UTC
    yes_ask_raw: float        # raw market ask (includes vig)
    yes_bid_raw: float        # raw market bid
    no_ask_raw: float
    no_bid_raw: float

    # De-vigged probabilities (YES resolves)
    p_proportional: float
    p_power: float
    p_shin: float

    @property
    def mid_raw(self) -> float:
        return (self.yes_ask_raw + self.yes_bid_raw) / 2

    @property
    def overround(self) -> float:
        """Total probability: should be > 1.0 (the vig); ~1.0 means tight spread."""
        return self.mid_raw + (1 - self.mid_raw)  # binary: always 1.0 by construction
        # For multi-way markets this would be sum(p_i); binary is special case


def _proportional_devig(p_yes_mid: float, p_no_mid: float) -> float:
    """De-vig by proportional normalisation.

    Simple and robust. Slight favourite-longshot bias remains because the vig
    is distributed proportionally rather than uniformly.
    """
    total = p_yes_mid + p_no_mid
    if total <= 0:
        return 0.5
    return p_yes_mid / total


def _power_devig(p_yes_mid: float, p_no_mid: float) -> float:
    """De-vig via power method (Forrest, Goddard & Simmons 2005).

    Find n such that p_yes^n + p_no^n = 1, then return p_yes^n.
    Better calibration at the extremes than proportional.
    """
    p_yes = max(_MIN_PRICE, min(_MAX_PRICE, p_yes_mid))
    p_no = max(_MIN_PRICE, min(_MAX_PRICE, p_no_mid))

    def f(n: float) -> float:
        return p_yes**n + p_no**n - 1.0

    try:
        n = brentq(f, 0.5, 20.0, xtol=1e-8)
        return p_yes**n
    except ValueError:
        return _proportional_devig(p_yes_mid, p_no_mid)


def _shin_devig(p_yes_mid: float, p_no_mid: float) -> float:
    """Shin's (1993) favourite-longshot correction.

    Models the vig as arising from insider trading on a binary market.
    z = fraction of insider volume. Solve for z, then back out true probabilities.

    For binary: p_true_yes = (sqrt(z^2 + 4(1-z)*p_raw*sum_p) - z) / (2*(1-z))
    where sum_p = p_yes_mid + p_no_mid.

    Numerically fragile when spread is near zero; falls back to proportional.
    """
    p_yes = max(_MIN_PRICE, min(_MAX_PRICE, p_yes_mid))
    p_no = max(_MIN_PRICE, min(_MAX_PRICE, p_no_mid))
    sum_p = p_yes + p_no

    if sum_p <= 1.0 + 1e-6:
        return _proportional_devig(p_yes_mid, p_no_mid)

    def shin_eq(z: float) -> float:
        if z <= 0 or z >= 1:
            return float("inf")
        return sum(
            math.sqrt(z**2 + 4 * (1 - z) * pi * sum_p) - z
            for pi in (p_yes, p_no)
        ) / (2 * (1 - z)) - 1.0

    try:
        z = brentq(shin_eq, 1e-8, 0.5, xtol=1e-8)
        p_true = (math.sqrt(z**2 + 4 * (1 - z) * p_yes * sum_p) - z) / (2 * (1 - z))
        return max(_MIN_PRICE, min(_MAX_PRICE, p_true))
    except ValueError:
        return _proportional_devig(p_yes_mid, p_no_mid)


def devig_kalshi_market(
    ticker: str,
    yes_ask: float,
    yes_bid: float,
    no_ask: float,
    no_bid: float,
    snapshot_ts: str,
) -> DeViggedPrice:
    """Compute all three de-vigged probabilities from a Kalshi market snapshot.

    Input prices are in USD (0.0–1.0). Mid-prices are used as the raw inputs
    to de-vigging (not ask or bid alone) to be symmetric around fair value.
    """
    yes_mid = (yes_ask + yes_bid) / 2
    no_mid = (no_ask + no_bid) / 2

    yes_mid = max(_MIN_PRICE, min(_MAX_PRICE, yes_mid))
    no_mid = max(_MIN_PRICE, min(_MAX_PRICE, no_mid))

    return DeViggedPrice(
        ticker=ticker,
        snapshot_ts=snapshot_ts,
        yes_ask_raw=yes_ask,
        yes_bid_raw=yes_bid,
        no_ask_raw=no_ask,
        no_bid_raw=no_bid,
        p_proportional=_proportional_devig(yes_mid, no_mid),
        p_power=_power_devig(yes_mid, no_mid),
        p_shin=_shin_devig(yes_mid, no_mid),
    )


def is_admissible_for_training(
    snapshot_ts: datetime,
    kickoff_ts: datetime,
    horizon: timedelta = MIN_TRAINING_HORIZON,
) -> bool:
    """True if this snapshot is safe to use as a training feature for this match.

    A price taken AFTER the lineup was released (typically 60-75 min pre-kickoff)
    may contain information about the confirmed lineup and is NOT admissible for
    pre-lineup prediction tasks. The 24h default is conservative and safe; it can
    be tightened in Phase 5 once we have lineup-release timestamps in the store.
    """
    return snapshot_ts <= kickoff_ts - horizon


def market_features_for_match(
    dv: DeViggedPrice,
    *,
    snapshot_ts: datetime,
    kickoff_ts: datetime | None = None,
    label_prefix: str = "kalshi",
) -> dict[str, float | None]:
    """Convert a DeViggedPrice into a flat feature dict.

    If kickoff_ts is provided, includes an admissibility flag and sets features
    to None if the snapshot is not admissible for training. For live prediction
    (kickoff_ts = None), all features are returned unconditionally.
    """
    admissible = (
        kickoff_ts is None or is_admissible_for_training(snapshot_ts, kickoff_ts)
    )
    if not admissible:
        return {
            f"{label_prefix}_p_proportional": None,
            f"{label_prefix}_p_power": None,
            f"{label_prefix}_p_shin": None,
            f"{label_prefix}_admissible": 0.0,
        }
    return {
        f"{label_prefix}_p_proportional": dv.p_proportional,
        f"{label_prefix}_p_power": dv.p_power,
        f"{label_prefix}_p_shin": dv.p_shin,
        f"{label_prefix}_admissible": 1.0,
    }
