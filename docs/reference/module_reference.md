# Python API & Module Reference

This page provides the automated API reference for all public classes and functions within the `wc2026` package, compiled directly from codebase docstrings via `mkdocstrings`.

---

## 1. Core Integrity Components

::: wc2026.pit.PointInTimeStore
    options:
      show_root_heading: true

::: wc2026.ledger.AppendOnlyLedger
    options:
      show_root_heading: true

::: wc2026.hashing
    options:
      show_root_heading: true

::: wc2026.runs.RunRecord
    options:
      show_root_heading: true

---

## 2. Ingestion Layers

::: wc2026.ingest.results
    options:
      show_root_heading: true

::: wc2026.ingest.elo
    options:
      show_root_heading: true

::: wc2026.ingest.crosswalk.TeamCrosswalk
    options:
      show_root_heading: true

---

## 3. Modeling Suite

::: wc2026.models.base.Model
    options:
      show_root_heading: true

::: wc2026.models.base.ScoreDist
    options:
      show_root_heading: true

::: wc2026.models.dixon_coles.DixonColesModel
    options:
      show_root_heading: true

::: wc2026.models.state_space.DynamicStateSpaceModel
    options:
      show_root_heading: true

::: wc2026.models.hierarchical.BayesianHierarchicalModel
    options:
      show_root_heading: true

::: wc2026.models.gbm.GBMModel
    options:
      show_root_heading: true

::: wc2026.models.market_implied.MarketImpliedModel
    options:
      show_root_heading: true

::: wc2026.models.meta_ensemble.MetaModel
    options:
      show_root_heading: true

---

## 4. Simulator & Pricing

::: wc2026.simulator.engine
    options:
      show_root_heading: true

::: wc2026.pricing.fair_value
    options:
      show_root_heading: true

::: wc2026.pricing.coherence.CoherenceEngine
    options:
      show_root_heading: true

---

## 5. Quoting & Risk Control

::: wc2026.execution.quoting.QuotingEngine
    options:
      show_root_heading: true

::: wc2026.execution.portfolio.PortfolioOptimizer
    options:
      show_root_heading: true

::: wc2026.execution.kill_switches.KillSwitches
    options:
      show_root_heading: true
