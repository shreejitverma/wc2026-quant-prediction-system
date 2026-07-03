# Architecture Decision Records (ADR) Index

This directory contains the history of architectural decisions made during the design and build phases of the WC2026 Prediction System.

---

## Decision Log Summary

| ADR ID | Decision Title | Status | Consequence |
|---|---|---|---|
| **[ADR-0001](0001-record-architecture-decisions.md)** | Record Architecture Decisions | Accepted | We use the standard ADR layout to log major design and system decisions chronologically. |
| **[ADR-0002](0002-storage-stack-duckdb-parquet.md)** | Storage Stack — DuckDB + Parquet | Accepted | Data plane consists of files on disk (Parquet/JSONL) queried by an embedded DuckDB engine. No SQL server to manage. |
| **[ADR-0003](0003-experiment-tracking-local-runs-ledger.md)** | Local Runs Ledger | Accepted | Runs are logged locally to JSONL, avoiding MLflow/server infrastructure dependencies. |
| **[ADR-0004](0004-append-only-ledger-hash-chain.md)** | Append-Only Ledger Hash-Chain | Accepted | Ledger entries form a SHA-256 cryptographic chain, preventing post-hoc manual tampering of trade results. |
| **[ADR-0005](0005-point-in-time-gate.md)** | Single Point-in-Time Gate | Accepted | All feature reads filter on `knowable_at <= ts`, verified by Hypothesis property-based tests in git pre-commit. |
| **[ADR-0006](0006-edge-thesis-coherence-settlement-timing.md)** | Edge Thesis | Accepted | Primary edge is cross-market coherence pricing and timing, not out-predicting sharp 1X2 closing lines. |
| **[ADR-0007](0007-free-first-data-access.md)** | Free-First Data Access | Accepted | System boots on free scrapers and Kaggle datasets, with clean interface-based paid API upgrade slots. |
| **[ADR-0008](0008-scope-and-killswitch.md)** | Scope & Killswitch | Accepted | Operational mode defaults to `paper`. Live trading requires promoting through pre-registered gates; kill switch is v1. |
| **[ADR-0009](0009-llm-news-router-not-signal.md)** | LLM News Router | Accepted | LLM extracts structured facts from news feeds to route to a human review queue; never executes trades autonomously. |
| **[ADR-0010](0010-fetch-parse-separation.md)** | Fetch/Parse Separation | Accepted | Ingestion separates I/O fetch from pure parse logic, allowing CI tests to run network-free using fixtures. |
| **[ADR-0011](0011-terminal-ui-stack.md)** | Terminal UI Stack | Accepted | Defines the initial terminal-based visualization stack (superseded by Vite React SPA). |
| **[ADR-0012](0012-api-provenance-envelope.md)** | API Provenance Envelope | Accepted | Every API response payload is wrapped in metadata identifying git commit, config hash, and real vs mock status. |
| **[ADR-0013](0013-terminal-design-system.md)** | Terminal Design System | Accepted | Establishes formatting constraints and screen layouts for terminal operators. |
| **[ADR-0014](0014-multiplexed-websocket.md)** | Multiplexed WebSocket | Accepted | Native Python WebSocket server broadcasts incremental L2 orderbook updates to the client in real-time. |
| **[ADR-0015](0015-vite-spa-toolchain.md)** | Vite SPA Toolchain | Accepted | Transition frontend from Next.js SSR to a Vite-managed React Single Page Application for faster local render cycles. |
| **[ADR-0016](0016-visualization-stack-split.md)** | Visualization Stack Split | Accepted | Decouples chart rendering and plotting code from the core backend library to prevent dependency bloating. |
