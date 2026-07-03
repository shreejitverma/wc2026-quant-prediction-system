"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, AlertTriangle, BookLock, Shield } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchHealth, fetchOpportunities } from "@/lib/api";
import { ProvenanceChip, SourceBanner } from "@/components/Provenance";

/**
 * Command Center, Phase 0 scope: every number on this page is either real
 * (health/ledger, from pipeline artifacts) or sits under the MOCK banner.
 * The fabricated KPI cards from the scaffold (session PnL, active matches,
 * stale-contract counts) are gone until a real endpoint backs them.
 */
export default function GlobalCommandCenter() {
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth, refetchInterval: 15_000 });
  const opps = useQuery({ queryKey: ["opportunities"], queryFn: fetchOpportunities });

  if (health.isLoading || opps.isLoading)
    return (
      <div className="p-8 text-center text-muted-foreground animate-pulse">
        Loading command center...
      </div>
    );
  if (health.isError)
    return (
      <div className="p-8 text-center text-red-500">
        API unreachable — is the backend running? (make api)
      </div>
    );

  const h = health.data?.data;
  const topOpportunities = (opps.data?.data ?? []).slice(0, 3);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">Command Center</h1>
          {h && (
            <Badge
              variant={h.mode === "live" ? "destructive" : "secondary"}
              className="uppercase tracking-widest"
            >
              {h.mode}
            </Badge>
          )}
        </div>
        <ProvenanceChip provenance={health.data?.provenance} />
      </div>

      <SourceBanner provenances={[opps.data?.provenance]} />

      {/* KPI cards: real values from /api/v1/health only. */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Data Status</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div
              className={`text-2xl font-bold uppercase tabular-nums ${
                h?.data_status === "ok" ? "" : "text-amber-500"
              }`}
            >
              {h?.data_status}
            </div>
            <p className="text-xs text-muted-foreground">
              {h?.ledger_staleness_seconds != null
                ? `last ledger write ${Math.round(h.ledger_staleness_seconds)}s ago (limit ${h.max_data_staleness_seconds}s)`
                : "no ledger entries yet"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ledger</CardTitle>
            <BookLock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">{h?.ledger_entries ?? 0}</div>
            <p className="text-xs text-muted-foreground">append-only entries, hash-chained</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Stay-Flat Threshold</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {h ? `${(h.min_edge * 100).toFixed(1)}%` : "—"}
            </div>
            <p className="text-xs text-muted-foreground">min post-fee edge to act (config)</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Kill Switch</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold uppercase">
              {h?.kill_switch_enabled ? "Armed" : "Disabled"}
            </div>
            <p className="text-xs text-muted-foreground">
              venues: {h?.venues.kalshi_enabled ? "kalshi " : ""}
              {h?.venues.polymarket_enabled ? "polymarket" : ""}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Top Opportunities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {topOpportunities.map((opp) => (
                <div
                  key={opp.ticker}
                  className="flex items-center justify-between p-4 border rounded-lg bg-card/50"
                >
                  <div className="flex flex-col gap-1">
                    <span className="text-sm font-bold">{opp.ticker}</span>
                    <span className="text-xs text-muted-foreground">{opp.venue}</span>
                  </div>
                  <div className="flex gap-6 text-sm tabular-nums">
                    <div className="flex flex-col items-end">
                      <span className="text-muted-foreground text-xs">Bid/Ask</span>
                      <span>
                        {opp.best_bid.toFixed(2)} / {opp.best_ask.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className="text-muted-foreground text-xs">Fair Value</span>
                      <span className="font-bold">{opp.fair_value.toFixed(2)}</span>
                    </div>
                    <div className="flex flex-col items-end">
                      <span className="text-muted-foreground text-xs">Edge</span>
                      <span className="font-bold">
                        {(opp.edge_after_fees * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>P&amp;L</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              No fills recorded — 0 paper trades in the ledger. Execution (paper) arrives with the
              MM console phase; this panel stays empty rather than inventing a number.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
