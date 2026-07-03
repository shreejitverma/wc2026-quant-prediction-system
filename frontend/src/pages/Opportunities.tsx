import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useQuery } from "@tanstack/react-query"
import { fetchHealth, fetchOpportunities, type MarketOpportunity } from "@/lib/api"
import { EdgeBadge } from "@/components/primitives/EdgeBadge"
import { ProvenanceChip, SourceBanner } from "@/components/Provenance"

export default function MarketsPage() {
  const { data: envelope, isLoading } = useQuery({ queryKey: ['opportunities'], queryFn: fetchOpportunities })
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth })
  // The stay-flat threshold comes from backend config only. If health is
  // unavailable the honest fallback is "cannot assess edge" (+Infinity blanks
  // every badge to no-edge), never a number invented client-side.
  const minEdge = health.data?.data.min_edge ?? Number.POSITIVE_INFINITY
  const markets = envelope?.data

  if (isLoading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading markets...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Opportunity Board</h1>
        <ProvenanceChip provenance={envelope?.provenance} />
      </div>

      <SourceBanner provenances={[envelope?.provenance]} />

      <Card>
        <CardHeader>
          <CardTitle>Mapped Markets</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ticker</TableHead>
                <TableHead>Venue</TableHead>
                <TableHead className="text-right">Bid/Ask</TableHead>
                <TableHead className="text-right">Fair Value</TableHead>
                <TableHead className="text-right">Edge</TableHead>
                <TableHead className="text-right">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {markets?.map((m: MarketOpportunity, i: number) => (
                <TableRow key={i}>
                  <TableCell className="font-mono font-medium">{m.ticker}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{m.venue}</Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {m.best_bid.toFixed(2)} / {m.best_ask.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums font-bold">
                    {m.fair_value.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right">
                    <EdgeBadge
                      edgeAfterFees={m.edge_after_fees}
                      minEdge={minEdge}
                      stale={m.actionability === 'Stale'}
                      unconfirmedMapping={m.actionability === 'Unsafe'}
                      marketInsideBand={m.actionability === 'No Edge'}
                    />
                  </TableCell>
                  <TableCell className="text-right">
                    <Badge variant={m.actionability === 'Tradeable' ? 'default' : 'secondary'}>
                      {m.actionability}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
