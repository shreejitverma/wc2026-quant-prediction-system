/**
 * Tournament View (Phase 2, Job 1): where does tournament-level value hide.
 *
 * Ordered by decision priority: winner probabilities (with Wilson CIs from
 * draw counts - the headline numbers wear their sample size), the third-place
 * race (the 2026 format's 8-of-12 best-thirds machinery is where mispricing
 * concentrates), the advancement table (which replaces bracket art: P(reach
 * round) as a table is denser and cannot mislead about paths), group tables,
 * and the joint-query explorer - the coherence-edge UI.
 */
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchTournament } from "@/lib/api";
import { ProvenanceChip, SourceBanner } from "@/components/Provenance";
import { ProbabilityBar } from "@/components/primitives/ProbabilityBar";
import { JointQueryExplorer } from "@/components/JointQueryExplorer";

const pct = (x: number) => (100 * x).toFixed(1);

export default function TournamentPage() {
  const { data: envelope, isLoading, isError } = useQuery({
    queryKey: ["tournament"],
    queryFn: fetchTournament,
  });

  if (isLoading)
    return <div className="p-8 text-center text-muted-foreground animate-pulse">Counting draws…</div>;
  if (isError || !envelope)
    return (
      <div className="p-8 text-center text-status-critical">
        Tournament state unavailable — is the backend running? (make api)
      </div>
    );

  const t = envelope.data;
  const teams = t.advancement.map((a) => a.team);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <h1 className="text-3xl font-bold tracking-tight">Tournament</h1>
          <span className="font-mono text-xs text-muted-foreground">
            n = {t.n_draws.toLocaleString()} draws
          </span>
        </div>
        <ProvenanceChip provenance={envelope.provenance} />
      </div>

      <SourceBanner provenances={[envelope.provenance]} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Winner probabilities (Wilson 95% from draw counts)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {t.winner.map((w) => (
              <ProbabilityBar key={w.team} label={w.team} p={w.p.p} band={[w.p.lo, w.p.hi]} />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              Third-place race — 8 of 12 thirds advance (the format's hidden value)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full border-collapse" data-testid="third-place-race">
              <thead>
                <tr className="border-b border-border text-[10px] uppercase text-muted-foreground">
                  <th className="py-1 text-left font-medium">team</th>
                  <th className="py-1 text-right font-medium">grp</th>
                  <th className="py-1 text-right font-medium">P(3rd)</th>
                  <th className="py-1 text-right font-medium">P(adv | 3rd)</th>
                  <th className="py-1 text-right font-medium">P(best-3rd path)</th>
                </tr>
              </thead>
              <tbody>
                {t.third_place_race.slice(0, 10).map((c) => (
                  <tr key={c.team} className="border-b border-border/40">
                    <td className="py-1 font-mono text-xs">{c.team}</td>
                    <td className="py-1 text-right font-mono text-xs text-muted-foreground">{c.group}</td>
                    <td className="py-1 text-right font-mono text-xs">{pct(c.p_third)}%</td>
                    <td className="py-1 text-right font-mono text-xs">{pct(c.p_qualify_given_third)}%</td>
                    <td className="py-1 text-right font-mono text-xs font-semibold">
                      {pct(c.p_best_third_qualify)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-[10px] text-muted-foreground">
              Markets often price "advances" as if top-2 were the only path; the best-third column
              is the part they get wrong.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">
            Advancement — P(reach round), counted; each row must be non-increasing
          </CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full border-collapse" data-testid="advancement-table">
            <thead>
              <tr className="border-b border-border text-[10px] uppercase text-muted-foreground">
                <th className="py-1 text-left font-medium">team</th>
                {["R32", "R16", "QF", "SF", "F", "W"].map((h) => (
                  <th key={h} className="py-1 pl-3 text-right font-medium">
                    {h}%
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {t.advancement.map((a) => (
                <tr key={a.team} className="border-b border-border/40">
                  <td className="py-1 font-mono text-xs">{a.team}</td>
                  {[a.p_r32, a.p_r16, a.p_qf, a.p_sf, a.p_final, a.p_champion].map((p, i) => (
                    <td key={i} className="py-1 pl-3 text-right font-mono text-xs">
                      {pct(p)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {t.groups.map((g) => (
          <Card key={g.group}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Group {g.group}</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-border text-[10px] uppercase text-muted-foreground">
                    <th className="py-1 text-left font-medium">team</th>
                    <th className="py-1 text-right font-medium">1st</th>
                    <th className="py-1 text-right font-medium">2nd</th>
                    <th className="py-1 text-right font-medium">3rd</th>
                    <th className="py-1 text-right font-medium">adv</th>
                  </tr>
                </thead>
                <tbody>
                  {g.teams.map((team) => (
                    <tr key={team.team} className="border-b border-border/40">
                      <td className="py-1 font-mono text-xs">{team.team}</td>
                      <td className="py-1 text-right font-mono text-xs">{pct(team.p_first)}</td>
                      <td className="py-1 text-right font-mono text-xs">{pct(team.p_second)}</td>
                      <td className="py-1 text-right font-mono text-xs text-muted-foreground">
                        {pct(team.p_third)}
                      </td>
                      <td className="py-1 text-right font-mono text-xs font-semibold">
                        {pct(team.p_advance)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">
            Joint-probability explorer — P(A ∧ B) counted from the draws
          </CardTitle>
        </CardHeader>
        <CardContent>
          <JointQueryExplorer teams={teams} />
        </CardContent>
      </Card>
    </div>
  );
}
