# Data Dictionary & Schema Specification

This document provides the structural specification for all raw and processed storage files, database tables, and the canonical ID crosswalk mappings within the WC2026 system.

---

## 1. Storage Layout & Cadences

The file storage system is partitioned locally on disk under `data/` ([ADR-0002](file:///Users/shreejitverma/github/footbal_prediction/docs/adr/0002-storage-stack-duckdb-parquet.md)):

```
data/
├── raw/                      # Immutable, dated raw payloads (JSON/CSV)
│   ├── results/              # Daily cron downloads of international results
│   ├── elo/                  # Nightly scrapes of eloratings.net
│   └── markets/              # Persistent WS logs of Kalshi & Polymarket orderbooks
└── processed/
    ├── features.db           # Embedded DuckDB database
    └── features/             # Columnar Parquet exports partitioned by date
```

---

## 2. DuckDB Database Schema

The database `data/processed/features.db` holds three tables. All timestamps are stored as **UTC ISO 8601 strings**.

### 2.1 The `results` Table
Stores chronological historical match results.

| Column | Type | Description | PIT Semantics |
| :--- | :--- | :--- | :--- |
| `match_id` | `VARCHAR` | Primary Key. Format: `{home_team}_vs_{away_team}_{date}` | Immutable |
| `date` | `TIMESTAMP` | Kickoff timestamp in UTC | Immutable |
| `home_team` | `VARCHAR` | Canonical name of the home team | Immutable |
| `away_team` | `VARCHAR` | Canonical name of the away team | Immutable |
| `home_score` | `INTEGER` | Actual goals scored by the home team | Knowable at Full-Time |
| `away_score` | `INTEGER` | Actual goals scored by the away team | Knowable at Full-Time |
| `neutral` | `BOOLEAN` | True if the match was played on neutral territory | Knowable pre-kickoff |
| `knowable_at` | `TIMESTAMP` | UTC timestamp when results became public | Standard PIT filter |

---

### 2.2 The `elo_timeline` Table
Stores sequential Elo rating updates calculated walk-forward by `EloTimeline`.

| Column | Type | Description | PIT Semantics |
| :--- | :--- | :--- | :--- |
| `team` | `VARCHAR` | Canonical name of the team | Indexed key |
| `date` | `TIMESTAMP` | UTC timestamp of match day | Update key |
| `elo` | `DOUBLE` | Reconstructed rating at end of match day | Recomputed walk-forward |
| `is_reliable` | `BOOLEAN` | True if the team has played $\ge 30$ historical matches | Quality gate filter |
| `knowable_at` | `TIMESTAMP` | UTC timestamp of match day full-time | PIT gate check |

---

### 2.3 The `features` Table
Stores final feature vectors read by prediction models. It features explicit **temporal versioning** columns to support retroactive corrections.

| Column | Type | Description | PIT Filter Rule |
| :--- | :--- | :--- | :--- |
| `match_id` | `VARCHAR` | Key matching the `results` table | Standard join |
| `feature_name` | `VARCHAR` | Name of the feature (e.g. `elo_diff`, `altitude_m`) | Feature lookup |
| `value` | `DOUBLE` | Numerical value of the feature | Model input |
| `knowable_at` | `TIMESTAMP` | The exact time this value became knowable | Checked by `as_of` |
| `superseded_at` | `TIMESTAMP` | UTC time when a correction row superseded this | Hidden if `as_of < superseded_at` |

---

## 3. The Canonical ID Team Crosswalk

To resolve differences in team names across raw files (e.g., `West Germany` vs `Germany`, or `US` vs `USA`), we maintain a mapping dictionary inside [`configs/crosswalk_teams.yaml`](file:///Users/shreejitverma/github/footbal_prediction/configs/crosswalk_teams.yaml):

```yaml
# configs/crosswalk_teams.yaml
canonical_mappings:
  "United States": "USA"
  "US": "USA"
  "USA": "USA"
  "Mexico": "MEX"
  "Deutschland": "GER"
  "Germany": "GER"
  "West Germany": "GER"
```

The `wc2026.ingest.crosswalk.TeamCrosswalk` class handles resolution:
- All scraped or fetched names are passed to `resolve_team(raw_name)`.
- If a name is not matched, it defaults to a fuzzy string-match algorithm using `difflib`. If similarity is $< 0.85$, it logs a validation quarantine warning.
- Duplicate entries are blocked at parsing time via unit tests (`tests/ingest/test_crosswalk.py`).
