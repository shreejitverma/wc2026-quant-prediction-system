# Operational Runbook

This document is the definitive operational manual for deploying, monitoring, and debugging the WC2026 Prediction System in both Paper Trading and Live environments.

---

## 1. Local Deployment & Setup

The system enforces strict Python dependencies for reproducibility. We use `uv` and lock our dependencies explicitly.

```bash
# Clone the repository
git clone https://github.com/shreejitverma/wc2026-quant-prediction-system.git
cd wc2026-quant-prediction-system

# Install uv if missing
curl -LsSf https://astral.sh/uv/install.sh | sh

# Resolve dependencies and setup virtual environment
make setup

# Install the Point-in-Time git hooks (CRITICAL)
make hooks

# Run the end-to-end self-check (Verify the harness is intact)
make verify
```

### Launching the Dashboard Stack
To start the Next.js React frontend and the FastAPI backend concurrently:
```bash
./run.sh
```
- **Operator Console**: `http://localhost:3000`
- **FastAPI Backend Swagger**: `http://localhost:8000/docs`

---

## 2. CLI Orchestrator Modes

The underlying quantitative engine is executed via `wc2026.ops.cron`.

### Backtesting Mode
```bash
uv run python -m wc2026.ops.cron backtest
```
Runs the full Meta-Model ensembler across historical fixtures, pushing outputs through the PIT (Point-in-Time) gate.

### Live Mode
```bash
uv run python -m wc2026.ops.cron live
```
The active execution mode. Parses real-time data, recalibrates probabilities, and triggers the `Quoting Engine` to execute trades on Kalshi/Polymarket based on calculated edge.

### Coherence Mode
```bash
uv run python -m wc2026.ops.cron coherence
```
Scans the live orderbooks across venues strictly to find cross-market arbitrage opportunities or internal mispricings caused by edge-case settlement rules.

---

## 3. Continuous Integration & CD

We enforce a strict CI pipeline to protect the mathematical integrity of the models.
The `.github/workflows/ci.yml` enforces the following gates on every pull request:
1. **Linting**: Ruff formatting and type checking.
2. **Unit Tests**: Full `pytest` suite execution.
3. **Coverage Constraint**: Code coverage must be **>= 93%**. Dropping below this fails the build, preventing untested edge cases from reaching production.
4. **Performance Benchmarks**: `pytest-benchmark` runs on the `MetaModel.fit()` hot-paths and the Monte Carlo Tournament Simulator. Any code change that significantly slows execution speed fails the pipeline.

---

## 4. Troubleshooting & Debugging

### The Hash Ledger (`wc2026.ledger`)
If a trade executes that looks suspicious or unprofitable, you must consult the ledger.
The ledger is stored at `data/ledger/ledger.jsonl`.
Because it is append-only and cryptographically hash-chained, you can trace exactly what the models believed the probabilities were at the millisecond the trade was placed.
```python
from wc2026.ledger import verify_chain
# If this returns False, someone manually altered a past trade record to hide a mistake.
assert verify_chain() == True 
```

### State Management Debugging
The Operator Console uses `Zustand` for state tracking of the Paper Trading Blotter. If the UI state falls out of sync, check the `tradingStore.ts` implementation or monitor the WebSocket feed coming from `/api/ws/orderbook/`.

---

## 5. Emergency Kill Switches

Our architectural edge is model quality, not HFT speed. However, speed is used defensively.
If a live game experiences a sudden, unpredicted event (a red card, an instant goal) before the external data APIs (FBref) can update our models, we risk leaving stale quotes on the exchange that sharps will pick off.

**Kill Switch Execution:**
The orchestrator monitors real-time rapid odds shifts across sharp offshore books. If a shift exceeds a predefined $\Delta$, the `Quoting Engine` immediately executes a pull-all-quotes command to Polymarket/Kalshi. 

In manual emergencies, the kill switch can be tripped manually via the Next.js Operator Console (in the upper right Command Palette).
