/**
 * Opportunity Board (Phase 3, Jobs 2-3): every priced contract on both
 * venues, ranked by risk-adjusted after-fee edge, each discrepancy classified
 * BEFORE the operator may act on it.
 *
 * Honesty rules this screen owns:
 *  - the min-edge filter's FLOOR is the backend's stay-flat threshold: the UI
 *    can be stricter than config, never looser;
 *  - a row whose settlement mapping is unconfirmed renders quarantined
 *    (dimmed, badge says UNCONFIRMED) - inspectable, never attractive;
 *  - row expansion shows the fair-value waterfall and the settlement text
 *    next to the model event it allegedly prices - the trap lives in that
 *    gap, so the screen puts them side by side.
 */
import { Fragment, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useQuery } from "@tanstack/react-query"
import { fetchCoherence, fetchHealth, fetchOpportunities, type MarketOpportunity } from "@/lib/api"
import { EdgeBadge } from "@/components/primitives/EdgeBadge"
import { FairValueWaterfall } from "@/components/FairValueWaterfall"
import { ProvenanceChip, SourceBanner } from "@/components/Provenance"
import { utcShort } from "@/lib/time"

const pct1 = (x: number) => `${(100 * x).toFixed(1)}%`

function SettlementPanel({ row }: { row: MarketOpportunity }) {
  const s = row.settlement
  return (
    <div className="space-y-1" data-testid="settlement-panel">
      <div className="text-[10px] uppercase text-muted-foreground">settlement mapping</div>
      <p className="text-xs italic text-muted-foreground">“{s.market_text}”</p>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-muted-foreground">→ model event</span>
        <span className="font-mono">{s.model_event}</span>
        {s.confirmed ? (
          <span className="rounded border border-status-good/60 px-1.5 py-0.5 font-mono text-[10px] text-status-good">
            CONFIRMED {s.confirmed_at ? `· ${utcShort(s.confirmed_at)}` : ""}
          </span>
        ) : (
          <span className="rounded border border-status-warn/60 bg-status-warn/10 px-1.5 py-0.5 font-mono text-[10px] font-bold text-status-warn">
            UNCONFIRMED — QUARANTINED
          </span>
        )}
      </div>
      {s.note && <p className="text-xs text-status-warn">{s.note}</p>}
    </div>
  )
}

export default function MarketsPage() {
  const { data: envelope, isLoading } = useQuery({ queryKey: ['opportunities'], queryFn: fetchOpportunities })
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth })
  const coherence = useQuery({ queryKey: ['coherence'], queryFn: fetchCoherence })
  // The stay-flat threshold comes from backend config only. If health is
  // unavailable the honest fallback is "cannot assess edge" (+Infinity blanks
  // every badge to no-edge), never a number invented client-side.
  const configFloor = health.data?.data.min_edge ?? Number.POSITIVE_INFINITY
  // Filter default derives from server config on every load - deliberately
  // ephemeral (plain state, no persistence) so yesterday's personal filter
  // cannot silently hide today's edges.
  const [minEdgePct, setMinEdgePct] = useState<number | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)
  const effectiveMin = Math.max(minEdgePct != null ? minEdgePct / 100 : 0, Number.isFinite(configFloor) ? configFloor : 0)

  if (isLoading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading markets...</div>

  const all = envelope?.data ?? []
  // Quarantined/stale rows always show (they are information); the min-edge
  // filter only prunes the actionable-looking tail.
  const rows = all.filter(
    (m) => m.actionability === 'Unsafe' || m.actionability === 'Stale' || Math.abs(m.edge_risk_adjusted) >= effectiveMin,
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Opportunity Board</h1>
        <ProvenanceChip provenance={envelope?.provenance} />
      </div>

      <SourceBanner provenances={[envelope?.provenance, coherence.data?.provenance]} />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle>Ranked by risk-adjusted after-fee edge</CardTitle>
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            min |edge|
            <input
              type="number"
              step={0.5}
              min={Number.isFinite(configFloor) ? configFloor * 100 : 0}
              value={minEdgePct ?? (Number.isFinite(configFloor) ? configFloor * 100 : 0)}
              onChange={(e) => {
                const v = Number(e.target.value)
                const floorPct = Number.isFinite(configFloor) ? configFloor * 100 : 0
                setMinEdgePct(Number.isNaN(v) ? null : Math.max(v, floorPct))
              }}
              className="w-16 rounded border border-input bg-transparent px-2 py-1 text-right font-mono text-xs"
              data-testid="min-edge-input"
            />
            % <span>(config floor {Number.isFinite(configFloor) ? pct1(configFloor) : "unknown"})</span>
          </label>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead />
                <TableHead>Contract</TableHead>
                <TableHead>Venue</TableHead>
                <TableHead className="text-right">Fair ± band</TableHead>
                <TableHead className="text-right">Bid/Ask</TableHead>
                <TableHead className="text-right">Depth</TableHead>
                <TableHead className="text-right">Unc</TableHead>
                <TableHead className="text-right">Edge (risk-adj)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="py-6 text-center text-muted-foreground">
                    0 contracts above {pct1(effectiveMin)} — definitive, not an error.
                  </TableCell>
                </TableRow>
              )}
              {rows.map((m) => {
                const quarantined = m.actionability === 'Unsafe'
                const open = expanded === m.ticker
                return (
                  <Fragment key={m.ticker}>
                    <TableRow
                      data-testid={`opp-row-${m.ticker}`}
                      data-quarantined={quarantined}
                      className={`cursor-pointer ${quarantined ? "opacity-55" : ""}`}
                      onClick={() => setExpanded(open ? null : m.ticker)}
                    >
                      <TableCell className="w-6 text-muted-foreground">{open ? "▾" : "▸"}</TableCell>
                      <TableCell className="text-xs">{m.contract_label}
                        <span className="ml-2 font-mono text-[10px] text-muted-foreground">{m.ticker}</span>
                      </TableCell>
                      <TableCell><Badge variant="outline">{m.venue}</Badge></TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {m.fair.p.toFixed(3)}
                        <span className="text-muted-foreground"> [{m.fair.lo.toFixed(3)}–{m.fair.hi.toFixed(3)}]</span>
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {m.best_bid.toFixed(3)} / {m.best_ask.toFixed(3)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs text-muted-foreground">
                        {m.depth_bid}×{m.depth_ask}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs text-muted-foreground">
                        {m.uncertainty_score.toFixed(2)}
                      </TableCell>
                      <TableCell className="text-right">
                        <EdgeBadge
                          edgeAfterFees={m.edge_risk_adjusted}
                          minEdge={configFloor}
                          stale={m.actionability === 'Stale'}
                          unconfirmedMapping={!m.settlement.confirmed}
                          classification={m.classification}
                        />
                      </TableCell>
                    </TableRow>
                    {open && (
                      <TableRow data-testid={`opp-detail-${m.ticker}`}>
                        <TableCell />
                        <TableCell colSpan={7} className="bg-muted/20">
                          <div className="grid gap-6 py-2 lg:grid-cols-2">
                            <div>
                              <div className="mb-1 text-[10px] uppercase text-muted-foreground">fair-value decomposition</div>
                              <FairValueWaterfall steps={m.decomposition} />
                            </div>
                            <SettlementPanel row={m} />
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Cross-venue coherence</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event</TableHead>
                  <TableHead className="text-right">Kalshi</TableHead>
                  <TableHead className="text-right">Poly</TableHead>
                  <TableHead className="text-right">De-vig ref</TableHead>
                  <TableHead className="text-right">Max spread</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(coherence.data?.data.cross_venue ?? []).map((c) => (
                  <TableRow key={c.event}>
                    <TableCell className="text-xs">{c.event}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{c.kalshi?.toFixed(3) ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{c.polymarket?.toFixed(3) ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs text-muted-foreground">{c.devig_ref?.toFixed(3) ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{c.max_spread_pp.toFixed(1)}pp</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Internal coherence (joint draws)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(coherence.data?.data.internal ?? []).map((v) => (
              <div key={v.description} className="space-y-0.5 border-b border-border/50 pb-2 text-xs">
                <p className="text-muted-foreground">{v.description}</p>
                <p className="font-mono">
                  product {v.product_price.toFixed(3)} vs direct {v.direct_price.toFixed(3)}{" "}
                  <span className="font-semibold">({v.gap_pp > 0 ? "+" : ""}{v.gap_pp.toFixed(1)}pp)</span>
                  <span className="ml-2 rounded bg-muted px-1 py-0.5 text-[10px] uppercase text-muted-foreground">
                    safest: {v.safest_class}
                  </span>
                </p>
              </div>
            ))}
            <p className="text-[10px] text-muted-foreground">
              Bracket-path products vs direct prices, answered from the persisted simulation draws
              (mock until the simulator persists). Divergence spikes usually mean stale data, not free money.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
