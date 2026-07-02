# ADR-0009: LLM news pipeline is an information router, never an autonomous trading signal

- Status: accepted
- Date: 2026-07-01

## Context

Operator constraint (2026-07-01): the Tier 5 LLM news-extraction pipeline is in scope.
It is high-value (beat-source injury/rotation news decays fast and moves quotes) but is the one component that can silently become an autonomous trading signal if not fenced.
LLM extraction is probabilistic and hallucination-prone; letting it move money without a human is an uncontrolled risk.

## Decision

We will treat LLM news extraction as an information *router*:
- Feeds (RSS/API from reliable beat sources) -> LLM structured extraction into typed events (`player X doubtful`, `coach confirms rotation`) with **source, confidence, and timestamp** logged as provenance.
- Any extracted fact whose implied quote move exceeds `news.review_threshold_quote_move` (default 2%) goes to a **human review queue** before it can influence a quote.
- The fence is encoded in the type system: `NewsConfig.autonomous_trading` is `Literal[False]` — setting it true in YAML raises a validation error. There is no code path from LLM output directly to an order.

## Alternatives rejected

- **LLM output feeds quotes directly** — one hallucinated "star player injured" prints a wrong quote at size; unacceptable.
- **Skip LLM news entirely** — forfeits a genuine, fast-decaying information edge the operator explicitly wants.

## Consequences

Every traded fact has a logged provenance chain (source -> extraction -> human confirmation for material moves).
The LLM accelerates information *routing* without ever being trusted as an autonomous decision-maker.
Failure mode avoided: an automated system trading on a fabricated or misparsed news item.
