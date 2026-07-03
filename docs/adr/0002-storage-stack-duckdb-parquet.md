# ADR-0002: Storage Stack — DuckDB + Parquet + JSONL, No Server

- **Status**: Accepted
- **Date**: 2026-07-01
- **Deciders**: Shreejit Verma

---

## Context

The system needs four distinct storage layers:
1. **Raw Store**: The original payloads from every external API call, exactly as received.
2. **Processed Store**: Clean, normalized features ready for model training.
3. **Audit Ledger**: An append-only, tamper-evident record of every prediction and trade.
4. **Query Engine**: Fast analytical queries over the processed data.

**The critical constraint**: A solo operator should not spend research time babysitting infrastructure. Every minute spent on database cluster management, backup procedures, or schema migrations is a minute not spent on model quality — which is where the actual edge comes from.

**Data volume sanity check**: This system processes:
- ~104 matches in a live tournament.
- ~10,000–50,000 historical international matches.
- Orderbook snapshots at configurable cadences (e.g., every 60 seconds per market).
- Total data volume: **single-digit gigabytes** — easily fits on a $10/month storage volume.

At this scale, a distributed database or streaming platform would be **operationally inappropriate** — like using a cargo ship to move a bicycle.

---

## Decision

We use the following four-layer stack:

| Layer | Technology | Format | Justification |
|-------|-----------|--------|--------------|
| **Raw Store** | Files on disk | JSON/CSV exactly as received | Immutable; SHA-256 hashed; replayable without re-fetching |
| **Processed Store** | Files on disk | Parquet, partitioned by `source/date` | Columnar compression; DuckDB-native; fast analytical reads |
| **Audit Ledger** | Files on disk | JSONL, append-only | Human-inspectable; cryptographically chainable (ADR-0004) |
| **Query Engine** | DuckDB (embedded) | SQL queries over Parquet/JSONL | Zero servers; 10-100× faster than SQLite on analytical queries |
| **Scheduling** | cron | — | Simple, reliable, no process manager required |

### Why DuckDB over PostgreSQL?

| Feature | DuckDB | PostgreSQL |
|---------|--------|-----------|
| Server required | ❌ No (embedded library) | ✅ Yes (persistent server process) |
| `pandas`/`polars` integration | Native (zero-copy) | Requires psycopg2 + serialization |
| Analytical query speed (columnar) | 10–100× faster on GROUP BY/window functions | Slower (row-oriented) |
| Backup procedure | `cp *.parquet ~/backup/` | pg_dump + restore |
| Schema migrations | No migrations needed (schema-on-read) | ALTER TABLE scripts |
| Setup time | `import duckdb` (10 seconds) | Docker, config, pg_hba.conf (30+ minutes) |

DuckDB's "query a directory of files" pattern is specifically what we need:
```python
import duckdb
# Query all results from Q1 2026 across all sources in one line
df = duckdb.query("SELECT * FROM 'data/processed/results/2026-Q1/*.parquet'").df()
```

### Why Parquet for the Processed Layer?

Parquet is the right format because:
- **Columnar storage**: Analytical queries read only the columns they need, not entire rows.
- **Compression**: ~5× smaller than CSV (run-length encoding, dictionary encoding, Snappy/Zstd).
- **Schema enforcement**: Each column has a typed schema — prevents silent type coercions.
- **Partitioned reads**: DuckDB can skip entire partition directories based on `WHERE` predicates.

### Why JSONL for the Ledger?

The ledger has fundamentally different requirements from the processed store:
- **Append-only writes**: Parquet files are immutable blobs; appending one row means rewriting the entire file. JSONL appends are O(1).
- **Human-inspectable**: During an audit or debugging session, `tail -f ledger.jsonl` shows real-time trade activity without any tooling.
- **Crash-safe**: Each line is a complete, self-contained JSON object. A crash mid-write leaves the last line incomplete — detectable and truncatable.

---

## Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| **SQLite** | Fine for transactional rows; weak for columnar analytical scans over Parquet; awkward for the "point a query at a directory of files" pattern. DuckDB strictly dominates. |
| **PostgreSQL / PostGIS** | Adds a persistent server process, backup procedures, and schema migrations. Buys multi-writer concurrency we don't need. Clean upgrade path if concurrency appears (it shouldn't for a solo operator). |
| **Kafka / Spark / Streaming stack** | Massive operational surface area for data volumes that fit in RAM. The streaming-like needs (lineup news, orderbook updates) are handled by event-triggered cron fast-paths. Requires a measured latency bottleneck to justify. |
| **Redis** | Appropriate for low-latency in-memory key-value; overkill for our cadence (seconds, not microseconds); adds a server process. |

---

## Consequences

### Positive
- The entire data plane is **files on disk plus a library import**. Reproducible, inspectable, trivially backed up with `rsync`.
- No service to keep alive, no cluster to babysit.
- A new developer can set up the full data layer in under 5 minutes.

### Negative / Cost
- Single-node: concurrent write access from multiple processes is not supported. (For a solo operator, this is not a constraint.)
- DuckDB in-memory caching may conflict if multiple scripts query large datasets simultaneously (manageable with read-only connections).

### Explicit Upgrade Points
- **Postgres**: if multi-writer concurrency is ever needed (e.g., multiple operators, distributed backtest runners).
- **A streaming layer** (Kafka, Redpanda): only if a measured latency bottleneck is proven by profiling.

### Failure Mode Avoided
Infrastructure that consumes the research and modeling time that should go into edge quality.
