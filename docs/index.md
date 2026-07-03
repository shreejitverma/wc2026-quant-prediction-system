# WC2026 Prediction System Documentation

Welcome to the technical documentation site for the **WC2026 Quantitative Prediction and Execution System**. 

This system is an end-to-end, single-node quantitative market-making and arbitrage platform designed to price and trade derivative contracts for the FIFA World Cup 2026 on prediction markets (Kalshi and Polymarket).

---

## Guide for the Three Target Audiences

To help you find what you need in under 30 seconds:

### 1. 🚨 Operating During a Matchday Incident
If you are currently experiencing a live incident on matchday (e.g., feed disconnect, exchange API error, reconciliation breach, or a sudden goal requiring quote suspension):
- Go directly to the **[Operational Runbooks](runbook.md)**.
- Locate the **[Disaster Recovery Matrix](runbook.md#5-disaster-recovery-matrix)**.
- To execute the emergency quote cancel commands, read the **[Emergency Kill Switches Guide](runbook.md#6-emergency-kill-switches)**.

### 2. 🧠 Me in Six Months (Maintenance & Retraining)
If you are returning to the codebase to add a new model, integrate a new data source, re-run backtests, or recalibrate the ensembler weights:
- Start with the **[System Architecture Deep-Dive](architecture.md)** to rebuild your mental model.
- Review the **[Mathematical Modeling Suite Deep-Dive](models.md)** to verify likelihood and decay equations.
- Check the **[System Discrepancies Log](discrepancies.md)** to see where code and design currently diverge.
- Read the task-oriented **[How-To Guides](file:///Users/shreejitverma/github/footbal_prediction/MASTER_PLAN.md#phase-status-summary)** for step-by-step instructions.

### 3. 💼 Collaborators & Technical Reviewers
If you are auditing the design, code cleanliness, or statistical integrity of this system:
- Read the **[Core Design Creed & Edge Thesis](adr/0006-edge-thesis-coherence-settlement-timing.md)** to understand our trading philosophy.
- Inspect the **[Honesty Harness Principles](architecture.md#the-honesty-harness)** to see how we mechanically prevent backtest cheating and feature leakage.
- Review the **[Model Cards Catalog](model_cards/README.md)** for a summary of each of the 6 predictive models (M1–M6).
- Audit the **[API Surface Specification](api-surface.md)** and **[Data Contracts](data_contracts/README.md)**.

---

## diátaxis Documentation Structure

Our documentation is structured strictly according to the **Diátaxis framework**:

- **Tutorials (Learning-Oriented)**: Basic guides to get the system compiled and running from absolute scratch.
- **How-To Guides (Task-Oriented)**: Recipes to achieve operational goals (e.g. running backtests, committing pre-registrations).
- **Reference (Information-Oriented)**: Exhaustive details on API surfaces, configuration schemas, CLI commands, and database structures.
- **Explanation (Understanding-Oriented)**: Deep-dives into quant theory, statistical derivations, bracket simulation topology, and architectural decisions.
