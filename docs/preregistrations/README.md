# Pre-registrations

Before any backtest or live-promotion gate, we write down:
1. **The hypothesis** — exactly what we're trying to prove.
2. **The metric** — how we measure success (e.g., Brier Score, CLV, Log-Loss improvement).
3. **The threshold** — what value constitutes "pass" vs "fail".
4. **The required sample size** — how many matches/contracts are needed to detect a real effect with statistical confidence.

Then we *run the evaluation without changing any of the above*. No moving goalposts after seeing results.

> **Why is this load-bearing?** With only ~104 matches in a single World Cup, a single tournament cannot statistically separate skill from luck (see the Phase 7 power analysis). Cross-tournament historical data carries the statistical weight; the live tournament is *confirmation*, not *proof*. Pre-registration is what stops us from retrofitting a threshold to whatever the result happened to be.

---

## What is Pre-Registration and Why Should I Care?

**The problem without pre-registration**: A researcher runs a backtest. The first threshold they test is "beat the market by 2%". The result comes back: 1.7%. They think "close enough, let me try 1.5%". That also seems arbitrary, so they try "beat the market by 1%". The result is 1.2% — they declare success. But they've been p-hacking: by testing multiple thresholds and reporting only the one that worked, they've inflated the apparent significance of a result that may be pure noise.

**The solution**: Before running any evaluation, commit the following to git (the timestamp is the proof it came first):
- The exact metric formula.
- The exact threshold.
- The exact data window.
- The minimum required sample size from a pre-computed power analysis.

If the result doesn't meet the threshold, the gate fails — even if it's "very close."

---

## Pre-Registration Index

| ID | Experiment / Gate | Metric | Threshold | Sample Size | Status | Committed (pre-run) |
|----|-------------------|--------|-----------|------------|--------|---------------------|
| PR-0001 | M1 vs M6 walk-forward on 2010–2022 WCs + qualifiers | Brier Score improvement | ΔBrier > 0.005 | n ≥ 800 matches | 🔄 Draft | — |
| PR-LIVE-0001 | Paper → Live promotion gate | CLV (Closing Line Value) | CLV > 0.0 over 200+ bets | n ≥ 200 bets | 🔄 Draft | — |

---

## Template

Use [`_template.md`](_template.md) for each new experiment or gate. The template enforces the required fields.

---

## How to Add a New Pre-Registration

1. Copy `_template.md` to a new file (e.g., `PR-0002-ensemble-weight-stability.md`).
2. Fill in all required fields. Leave none blank.
3. **Commit and push to git *before* running any evaluation code.**
4. After the evaluation runs, update only the `Status` and `Result` fields.
5. Add the experiment to the index table in this file.
