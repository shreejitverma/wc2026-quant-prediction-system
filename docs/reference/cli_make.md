# CLI Command & Makefile Reference

This document provides a quick reference for the command-line orchestrator and all automation targets defined in the project `Makefile`.

---

## 1. CLI Command Orchestrator (`cron.py`)

The primary entry point for executing batch cron cycles and backtests is [`src/wc2026/ops/cron.py`](file:///Users/shreejitverma/github/footbal_prediction/src/wc2026/ops/cron.py). 

> **Important Operational Note**: As detailed in the **[Discrepancies Log](../discrepancies.md)**, these Click commands are currently mock wrappers that print simulated logs. The underlying functional pipelines must be run via their individual module entry points or tests.

### 1.1 `uv run python -m wc2026.ops.cron backtest`
- **Purpose**: Runs a rolling walk-forward backtest over historical results.
- **Side Effects**: Reads historical match parameters from `features.db`, generates out-of-sample prediction rows, and logs performance metrics.
- **Ledger footprint**: None (writes to local terminal console only).

### 1.2 `uv run python -m wc2026.ops.cron live`
- **Purpose**: Computes predictions for current tournament fixtures.
- **Side Effects**: Fetches current ratings, simulates tournament brackets, and computes fair values.
- **Ledger footprint**: Appends a `prediction` event row containing fair values to the ledger.

### 1.3 `uv run python -m wc2026.ops.cron coherence`
- **Purpose**: Scans exchange L2 books for cross-venue or internal coherence pricing discrepancies.
- **Side Effects**: Queries Kalshi and Polymarket orderbook snapshots, computes EV margins, and prints arbitrage candidates.
- **Ledger footprint**: Appends a `coherence_scan` row to the ledger if any discrepancy is found.

---

## 2. Makefile Target Catalog

All automation tasks are defined in the [`Makefile`](file:///Users/shreejitverma/github/footbal_prediction/Makefile).

| Target | Command Executed | Description | Side Effects |
| :--- | :--- | :--- | :--- |
| **`make setup`** | `uv sync --extra dev` | Rebuilds the virtual environment from the lockfile. | Installs/updates dependencies under `.venv/`. |
| **`make lock`** | `uv lock` | Generates a clean `uv.lock` file from `pyproject.toml`. | Writes `uv.lock`. |
| **`make test`** | `uv run pytest` | Runs the test suite (168 tests). | Generates `.coverage` and test caches. |
| **`make test-cov`**| `uv run pytest --cov=src --cov-fail-under=93` | Runs test coverage, requiring $\ge 93\%$ coverage. | Fails build if coverage falls below threshold. |
| **`make lint`** | `uv run ruff check src tests scripts` | Runs Ruff linter on all python directories. | Fails if style or syntax violations are found. |
| **`make fmt`** | `uv run ruff format src tests scripts` | Auto-formats source code files. | Overwrites Python files with clean formatting. |
| **`make verify`** | `lint test selfcheck` | Combined validation gate. Must pass before git commits. | Runs full testing and self-check scripts. |
| **`make selfcheck`**| Runs `phase0_selfcheck.py` and `phase2_selfcheck.py`. | Runs end-to-end integration smoke tests. | Populates temporary memory databases. |
| **`make api`** | `uv run uvicorn wc2026.api.server:app --reload` | Launches the FastAPI server on port 8000. | Spawns a persistent uvicorn server process. |
| **`make openapi`** | Exports OpenAPI schemas. | Exports FastAPI spec to `frontend/openapi.json`. | Overwrites the frontend schema file. |
| **`make docs`** | `uv run mkdocs build` | Compiles the documentation to static HTML. | Writes output to `/site/`. |
| **`make docs-serve`**| `uv run mkdocs serve -a 127.0.0.1:8001` | Runs a local documentation server on port 8001. | Spawns a web dev server process. |
| **`make docs-verify`**| Compiles docs strictly and checks links. | Strict build check + runs link-checking validation. | Fails if any broken links or markdown typos exist. |
