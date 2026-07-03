/**
 * JointQueryExplorer: P(A ∧ B ∧ …) answered by COUNTING the persisted
 * simulation draws - the UI for the coherence edge (ADR-0006).
 *
 * The result always shows three things side by side: the counted joint (with
 * Wilson CI and n), the naive product of marginals, and their ratio. The
 * ratio IS the edge: markets price paths as products; the draws know the
 * bracket. A ratio of 1.0 is also an answer - it says the naive price is fair.
 *
 * State teaching note: this POST is a READ (idempotent query semantics), so it
 * lives in useQuery keyed by the event list - repeat queries hit the cache -
 * rather than useMutation, which is reserved for writes with side effects.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { postSimQuery, type SimQueryEvent } from "@/lib/api";

const OUTCOMES: Array<[SimQueryEvent["outcome"], string]> = [
  ["wins_group", "wins group"],
  ["qualifies", "reaches R32"],
  ["reaches_r16", "reaches R16"],
  ["reaches_qf", "reaches QF"],
  ["reaches_sf", "reaches SF"],
  ["reaches_final", "reaches final"],
  ["champion", "champion"],
];

const pct = (x: number, d = 2) => `${(100 * x).toFixed(d)}%`;

export function JointQueryExplorer({ teams }: { teams: string[] }) {
  const [events, setEvents] = useState<SimQueryEvent[]>([
    { team: teams[0] ?? "", outcome: "wins_group" },
    { team: teams[1] ?? "", outcome: "reaches_final" },
  ]);
  const [submitted, setSubmitted] = useState<SimQueryEvent[] | null>(null);

  const result = useQuery({
    queryKey: ["sim-query", submitted],
    queryFn: () => postSimQuery(submitted!),
    enabled: submitted !== null,
  });

  const setEvent = (i: number, patch: Partial<SimQueryEvent>) =>
    setEvents((es) => es.map((e, j) => (j === i ? { ...e, ...patch } : e)));

  const selectCls =
    "rounded border border-input bg-transparent px-2 py-1 text-xs font-mono [&>option]:bg-popover";

  const r = result.data?.data;
  return (
    <div className="space-y-3" data-testid="joint-query-explorer">
      <div className="flex flex-wrap items-center gap-2">
        {events.map((e, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <span className="font-mono text-sm text-muted-foreground">∧</span>}
            <select
              aria-label={`team ${i + 1}`}
              className={selectCls}
              value={e.team}
              onChange={(ev) => setEvent(i, { team: ev.target.value })}
            >
              {teams.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
            <select
              aria-label={`outcome ${i + 1}`}
              className={selectCls}
              value={e.outcome}
              onChange={(ev) => setEvent(i, { outcome: ev.target.value as SimQueryEvent["outcome"] })}
            >
              {OUTCOMES.map(([v, label]) => (
                <option key={v} value={v}>
                  {label}
                </option>
              ))}
            </select>
          </span>
        ))}
        {events.length < 4 && (
          <button
            className="rounded border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
            onClick={() => setEvents((es) => [...es, { team: teams[0] ?? "", outcome: "champion" }])}
          >
            + event
          </button>
        )}
        {events.length > 1 && (
          <button
            className="rounded border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent"
            onClick={() => setEvents((es) => es.slice(0, -1))}
          >
            − event
          </button>
        )}
        <button
          className="rounded bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground hover:opacity-90"
          onClick={() => setSubmitted([...events])}
          data-testid="run-query"
        >
          Query draws
        </button>
      </div>

      {result.isLoading && submitted && (
        <p className="text-xs text-muted-foreground animate-pulse">counting draws…</p>
      )}
      {result.isError && (
        <p className="text-xs text-status-warn">Query failed — is the API up?</p>
      )}
      {r && (
        <div className="space-y-1 rounded border border-border/60 bg-muted/20 p-3" data-testid="query-result">
          <p className="font-mono text-sm">
            P(joint) = <span className="font-bold">{pct(r.p.p)}</span>{" "}
            <span className="text-muted-foreground">
              [{pct(r.p.lo)}–{pct(r.p.hi)}] · {r.n_hits.toLocaleString()} of{" "}
              {r.n_draws.toLocaleString()} draws
            </span>
          </p>
          <p className="font-mono text-xs text-muted-foreground">
            naive product of marginals = {pct(r.independent_product)}
            {r.dependence_ratio != null && (
              <>
                {" "}
                → dependence <span className="font-bold text-foreground">×{r.dependence_ratio.toFixed(2)}</span>
              </>
            )}
          </p>
          <p className="text-[10px] text-muted-foreground">
            Counted from the draws, never multiplied. Markets often price paths as products; the
            ratio above is where cross-market incoherence hides. ×1.00 is also an answer.
          </p>
        </div>
      )}
    </div>
  );
}
