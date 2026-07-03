# The Honesty Harness

The **Honesty Harness** is the collective set of cryptographic, architectural, and time-discipline guardrails built into the WC2026 Prediction System. Its sole purpose is to make cheating — whether intentional or accidental — structurally impossible. 

In quantitative research, look-ahead bias, data leakage, and selective metric reporting are the dominant failure modes. This harness enforces research integrity at the compiler and testing level.

---

## 1. Subsystem Interlock Matrix

The harness consists of five distinct components that enforce constraints at different layers of the system:

| Harness Component | Target Threat | Enforcement Mechanism | Failure Consequence |
| :--- | :--- | :--- | :--- |
| **Tamper-Evident Ledger** | Cherry-picking; post-hoc backtest adjustments | SHA-256 hash chaining of rows; contiguous sequence numbers | Chain validation (`verify_chain()`) fails on startup; CI rejects commit. |
| **Point-in-Time Gate** | Future leakage; training on post-event data | Unified SQL filter `knowable_at <= as_of_ts` in DuckDB | Out-of-sample performance appears artificially high, leading to live loss. |
| **Pre-registration** | $p$-hacking; selective metric reporting | Git commit freeze of metric thresholds *before* execution | Invalidates validation results; model cannot be promoted. |
| **UTC-Only Time** | Timezone leaks; timeline inversion | Naive `datetime` instances rejected at package boundaries | Silent timezone offset shift (e.g., UTC vs EST) leaks data. |
| **Config Fences** | Accidental live execution; autonomous trading | Pydantic validation; `Literal[False]` configuration types | Invalid configuration prevents CLI execution or server boot. |

---

## 2. Component Deep-Dives

### 2.1 The Tamper-Evident Ledger

The ledger is the source of truth for the system's performance. It is stored as newline-delimited JSON (JSONL) to combine append-only I/O efficiency with human readability.

#### Cryptographic Chain Mechanics

Every row $n$ in the ledger is cryptographically linked to row $n-1$:

$$
H_n = \text{SHA-256}\Big(\text{CanonicalJSON}\big(\{ \text{seq}_n, \text{ts\_utc}_n, \text{kind}_n, H_{n-1}, \text{payload}_n \}\big)\Big)
$$

Where:
- $\text{seq}_n = \text{seq}_{n-1} + 1$: Monotonically increasing sequence number.
- $H_{n-1} = \text{prev\_hash}$: The hash of the previous row.
- $H_n = \text{row\_hash}$: The cryptographic digest of the current row.

#### Chain Validation Algorithm

When `wc2026.ledger.verify_chain()` runs:
1. It reads `ledger.jsonl` sequentially.
2. It asserts $\text{seq}_n == \text{seq}_{n-1} + 1$. Any missing row raises a `SequenceGapError`.
3. It recomputes the SHA-256 hash of the row payload combined with the previous hash and checks if it matches the stored `row_hash`. Any mismatch raises a `TamperEventError`.
4. The system validates the entire chain from the genesis block (seq=1) to the tip before allowing the execution engine to boot.

---

### 2.2 Point-in-Time (PIT) Gating

The PIT gate is the single query boundary through which all feature and historical rating data must flow.

#### The Point-in-Time Invariant

For any query evaluated at timestamp $T$, the database must only return rows where:

$$
\text{knowable\_at} \le T
```
           Match Kickoff (15:00 UTC)
─────────────────┿──────────────────► Time
        ▲                  ▲
    as_of (14:55)     Goal (15:15)
 (Goal is INadmissible)  (knowable_at = 15:15)
```

#### Verification via Property-Based Testing

Because PIT gating is safety-critical, we enforce it using property-based testing (`tests/features/test_store_pit.py`) powered by `Hypothesis`.
The property asserts:
- Let $D$ be a random dataset.
- Let $T_c$ be a random evaluation cutoff timestamp.
- For all records returned by the store, assert $T_{\text{knowable}} \le T_c$.
- For all records not returned by the store, assert $T_{\text{knowable}} > T_c$.

This test runs on every git commit.

---

### 2.3 UTC-Only Time Discipline

Sports fixtures, API updates, and exchange orders originate across multiple timezones. Standardizing on UTC is a hard boundary rule:
- All input strings are parsed and forced to UTC timezone-aware datetimes using `wc2026.time_utils.ensure_utc()`.
- Naive datetime objects (which lack timezone offset data) are rejected at the package boundary with a `ValueError`.
- Time-differences are calculated using explicit timezone-aware offsets to prevent daylight savings shifts from leaking or shifting the order sequence.

---

### 2.4 Configuration Fences

The configuration file [`configs/default.yaml`](file:///Users/shreejitverma/github/footbal_prediction/configs/default.yaml) and parser [`src/wc2026/config.py`](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/config.py) enforce safety boundaries via Pydantic:
- **Default Mode**: `mode` defaults to `paper`. Live execution is structurally blocked unless explicitly overridden in target configs.
- **Autonomous News Fences**: `NewsConfig.autonomous_trading` is typed as `Literal[False]`. The system will raise a validation error at startup if configured to trade news automatically, ensuring a human review step is always in the loop.
