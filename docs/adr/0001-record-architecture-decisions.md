# ADR-0001: Record architecture decisions

- Status: accepted
- Date: 2026-07-01

## Context

This is a solo build spanning statistics, market microstructure, and infrastructure, run over months.
Decisions made in Sprint 1 will look arbitrary in Sprint 4 unless the reasoning is captured.
A system whose goal is to make self-deception hard must first make its own past reasoning auditable.

## Decision

We will record every significant, hard-to-reverse, or non-obvious decision as a numbered ADR in `docs/adr/`, using the `0000-template.md` format (Context / Decision / Alternatives rejected / Consequences).
ADRs are append-only in spirit: a reversed decision gets a new ADR that supersedes the old one; the old one is marked superseded, never deleted.

## Alternatives rejected

- **No ADRs, rely on commit messages** — commit messages explain *what* changed, rarely *why not the alternative*; the rejected-options reasoning is exactly what future-me needs.
- **A single running design doc** — becomes a swamp; loses the one-decision-per-file auditability and the supersession trail.

## Consequences

Every design claim in this repo is traceable to a dated rationale.
Slight overhead per decision; that overhead is the point, since it forces the alternatives to be named.
