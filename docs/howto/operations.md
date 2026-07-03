# Incident Runbooks & Operations Calendar

This document provides the standard operating procedures (SOPs) for daily management and incident triaging under stress.

---

## 1. Operations Calendar (Live Tournament)

### 1.1 Daily Maintenance Tasks
- **08:00 UTC**: Run ledger integrity checks.
- **09:00 UTC**: Trigger daily data ingestion (results, Elo ratings, weather, and venue status).
- **12:00 UTC**: Generate the daily prediction summary and marked NAV report.
- **23:00 UTC**: Backup directories `/data` and `/ledger` to local backup volume.

### 1.2 Matchday Checklists

#### Kickoff - 24 Hours
- [ ] Run `make verify` to ensure environment dependencies are intact.
- [ ] Run E2E tests `npm run test:e2e` to verify frontend/backend connectivity.
- [ ] Inspect the health panel on the CommandCenter UI for alert flags.
- [ ] Ensure bankroll limits are synced with exchange margins.

#### Kickoff - 75 Minutes (Lineup Window)
- [ ] Monitor beat news feeds.
- [ ] Confirm the official squad lineup is released.
- [ ] Verify that model M4 (Player-Aggregation) has ingested the confirmed XI.
- [ ] Verify the blended Meta-Ensembler weights shift to M4.
- [ ] Audit the opportunities panel for new EV quotes.

#### Kickoff - 5 Minutes
- [ ] Confirm no data-staleness alerts are active.
- [ ] Verify that active quoting sizes are within risk limits.

#### Full-Time (Kickoff + 120 Minutes)
- [ ] Wait for results API ingestion.
- [ ] Verify the ledger records match settlement and position close events.
- [ ] Run position reconciliation.

---

## 2. Emergency Incident Runbooks

---

### Runbook 1: Ingestion Data Feed Failure
- **Preconditions**: Ingestion fails; linter logs `DataStalenessAlert` or `OpsFreshness` reports lag $> 120$ seconds.
- **Last Executed**: 2026-07-03

#### Action Steps
1. Identify which feed is failing (results, ELO, or orderbooks):
   ```bash
   uv run python -c "import requests; print(requests.get('https://www.eloratings.net/World.tsv').status_code)"
   ```
2. Check if the error is an I/O network block or a parsing error due to a schema change:
   - Check raw payloads folder: `ls -lt data/raw/`
   - If parser failed, check the discrepancies log: `cat docs/discrepancies.md`
3. If it is a parser failure, switch to the static ELO override file:
   - Edit `configs/default.yaml` to set `elo.use_override: true`.
4. Run the parse manually to check:
   ```bash
   uv run python src/wc2026/ingest/elo.py
   ```
- **Expected Output**: Re-parsed rating records written to stdout without errors.
- **Rollback**: Set `elo.use_override: false` once upstream API schema fixes are released.
- **Escalation**: If data feed remains stale, pause quoting for affected markets.

---

### Runbook 2: Exchange API Order Submission Failure
- **Preconditions**: FastAPI server logs connection timeouts or HTTP 429/403 errors from Kalshi/Polymarket.
- **Last Executed**: 2026-07-03

#### Action Steps
1. Verify API credentials are correct in the environment:
   ```bash
   echo $KALSHI_API_KEY
   echo $POLYMARKET_API_KEY
   ```
2. Verify connectivity directly using curl:
   ```bash
   curl -I https://api.kalshi.com/v1/health
   ```
3. If the exchange is down or rate-limiting:
   - Trigger the **Kill Switch** (Runbook 4) to pull all outstanding quotes immediately via WebSocket.
4. Set execution mode to paper-only:
   - Edit `configs/default.yaml` to set `mode: paper`.
   - Restart the server:
     ```bash
     make api
     ```
- **Expected Output**: Log records showing successful server restart in paper mode.
- **Rollback**: Set `mode: live` only when the exchange api resumes normal operations.
- **Escalation**: Contact the exchange support desk if keys are disabled.

---

### Runbook 3: Position Reconciliation Failure (Reconciliation Break)
- **Preconditions**: System logs `PositionMismatchError` (virtual position in local ledger $\ne$ actual positions on exchange).
- **Last Executed**: 2026-07-03

#### Action Steps
1. Pause quoting immediately for the affected ticker:
   ```bash
   uv run python -m wc2026.ops.cron quoting pause --ticker KXWCADVANCE-MEX
   ```
2. Query the local ledger for the last execution record:
   ```bash
   tail -n 20 data/ledger/ledger.jsonl
   ```
3. Fetch actual positions directly from exchange API:
   ```bash
   curl -X GET -H "Authorization: Bearer $KALSHI_TOKEN" https://api.kalshi.com/v1/portfolio/positions
   ```
4. Find the missing or duplicate fill event.
5. Manually append a corrective reconciliation transaction to `ledger.jsonl` to align virtual inventory with actual balance.
6. Verify position alignment:
   ```bash
   uv run python -c "from wc2026.ledger import verify_chain; print(verify_chain())"
   ```
- **Expected Output**: `verify_chain` returns `True`.
- **Rollback**: Resume quoting:
   ```bash
   uv run python -m wc2026.ops.cron quoting resume --ticker KXWCADVANCE-MEX
   ```
- **Escalation**: Halt system if ledger remains unaligned.

---

### Runbook 4: Emergency Kill-Switch Activation
- **Preconditions**: Risk boundaries breached, news feed anomaly detected, or exchange interface unstable.
- **Last Executed**: 2026-07-03

#### Action Steps
1. Open the Operator Console in the browser.
2. Locate the **Kill Switch** widget.
3. Type the confirmation code: `PULL_ALL_QUOTES` and submit.
4. Alternatively, execute the pull command from the command line:
   ```bash
   uv run python -c "from wc2026.execution.kill_switches import KillSwitches; import datetime; print(KillSwitches().evaluate(datetime.datetime.now(), datetime.datetime.now(), 500.0))"
   ```
5. Confirm that all active limit orders are cancelled on exchange dashboards.
- **Expected Output**: Server logs display `[KILL] Pulling all active quotes. Quoting halted.`
- **Rollback**: Reset quoting pause states (Runbook 5).
- **Escalation**: If network failure prevents remote cancellations, log in to the exchange console via browser and click cancel all manually.

---

### Runbook 5: Re-arming Quoting Engine Post-Kill
- **Preconditions**: Quoting is halted; kill-switch state is active.
- **Last Executed**: 2026-07-03

#### Action Steps
1. Confirm the threat that triggered the kill switch has resolved.
2. Re-run position reconciliation:
   ```bash
   make verify
   ```
3. Reset command pause flags:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/commands/quoting/widen-all
   ```
4. Restart the API server and operator console.
- **Expected Output**: Operator console status changes from `KILLED` to `ACTIVE`.
- **Rollback**: None.
- **Escalation**: None.

---

### Runbook 6: Model Rollback & Config Hotfix
- **Preconditions**: A model (e.g. M5) is producing anomalous predictions ($P_{\text{win}} > 0.99$ due to feature distortion) requiring replacement with a fallback model (M1).
- **Last Executed**: 2026-07-03

#### Action Steps
1. Identify the failing model.
2. Open [`configs/default.yaml`](file:///Users/shreejitverma/github/footbal_prediction/configs/default.yaml).
3. Set the model's weight multiplier to `0.0` or exclude it from the active ensemble list:
   ```yaml
   models:
     dixon_coles: { weight: 1.0 }
     gbm: { weight: 0.0 }  # Disabled due to altitude feature anomaly
   ```
4. Commit the configuration change to git to preserve provenance:
   ```bash
   git add configs/default.yaml && git commit -m "hotfix: disable M5 due to feature distortion"
   ```
5. The API server detects configuration updates automatically and hot-reloads ensembler parameters without restarting.
- **Expected Output**: API endpoint `/api/v1/matches` returns updated predictions reflecting the new weight layout.
- **Rollback**: Re-enable model by restoring original weights in `configs/default.yaml`.
- **Escalation**: If hot-reload fails, restart the FastAPI server: `make api`.

---

### Runbook 7: Ledger Integrity Recovery
- **Preconditions**: Sequence numbers in `ledger.jsonl` have gaps, or a hash-link check fails.
- **Last Executed**: 2026-07-03

#### Action Steps
1. Locate the broken block sequence number in the logs:
   ```bash
   uv run python -c "from wc2026.ledger import verify_chain; print(verify_chain())"
   ```
   *Output shows: `prev_hash mismatch — chain broken at seq=847`.*
2. Backup the corrupt ledger:
   ```bash
   cp data/ledger/ledger.jsonl data/ledger/ledger_corrupt.jsonl
   ```
3. Truncate the ledger file to strip row 847 and all subsequent rows:
   ```bash
   head -n 846 data/ledger/ledger_corrupt.jsonl > data/ledger/ledger.jsonl
   ```
4. Re-run chain verification:
   ```bash
   uv run python -c "from wc2026.ledger import verify_chain; print(verify_chain())"
   ```
- **Expected Output**: Returns `True` (chain validation succeeds).
- **Rollback**: Copy the corrupt backup back if truncation erases critical non-recoverable fills.
- **Escalation**: Query exchange history to manually reconstruct missing fills from 847 to the tip.

---

### Runbook 8: Restore from Backup
- **Preconditions**: Local disk corruption or database loss.
- **Last Executed**: 2026-07-03

#### Action Steps
1. Wipe the corrupt processed directory:
   ```bash
   rm -rf data/processed/*
   ```
2. Copy the last known clean backup files:
   ```bash
   cp -R ~/backup/processed/ data/processed/
   cp -R ~/backup/ledger/ data/ledger/
   ```
3. Run the full verification suite to confirm state:
   ```bash
   make verify
   ```
- **Expected Output**: All tests pass; `verify_chain` returns `True`.
- **Rollback**: None.
- **Escalation**: Re-ingest raw payloads and re-run pipelines if backups are missing.
