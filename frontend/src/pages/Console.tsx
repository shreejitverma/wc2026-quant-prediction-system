/**
 * MM Console (Phase 4, Job 5 - the sharp end).
 *
 * Rules this screen owns:
 *  - the quote FORMULA'S INPUTS are always visible (fair value, variance,
 *    inventory, gamma, T, fee floor, widen factor) - an operator who cannot
 *    see why the spread is wide will override the one time it is right;
 *  - control friction is proportional to risk direction: pause and widen-all
 *    (risk-reducing) are one click; resume (risk-increasing) demands a typed
 *    confirmation; kill lives globally (Shift-Cmd-K);
 *  - a stale feed degrades conservatively: the ladder dims and screams, and
 *    resume is disabled - the safe direction is never blocked, the risky one
 *    never defaults on;
 *  - every control is a fenced backend command that lands in the ledger;
 *    a 409 from the fence is surfaced verbatim, never retried silently.
 *
 * State teaching note: these are the terminal's first real useMutation calls -
 * writes with side effects. On success we invalidate the queries the command
 * changed (console, command state, health) instead of hand-patching caches:
 * the ledger fold is the truth, so re-reading it is the update.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  commandPause,
  commandResume,
  commandWiden,
  fetchConsole,
  fetchHealth,
  fetchOpportunities,
  fetchPortfolio,
} from "@/lib/api";
import { ProvenanceChip, SourceBanner } from "@/components/Provenance";
import { BookLadder } from "@/components/BookLadder";
import { ConfirmTyped } from "@/components/primitives/ConfirmTyped";
import { ageSeconds, utcShort } from "@/lib/time";

const pct = (x: number) => `${(100 * x).toFixed(1)}%`;

const NEWS_STYLE: Record<string, string> = {
  normal: "border-border text-muted-foreground",
  "lineup-window": "border-status-warn/60 text-status-warn",
  "post-goal": "border-status-warn/60 text-status-warn",
  quarantined: "border-status-warn/60 bg-status-warn/10 text-status-warn font-bold",
};

export default function ConsolePage() {
  const queryClient = useQueryClient();
  const opps = useQuery({ queryKey: ["opportunities"], queryFn: fetchOpportunities });
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth });
  const tickers = (opps.data?.data ?? []).map((o) => o.ticker);
  const [selected, setSelected] = useState<string | null>(null);
  const ticker = selected ?? tickers[0] ?? null;

  const consoleQ = useQuery({
    queryKey: ["console", ticker],
    queryFn: () => fetchConsole(ticker!),
    enabled: ticker !== null,
    refetchInterval: 5_000,
  });
  const portfolio = useQuery({ queryKey: ["portfolio"], queryFn: fetchPortfolio });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["console"] });
    queryClient.invalidateQueries({ queryKey: ["commands"] });
    queryClient.invalidateQueries({ queryKey: ["health"] });
  };
  const [fenceMsg, setFenceMsg] = useState<string | null>(null);
  const onFenceError = (e: Error) => setFenceMsg(e.message);

  const pause = useMutation({
    mutationFn: () => commandPause(ticker!, "console pause"),
    onSuccess: invalidate,
    onError: onFenceError,
  });
  const resume = useMutation({
    mutationFn: () => commandResume(ticker!, "console resume"),
    onSuccess: invalidate,
    onError: onFenceError,
  });
  const widen = useMutation({
    mutationFn: () => commandWiden(1.5),
    onSuccess: invalidate,
    onError: onFenceError,
  });
  const [resumeOpen, setResumeOpen] = useState(false);

  if (opps.isLoading)
    return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading console…</div>;
  if (!ticker)
    return <div className="p-8 text-center text-muted-foreground">0 contracts to quote — definitive.</div>;

  const c = consoleQ.data?.data;
  const maxAge = health.data?.data.max_data_staleness_seconds ?? 120;
  const stale = c ? ageSeconds(c.book_as_of) > maxAge : true;
  const killed = health.data?.data.killed ?? false;
  const q = c?.quote_inputs;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">MM Console</h1>
          <select
            className="rounded border border-input bg-transparent px-2 py-1 font-mono text-xs [&>option]:bg-popover"
            value={ticker}
            onChange={(e) => setSelected(e.target.value)}
            aria-label="contract"
          >
            {tickers.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          {killed && (
            <span className="rounded border border-status-critical/60 bg-status-critical/10 px-2 py-0.5 font-mono text-xs font-bold text-status-critical">
              KILLED — re-arm via CLI only
            </span>
          )}
        </div>
        <ProvenanceChip provenance={consoleQ.data?.provenance} />
      </div>

      <SourceBanner provenances={[consoleQ.data?.provenance]} />
      {fenceMsg && (
        <div
          role="alert"
          className="flex items-center justify-between rounded border border-status-warn/60 bg-status-warn/10 px-3 py-2 text-xs text-status-warn"
        >
          <span>Fence refused: {fenceMsg}</span>
          <button className="underline" onClick={() => setFenceMsg(null)}>
            dismiss
          </button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              Book — {ticker}{" "}
              {c && <span className="font-normal text-muted-foreground">as of {utcShort(c.book_as_of)}</span>}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {c ? (
              <BookLadder console={c} stale={stale} />
            ) : (
              <div className="p-6 text-center text-muted-foreground animate-pulse">loading book…</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm">Quote formula — inputs, not just output</CardTitle>
            {q && (
              <span
                className={`rounded border px-2 py-0.5 font-mono text-[10px] uppercase ${NEWS_STYLE[q.news_state]}`}
                data-testid="news-state"
              >
                {q.news_state}
              </span>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {q && c && (
              <>
                <div className="grid grid-cols-2 gap-x-6 gap-y-1 font-mono text-xs">
                  <span className="text-muted-foreground">fair value</span>
                  <span className="text-right">{q.fair_value.toFixed(4)}</span>
                  <span className="text-muted-foreground">variance p(1−p)</span>
                  <span className="text-right">{q.variance.toFixed(4)}</span>
                  <span className="text-muted-foreground">inventory</span>
                  <span className="text-right">{q.inventory > 0 ? "+" : ""}{q.inventory.toFixed(0)} contracts</span>
                  <span className="text-muted-foreground">time to settle</span>
                  <span className="text-right">{q.time_to_settlement_days}d</span>
                  <span className="text-muted-foreground">risk aversion γ</span>
                  <span className="text-right">{q.gamma}</span>
                  <span className="text-muted-foreground">fee floor</span>
                  <span className="text-right">{q.fee_floor.toFixed(3)}</span>
                  <span className="text-muted-foreground">widen factor (ledgered)</span>
                  <span className="text-right">×{q.widen_factor.toFixed(2)}</span>
                </div>
                <div className="border-t border-border/60 pt-2 font-mono text-sm">
                  → bid <span className="font-bold">{q.bid.toFixed(3)}</span> / ask{" "}
                  <span className="font-bold">{q.ask.toFixed(3)}</span>{" "}
                  <span className="text-xs text-muted-foreground">
                    spread {q.spread.toFixed(4)} · skew {q.skew >= 0 ? "+" : ""}
                    {q.skew.toFixed(4)} (inventory shade)
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2 border-t border-border/60 pt-3">
                  <span
                    className={`rounded px-2 py-1 font-mono text-xs font-bold ${
                      c.quoting_status === "active"
                        ? "bg-status-good/10 text-status-good border border-status-good/50"
                        : "bg-status-warn/10 text-status-warn border border-status-warn/50"
                    }`}
                    data-testid="quoting-status"
                  >
                    {c.quoting_status.toUpperCase()}
                  </span>
                  {c.quoting_status === "active" && (
                    <button
                      className="rounded border border-border px-3 py-1 text-xs hover:bg-accent"
                      onClick={() => pause.mutate()}
                      data-testid="pause-btn"
                    >
                      Pause quoting
                    </button>
                  )}
                  {c.quoting_status === "paused" && (
                    <button
                      className="rounded border border-status-warn/50 px-3 py-1 text-xs text-status-warn hover:bg-status-warn/10 disabled:cursor-not-allowed disabled:opacity-40"
                      onClick={() => setResumeOpen(true)}
                      disabled={killed || stale}
                      title={
                        killed
                          ? "Killed: resume is refused by the backend fence."
                          : stale
                            ? "Feed stale: resuming into a book you cannot see is how adverse selection collects."
                            : undefined
                      }
                      data-testid="resume-btn"
                    >
                      Resume quoting…
                    </button>
                  )}
                  <button
                    className="rounded border border-border px-3 py-1 text-xs hover:bg-accent"
                    onClick={() => widen.mutate()}
                    data-testid="widen-btn"
                  >
                    Widen all ×1.5
                  </button>
                  <span className="text-[10px] text-muted-foreground">
                    pause/widen: one click (risk-reducing) · resume: typed confirm · kill: ⇧⌘K
                  </span>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Inventory by correlation cluster</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(portfolio.data?.data.clusters ?? []).map((cl) => (
              <div key={cl.cluster_id} className="space-y-1 border-b border-border/40 pb-2">
                <div className="flex items-baseline justify-between text-xs">
                  <span>{cl.label}</span>
                  <span className="font-mono">
                    ${cl.net_exposure_usd.toFixed(0)} / ${cl.limit_usd.toFixed(0)}{" "}
                    <span className="text-muted-foreground">target ${cl.optimizer_target_usd.toFixed(0)}</span>
                  </span>
                </div>
                <div className="h-1.5 w-full rounded bg-muted/40">
                  <div
                    className={`h-1.5 rounded ${cl.utilization >= 0.85 ? "bg-status-warn" : "bg-uncertain/70"}`}
                    style={{ width: `${Math.min(100, 100 * cl.utilization)}%` }}
                    title={`utilization ${pct(cl.utilization)}`}
                  />
                </div>
              </div>
            ))}
            <p className="text-[10px] text-muted-foreground">
              Targets from the convex optimizer on the simulation covariance; amber ≥ 85% of limit.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Fills tape — annotated with context</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full border-collapse">
              <tbody>
                {(c?.fills ?? []).map((f, i) => (
                  <tr key={i} className="border-b border-border/40 font-mono text-xs">
                    <td className="py-1 text-muted-foreground">{utcShort(f.ts_utc)}</td>
                    <td className="py-1 uppercase">{f.side}</td>
                    <td className="py-1 text-right">{f.size}</td>
                    <td className="py-1 text-right">@{f.price.toFixed(3)}</td>
                    <td className="py-1 pl-3 text-muted-foreground">{f.context}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      <ConfirmTyped
        open={resumeOpen}
        onOpenChange={setResumeOpen}
        title="Resume quoting"
        description={`Resume posting two-sided quotes on ${ticker} (paper mode). The command is ledgered; the backend fence re-checks kill state.`}
        phrase="RESUME"
        confirmLabel="Resume"
        onConfirm={() => resume.mutate()}
      />
    </div>
  );
}
