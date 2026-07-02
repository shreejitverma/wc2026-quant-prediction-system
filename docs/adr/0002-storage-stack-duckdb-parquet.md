# ADR-0002: Storage stack — DuckDB + Parquet + JSONL, no server

- Status: accepted
- Date: 2026-07-01

## Context

We need a raw store, a processed analytical store, an audit ledger, and a query engine.
The operator can build Kafka/Spark/Postgres/K8s in his sleep, which is exactly why the default must resist it.
Data volumes here are small: ~104 matches in the live tournament, tens of thousands of historical internationals, order-book snapshots at fixed cadence.
This is gigabytes, not terabytes, and single-node.

## Decision

We will use:
- **Immutable raw layer**: JSON/CSV exactly as received, dated, never edited.
- **Processed layer**: Parquet, partitioned by `source/date`, columnar and compressed.
- **Audit ledger**: JSONL append-only (see ADR-0004 for why not Parquet here).
- **Query engine**: DuckDB — reads Parquet and JSONL directly, zero server, SQL, fast on single-node analytics.
- **Scheduling**: cron.

## Alternatives rejected

- **SQLite** — fine for transactional rows, but weak for columnar analytical scans over Parquet and awkward for the "point a query at a directory of files" pattern; DuckDB is strictly better for this workload.
- **Postgres/PostGIS** — a server to run, back up, and version-migrate; buys concurrency and geospatial we do not yet need. Clean upgrade point if multi-writer concurrency ever appears (it should not for a solo operator).
- **Kafka/Spark/streaming stack** — massive operational surface for data that fits in memory; event-driven needs (lineups/news) are handled by an event-triggered cron fast-path, not a streaming platform. Requires its own ADR with a measured bottleneck before adoption.

## Consequences

The whole data plane is files on disk plus a library import — reproducible, inspectable, trivially backed up.
No service to keep alive, no cluster to babysit.
Failure mode avoided: infrastructure that consumes the research time that should go into model quality.
Upgrade points are explicit (Postgres for concurrency, a streaming layer only if a measured latency bottleneck justifies it).
