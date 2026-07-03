# ADR-0005: Single point-in-time access gate, enforced by property tests

- **Status**: Accepted
- **Date**: 2026-07-01
- **Deciders**: Shreejit Verma

---

## Context

**Look-ahead bias is the dominant error term in sports prediction — not a minor one.**

Football outcomes are low-scoring Poisson noise with a genuinely low predictability ceiling. Legitimate signal exists, but it is small. The *apparent* skill injected by even a subtle data leakage can easily dwarf the real signal. Here are three examples of how leakage silently enters sports models:

| Leakage Type | Example | Why it inflates backtest performance |
|---|---|---|
| **Market value timing** | A player's transfer value scraped "today" (€120M) joined onto a match from 3 years ago when his value was €45M. | The model "knows" he became valuable; in reality, that information was unknowable. |
| **Suspension flags** | Using a red card flag to "predict" the match in which that card was shown. | The card happened *in* the match — it cannot be used to predict it. |
| **Closing odds timing** | Using the closing odds (sharp post-adjustment price) to predict what a pre-open market should be. | The closing odds *are* the result of sharp prediction; using them to predict themselves is circular. |

The core problem: **discipline does not survive month three of a solo build.** When a codebase has hundreds of features, each created under deadline pressure, it is practically certain that at least one feature join will accidentally pull future data. Manual review cannot catch all cases.

**Leak-prevention must be mechanical, not aspirational.**

---

## Decision

We will expose exactly **one read path for all features**: `as_of(ts)`.

This is implemented in `wc2026.pit.PointInTimeStore`. The interface works as follows:

```python
from wc2026.pit import PointInTimeStore

store = PointInTimeStore(data_source)

# At training time for a match on 2026-06-15T15:00:00Z:
features = store.as_of("2026-06-15T14:55:00Z")  # 5 minutes before kickoff
# Returns ONLY rows where knowable_at <= 2026-06-15T14:55:00Z
# A red card at 15:15:00Z is IMPOSSIBLE to retrieve via this call.
```

The invariant:
> `as_of(ts)` can **only ever return facts whose `knowable_at <= ts`.**

This invariant is enforced by **property-based tests** using `Hypothesis` (`tests/test_pit.py`), which generate thousands of random (ts, feature, knowable_at) combinations and assert:
1. No future fact ever leaks through (`knowable_at > ts`).
2. No admissible fact is ever dropped (`knowable_at <= ts` must appear in results).

These tests are wired into the **pre-commit hook** (`make hooks`), so a code change that breaks the PIT invariant cannot be committed to the repository.

---

## Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| **"Be careful in feature code"** | Promises, not proof. The first thing to fail under deadline pressure. An uncaught join error in a new feature leaves no visible error — just a silently inflated backtest. |
| **Timestamp columns without an enforced gate** | A column you can *forget* to filter on is not protection. The gate is the point. |
| **A feature-store product (Feast, Tecton)** | Heavy infrastructure adds operational burden and still does not give the property-test leak proof, which is the thing that actually matters. We need a proof that *no leakage is possible through the sanctioned path*; a managed service does not provide this. |

---

## Consequences

### Positive
- Look-ahead bias becomes **impossible to construct through the sanctioned path**, not merely discouraged.
- Every model and every backtest shares one verified, leak-proof gate.
- Backtest results become trustworthy: a pass is a pass, not a lucky leak.

### Negative / Cost
- Features must carry an honest `knowable_at` field, which forces careful thinking about when each datum was actually observable. This is a feature, not a bug — but it is additional discipline required when adding new data sources.

### Failure mode avoided
A beautiful backtest that produces a losing live book. This is the most common and most catastrophic failure mode in solo quantitative sports modeling.
