/**
 * Matchday mode (Phase 6): the read-mostly view for watching matches away
 * from the desk. One column, thumb-sized, no dense tables - today's
 * fixtures, the live edge board (top rows only), inventory utilization,
 * unacked alerts, and the kill switch. Everything else stays on the desktop.
 *
 * Deliberately reuses the same queries and primitives as the main screens:
 * matchday is a VIEW, not a second implementation that can drift.
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  fetchAlerts,
  fetchHealth,
  fetchMatches,
  fetchOpportunities,
  fetchPortfolio,
} from "@/lib/api";
import { EdgeBadge } from "@/components/primitives/EdgeBadge";
import { SourceBanner } from "@/components/Provenance";
import { useUiStore } from "@/store/uiStore";
import { localWithOffset } from "@/lib/time";

export default function MatchdayPage() {
  // The kill dialog is owned by the shell (Topbar renders the single global
  // ConfirmTyped); matchday's button just opens it - one dialog, one truth.
  const { setKillDialogOpen } = useUiStore();
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth, refetchInterval: 30_000 });
  const matches = useQuery({ queryKey: ["matches"], queryFn: fetchMatches });
  const opps = useQuery({ queryKey: ["opportunities"], queryFn: fetchOpportunities, refetchInterval: 30_000 });
  const alerts = useQuery({ queryKey: ["alerts"], queryFn: fetchAlerts, refetchInterval: 30_000 });
  const portfolio = useQuery({ queryKey: ["portfolio"], queryFn: fetchPortfolio });

  const h = health.data?.data;
  const minEdge = h?.min_edge ?? Number.POSITIVE_INFINITY;
  const topEdges = (opps.data?.data ?? []).slice(0, 5);
  const unacked = (alerts.data?.data.alerts ?? []).filter((a) => !a.acked);

  return (
    <div className="mx-auto max-w-md space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold tracking-tight">Matchday</h1>
        <span
          className={`rounded border px-2 py-1 font-mono text-xs font-bold ${
            h?.killed
              ? "border-status-critical text-status-critical"
              : h?.mode === "live"
                ? "border-status-critical/60 text-status-critical"
                : "border-border text-muted-foreground"
          }`}
        >
          {h?.killed ? "● KILLED" : `● ${(h?.mode ?? "?").toUpperCase()}`}
        </span>
      </div>

      <SourceBanner provenances={[matches.data?.provenance, opps.data?.provenance]} />

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Today</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(matches.data?.data ?? []).map((m) => (
            <Link
              key={m.match_id}
              to={`/matches/${m.match_id}`}
              className="flex items-center justify-between rounded border border-border px-3 py-2 text-sm hover:bg-accent"
            >
              <span>
                {m.home_team} <span className="text-muted-foreground">v</span> {m.away_team}
              </span>
              <span className="font-mono text-xs text-muted-foreground">
                {(100 * m.prob_home_win).toFixed(0)}/{(100 * m.prob_draw).toFixed(0)}/
                {(100 * m.prob_away_win).toFixed(0)}
              </span>
            </Link>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Top edges (read-only here — act from the desk)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {topEdges.map((o) => (
            <div key={o.ticker} className="flex items-center justify-between gap-2 text-xs">
              <span className="truncate">{o.contract_label}</span>
              <EdgeBadge
                edgeAfterFees={o.edge_risk_adjusted}
                minEdge={minEdge}
                stale={o.actionability === "Stale"}
                unconfirmedMapping={!o.settlement.confirmed}
                classification={o.classification}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Inventory</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {(portfolio.data?.data.clusters ?? []).map((cl) => (
            <div key={cl.cluster_id} className="flex items-center justify-between text-xs">
              <span className="truncate">{cl.label}</span>
              <span className={`font-mono ${cl.utilization >= 0.85 ? "text-status-warn" : "text-muted-foreground"}`}>
                {(100 * cl.utilization).toFixed(0)}% of limit
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Alerts ({unacked.length} unacked)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {unacked.length === 0 && <p className="text-xs text-muted-foreground">0 unacked — definitive.</p>}
          {unacked.map((a) => (
            <p key={a.alert_id} className="text-xs">
              <span className="font-mono font-bold uppercase text-status-warn">{a.severity}</span>{" "}
              {a.message.slice(0, 120)}
              {a.message.length > 120 ? "…" : ""}{" "}
              <span className="text-muted-foreground">{localWithOffset(a.ts_utc)}</span>
            </p>
          ))}
          <p className="pt-1 text-[10px] text-muted-foreground">Acknowledge from Ops — matchday is read-mostly.</p>
        </CardContent>
      </Card>

      {!h?.killed && (
        <button
          className="w-full rounded-md border border-status-critical/60 py-3 font-mono text-sm font-bold text-status-critical hover:bg-status-critical/10"
          onClick={() => setKillDialogOpen(true)}
        >
          KILL SWITCH
        </button>
      )}
    </div>
  );
}
