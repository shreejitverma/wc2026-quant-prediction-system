# How-To: Run Backtests & Evaluate Models

This guide details the procedures for executing backtests, setting up pre-registrations, triaging model races, and promoting model configurations.

---

## 1. Freeze a Pre-registration

Before running any backtest evaluation, you must **pre-register** the experiment parameters to prevent hindsight bias and selective metric cherry-picking.

1. Create a new markdown file under `docs/preregistrations/` (e.g. `docs/preregistrations/PR-2026-M5-LIGHTGBM.md`):
   - Record the hypothesis (e.g. "Adding altitude parameters to M5 reduces out-of-sample Log-Loss on matchdays").
   - Freeze the metric targets (e.g. Brier Score ECE $< 0.05$).
   - Set the validation window size (e.g. 15% out-of-sample split).
2. Commit the file to git *prior* to executing the model evaluation:
   ```bash
   git add docs/preregistrations/PR-2026-M5-LIGHTGBM.md
   git commit -m "prereg: freeze M5 altitude experiment parameters"
   ```

---

## 2. Execute the Walk-Forward Backtester

The walk-forward backtester evaluates model performance on rolling chronological windows without future feature leakage.

Run the backtester suite:
```bash
uv run pytest tests/eval/test_backtest.py
```

The underlying code class `WalkForwardBacktester` performs the following steps:
1. Sorts all historical records chronologically.
2. Loops month-by-month over the evaluation window.
3. Fits the target models on data strictly before the start of each month.
4. Generates predictions and computes proper scores (Log Loss, Brier Score) for matches within the month.
5. Returns averaged out-of-sample metrics.

---

## 3. Analyze Model Calibration & Edge

Review the calibration reports from `/api/v1/eval/calibration` or run a local diagnostic script:
- **ECE (Expected Calibration Error)**: Verify confidence matches frequency. If confidence is higher than actual win rates, the model is overconfident.
- **CLV (Closing Line Value)**: Check realized CLV. A positive mean CLV over $\ge 200$ matches is the primary indicator of alpha.
- **Log-Loss Race**: Review the head-to-head model race to verify if the challenger out-performs the champion.

---

## 4. Promote a Model to the Ensemble

Once a model meets the pre-registered promotion gates:
1. Update weights inside `configs/default.yaml` ([ADR-0008](file:///Users/shreejitverma/github/footbal_prediction/docs/adr/0008-scope-and-killswitch.md)).
2. Commit the updated configuration to git to preserve provenance:
   ```bash
   git add configs/default.yaml
   git commit -m "promote: set M5 (LightGBM) active ensemble weight to 0.20"
   git push origin main
   ```
3. The API server detects configuration updates automatically, reloading the active weights on the fly.
