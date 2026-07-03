# wc2026 - FIFA World Cup 2026 Quant System

A production-grade, end-to-end quantitative prediction, fair-value pricing, and market-making system for the FIFA World Cup 2026.

This system is designed for **operator-driven, quantitative execution** on prediction markets (Kalshi, Polymarket). It evaluates the entire joint distribution of the tournament (every match, every group standing, every knockout progression) and translates probabilistic edges into direct market quotes.

> **Our Edge:** Edge in this system is defined by model quality, information *timing* (e.g. lineup drops 60 mins pre-kickoff), settlement-rule precision (how FIFA tiebreakers resolve), and cross-market joint coherence. Edge is **not** high-frequency speed. See `docs/adr/0006`.

### Why Coherence Pricing beats Speed
Most prediction markets fail at pricing conditional events correctly. For example, if France scores an early goal against Brazil in Group G, human traders will immediately drop Brazil's odds of winning that specific match. 

However, they often forget to simultaneously short Brazil's odds of "Winning the World Cup" or adjusting Argentina's odds of facing Brazil in the Quarterfinals. 
Our **Coherence Pricing** edge relies on solving the *entire* tournament mathematically every time a single event changes, allowing us to find arbitrage in these secondary and tertiary derivative markets while retail traders focus on the primary event.

---

## 🚀 Quick Start

Ensure you have Python 3.12 and [uv](https://github.com/astral-sh/uv) installed.

```bash
# 1. Setup the environment (pins Python 3.12, installs deps from uv.lock)
make setup

# 2. Install pre-commit hooks (Point-in-Time leakage gates, linting)
make hooks

# 3. Verify the system (runs pytest, coverage checks, self-check harness)
make verify

# 4. Run the Full Stack (Starts FastAPI Backend & Next.js Operator Console)
./run.sh
```
*The Next.js Operator Console will be available at `http://localhost:3000`*

### CLI Orchestrator Operations
For headless operations (e.g., cron jobs, CI pipelines), the backend can be invoked directly:
```bash
uv run python -m wc2026.ops.cron backtest    # Run historical evaluation
uv run python -m wc2026.ops.cron live        # Execute live trading logic
uv run python -m wc2026.ops.cron coherence   # Verify cross-market pricing coherence
```

---

## 🏗️ System Architecture & Data Provenance

The project consists of an **Execution Loop** bolted to an **Honesty Harness**. 

```mermaid
graph TD
    subgraph Honesty Harness
        L[Ledger: Append-only hash chain]
        P[Pre-registration Gates]
        PIT[Point-In-Time Gate]
    end

    subgraph Data Ingestion
        A[Orderbooks: Kalshi/Polymarket] -->|Raw Store| C[Clean & Normalize]
        B[Stats: FBref/Elo/Venue] -->|Raw Store| C
    end

    subgraph Modeling & Execution Loop
        C -->|PIT Gate| D[(DuckDB Feature Store)]
        D --> E{Meta-Model Ensembler}
        E --> F[M1-M4 Sub-Models]
        F --> G[Tournament Simulator 100k Paths]
        G --> H[Fair Value Pricer]
        H --> I[Market Maker Quoting Engine]
        I --> J[Execution Layer]
    end
    
    J -.->|Records Trades & Quotes| L
```

### Data Provenance Flowchart
Before a model can generate a prediction, data must pass through the rigid provenance and Point-In-Time (PIT) pipeline to guarantee we never leak future data into a past backtest:

```mermaid
sequenceDiagram
    participant API as External Data (FBref)
    participant Raw as Raw File Store
    participant Clean as Normalization Layer
    participant PIT as Point-in-Time Gate
    participant FS as DuckDB Feature Store

    API->>Raw: Fetch JSON/HTML (Timestamped)
    Raw->>Raw: Hash payload (SHA-256)
    Raw->>Clean: Load raw strings
    Clean->>Clean: Normalize to Pandas DataFrame
    Clean->>PIT: Request Feature at Time T
    PIT->>PIT: Filter out ALL rows > Time T
    PIT->>FS: Write clean, leak-free Parquet
    FS-->>Models: Safe Feature Vectors
```

### Components Breakdown:
1. **Data Ingestion**: Scrapes and normalizes raw JSON/HTML from prediction markets (Kalshi, Polymarket) and statistical sources (FBref, Elo Ratings).
2. **Feature Store (DuckDB)**: A columnar, analytically optimized store for fast feature retrieval. 
3. **The Point-in-Time (PIT) Gate**: Structurally forbids the models from seeing data from the future during backtesting.
4. **Meta-Model Ensembler**: Combines state-space tracking, Poisson models (Dixon-Coles), Bayesian hierarchical, and player-level aggregates to output a canonical `ScoreDist` (a matrix of exact scoreline probabilities).
5. **Tournament Simulator**: Uses the match-level `ScoreDist` to run a 100,000-path Monte Carlo simulation mapping the complex tournament topology (group stage tiebreakers, 3rd place progression rules).
6. **Pricing & Execution**: Derives the exact probability of *any* market proposition, compares it to the live orderbook to find Edge, and manages the execution via Paper/Live interfaces.
7. **The Honesty Harness**: An append-only cryptographic ledger (`wc2026.ledger`) ensuring quotes, prices, and performance metrics are tamper-evident.

---

## 📚 Documentation Directory

For deep dives into specific engineering and quantitative aspects of the system, refer to the following documents:

- **[docs/architecture.md](docs/architecture.md)** — Deep dive into the data flows, Monte Carlo simulator, and Execution logic.
- **[docs/models.md](docs/models.md)** — A rigorous mathematical and statistical breakdown of the predictive modeling suite (Dixon-Coles, Bayesian Hierarchical, State-Space, Ensembling).
- **[docs/runbook.md](docs/runbook.md)** — The definitive operational manual. Covers deployment, troubleshooting, kill-switches, and CI/CD pipelines.
- **[frontend/README.md](frontend/README.md)** — Architecture and setup instructions specifically for the Next.js/Zustand/React-Query Operator Console.
- **[docs/adr/](docs/adr/)** — Architecture Decision Records explaining *why* we chose specific stacks (DuckDB over Postgres, Python over C++ for now).

---

## 🛡️ The Phase 0 Honesty Harness

The core philosophy of this repo is rigorous honesty with our results. Phase 0 implemented the following tools to enforce this:

| Module | Role |
|--------|------|
| `wc2026.time_utils` | UTC-only timestamp discipline (rejects naive datetimes). |
| `wc2026.hashing` | Git provenance + content hashing ensuring 100% reproducibility. |
| `wc2026.pit` | The single point-in-time access gate for all model features. |
| `wc2026.ledger` | Append-only, hash-chained, tamper-evident audit log of all trades. |
| `wc2026.config` | Strict Pydantic config ensuring Paper Mode execution is fenced off from Live credentials. |

---

## 📈 Status
**Phases 0–9 are fully built and verified.** 
- The system evaluates matches perfectly.
- The 100k-path simulator benchmarks at sub-millisecond execution times.
- The Next.js frontend is actively streaming live (simulated) WebSocket orderbook data.
- The system is live-capable, waiting behind the final pre-registration and live-execution gates.
