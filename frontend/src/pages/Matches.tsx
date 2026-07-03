import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useQuery } from "@tanstack/react-query"
import { fetchMatches, type MatchPrediction } from "@/lib/api"
import { ProvenanceChip, SourceBanner } from "@/components/Provenance"
import { ProbabilityBar } from "@/components/primitives/ProbabilityBar"

export default function MatchesPage() {
  const { data: envelope, isLoading } = useQuery({ queryKey: ['matches'], queryFn: fetchMatches })
  const matches = envelope?.data

  if (isLoading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading matches...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Match Predictions</h1>
        <ProvenanceChip provenance={envelope?.provenance} />
      </div>

      <SourceBanner provenances={[envelope?.provenance]} />

      <div className="grid gap-6">
        {matches?.map((match: MatchPrediction, i: number) => (
          <Card key={i} className="overflow-hidden">
            <div className="flex flex-col md:flex-row">
              <div className="p-6 flex-1 border-b md:border-b-0 md:border-r bg-card/50">
                <div className="flex items-center justify-between mb-4">
                  <Badge variant="outline">Group Stage</Badge>
                  <span className="text-xs text-muted-foreground">Updated: {new Date(match.freshness_utc).toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center text-2xl font-black tracking-tighter">
                  <span>{match.home_team}</span>
                  <span className="text-muted-foreground text-sm font-normal">vs</span>
                  <span>{match.away_team}</span>
                </div>
                <div className="flex justify-between items-center mt-2 text-sm text-muted-foreground">
                  <span>xG: {match.expected_goals_home.toFixed(2)}</span>
                  <span>xG: {match.expected_goals_away.toFixed(2)}</span>
                </div>
              </div>
              <div className="flex-1 p-6 flex flex-col justify-center gap-3">
                {([
                  [`${match.home_team} win`, match.prob_home_win],
                  ["Draw", match.prob_draw],
                  [`${match.away_team} win`, match.prob_away_win],
                ] as const).map(([label, p]) => {
                  // Mock band from the mock uncertainty score; labeled MOCK above.
                  const half = Math.max(0.01, match.uncertainty_score * 0.05)
                  return (
                    <ProbabilityBar
                      key={label}
                      label={label}
                      p={p}
                      band={[Math.max(0, p - half), Math.min(1, p + half)]}
                    />
                  )
                })}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
