"""Mock tournament draw table (Phase 2/3 UI work, ADR-0012 mock discipline).

A REAL draw-counting engine over FAKE draws: 20k simulated tournament paths,
deterministic per config seed, cached per process. Every probability the API
serves - group positions, best-third qualification, round-reach, winner, and
every joint query - is COUNTED from this one table, so internal coherence is
structural (P(A and B) <= min(P(A), P(B)) cannot be violated) and sample-size
honesty (n, Wilson CI) is real arithmetic, not decoration.

When the simulator persists its real ~100k draws, the endpoints swap this
table for a DuckDB scan; the counting logic is what carries over.

2026 format modeled: 48 teams, 12 groups of 4, top 2 advance plus the 8 best
third-placed teams -> 32. Knockout pairing is a per-draw shuffle (the real
bracket mapping arrives with the real simulator); winners advance by
strength-proportional Bernoulli.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

N_DRAWS = 20_000
GROUPS = "ABCDEFGHIJKL"  # 12 groups

# Real-ish field: the six fixture teams get top strengths; fillers complete 48.
_SEEDED = ["Brazil", "France", "Argentina", "England", "Spain", "USA"]
_FILLER = [
    "Germany", "Portugal", "Netherlands", "Belgium", "Italy", "Croatia",
    "Uruguay", "Colombia", "Mexico", "Japan", "Korea Rep", "Morocco",
    "Senegal", "Denmark", "Switzerland", "Austria", "Ecuador", "Canada",
    "Australia", "Nigeria", "Ghana", "Serbia", "Poland", "Ukraine",
    "Sweden", "Wales", "Peru", "Chile", "Costa Rica", "Panama",
    "Egypt", "Algeria", "Tunisia", "Cameroon", "Mali", "Ivory Coast",
    "Iran", "Saudi Arabia", "Qatar", "Uzbekistan", "New Zealand", "Jamaica",
]

# Stage codes for the reached[] table.
STAGE_GROUP = 0  # eliminated in group (3rd not qualified, or 4th)
STAGE_R32 = 1
STAGE_R16 = 2
STAGE_QF = 3
STAGE_SF = 4
STAGE_FINAL = 5
STAGE_CHAMPION = 6

OUTCOMES = {
    "wins_group": "wins the group",
    "qualifies": "reaches the round of 32",
    "reaches_r16": "reaches the round of 16",
    "reaches_qf": "reaches the quarter-final",
    "reaches_sf": "reaches the semi-final",
    "reaches_final": "reaches the final",
    "champion": "wins the tournament",
}


@dataclass(frozen=True)
class DrawTable:
    teams: list[str]                # 48 names
    group_of: np.ndarray            # (48,) int group index
    strength: np.ndarray            # (48,) float
    rank_in_group: np.ndarray       # (n_draws, 48) int 1..4
    reached: np.ndarray             # (n_draws, 48) int stage code
    best_third: np.ndarray          # (n_draws, 48) bool - qualified via best-third path

    @property
    def n_draws(self) -> int:
        return int(self.rank_in_group.shape[0])

    def team_index(self, team: str) -> int:
        try:
            return self.teams.index(team)
        except ValueError:
            raise KeyError(team) from None

    def event_mask(self, team: str, outcome: str) -> np.ndarray:
        """Boolean mask over draws for one (team, outcome) event."""
        i = self.team_index(team)
        if outcome == "wins_group":
            return self.rank_in_group[:, i] == 1
        stage = {
            "qualifies": STAGE_R32,
            "reaches_r16": STAGE_R16,
            "reaches_qf": STAGE_QF,
            "reaches_sf": STAGE_SF,
            "reaches_final": STAGE_FINAL,
            "champion": STAGE_CHAMPION,
        }[outcome]
        return self.reached[:, i] >= stage


def wilson_ci(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval - the band every counted probability wears."""
    if n == 0:
        return (0.0, 1.0)
    p = hits / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


@lru_cache(maxsize=2)
def draw_table(seed: int, n_draws: int = N_DRAWS) -> DrawTable:
    rng = np.random.default_rng(seed)
    teams = _SEEDED + _FILLER
    assert len(teams) == 48
    n_teams = 48

    # Strengths: log-normal-ish, seeded teams boosted; one seeded team per pot.
    strength = rng.lognormal(mean=0.0, sigma=0.5, size=n_teams)
    strength[: len(_SEEDED)] *= 3.0

    # Fixed group assignment: team k -> group k % 12 (one seeded team in each
    # of the first six groups).
    group_of = np.arange(n_teams) % 12

    rank_in_group = np.zeros((n_draws, n_teams), dtype=np.int8)
    reached = np.zeros((n_draws, n_teams), dtype=np.int8)
    best_third = np.zeros((n_draws, n_teams), dtype=bool)

    # Group stage: Plackett-Luce ranking via Gumbel trick, all draws at once.
    gumbel = rng.gumbel(size=(n_draws, n_teams))
    scores = np.log(strength)[None, :] + gumbel
    for g in range(12):
        idx = np.where(group_of == g)[0]
        order = np.argsort(-scores[:, idx], axis=1)  # (n_draws, 4) best-first
        for pos in range(4):
            rank_in_group[np.arange(n_draws), idx[order[:, pos]]] = pos + 1

    # Best thirds: 8 of the 12 third-placed teams, by the same draw's score.
    thirds_idx = np.zeros((n_draws, 12), dtype=np.int32)
    for g in range(12):
        idx = np.where(group_of == g)[0]
        third_pos = np.argmax(rank_in_group[:, idx] == 3, axis=1)
        thirds_idx[:, g] = idx[third_pos]
    third_scores = np.take_along_axis(scores, thirds_idx, axis=1)
    qualify_order = np.argsort(-third_scores, axis=1)[:, :8]
    for d in range(n_draws):
        best_third[d, thirds_idx[d, qualify_order[d]]] = True

    qualified = (rank_in_group <= 2) | best_third
    reached[qualified] = STAGE_R32

    # Knockout: per draw, shuffle the 32 qualifiers, pair, advance by
    # strength-proportional Bernoulli. Same generator per seed => reproducible.
    for d in range(n_draws):
        alive = np.where(qualified[d])[0]
        rng_d = np.random.default_rng(seed * 100_003 + d)
        rng_d.shuffle(alive)
        stage = STAGE_R32
        while len(alive) > 1:
            nxt = []
            for k in range(0, len(alive), 2):
                a, b = alive[k], alive[k + 1]
                p_a = strength[a] / (strength[a] + strength[b])
                winner = a if rng_d.random() < p_a else b
                nxt.append(winner)
            stage += 1
            alive = np.array(nxt)
            reached[d, alive] = stage
        # sole survivor already carries STAGE_CHAMPION via the last loop turn

    return DrawTable(
        teams=teams,
        group_of=group_of,
        strength=strength,
        rank_in_group=rank_in_group,
        reached=reached,
        best_third=best_third,
    )
