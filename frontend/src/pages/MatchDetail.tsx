/**
 * Match Detail - the workhorse screen (Phase 2, Job 1).
 *
 * Layout answers, top to bottom: what is this match and how fresh is my
 * information (header + lineup status); what does the ensemble believe and
 * how sure is it (heatmap + banded probabilities); who agrees and who is
 * earning their weight (model board vs the de-vigged market); WHY we
 * disagree with the market, in football language (never act on an
 * unexplained disagreement); and how belief and price evolved as
 * information arrived (timeline).
 */
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  fetchMatchDetail,
  fetchMatchTimeline,
  type Attribution,
  type MatchDetail,
  type ModelProbs,
} from "@/lib/api";
import { ProvenanceChip, SourceBanner } from "@/components/Provenance";
import { ProbabilityBar } from "@/components/primitives/ProbabilityBar";
import { ScorelineHeatmap } from "@/components/ScorelineHeatmap";
import { FairValueTimeline } from "@/components/FairValueTimeline";
import { localWithOffset, utcShort } from "@/lib/time";

const pct = (x: number) => `${(100 * x).toFixed(1)}`;

/** Lineup confirmation is the biggest pre-kickoff information event; its
 * arrival must be unmissable (status-good + timestamp), and its absence
 * visible (neutral EXPECTED, never alarming - waiting is the normal state). */
function LineupChip({ lineup }: { lineup: MatchDetail["lineup"] }) {
  if (lineup.state === "confirmed" && lineup.confirmed_at) {
    return (
      <span
        data-testid="lineup-chip"
        className="inline-flex items-center gap-1.5 rounded border border-status-good/60 bg-status-good/10 px-2 py-0.5 font-mono text-xs font-bold text-status-good"
      >
        XI CONFIRMED · {utcShort(lineup.confirmed_at)}
      </span>
    );
  }
  return (
    <span
      data-testid="lineup-chip"
      className="inline-flex items-center gap-1.5 rounded border border-border px-2 py-0.5 font-mono text-xs text-muted-foreground"
    >
      XI EXPECTED · checked {utcShort(lineup.as_of)}
    </span>
  );
}

/** A table beats a chart here: 8 rows x 6 numbers is a read-off task, not a
 * comparison-of-shapes task. Market row is the baseline the eye anchors on. */
function ModelBoard({ detail }: { detail: MatchDetail }) {
  const cols: Array<[string, (m: ModelProbs) => number]> = [
    ["H", (m) => m.p_home],
    ["D", (m) => m.p_draw],
    ["A", (m) => m.p_away],
    ["O2.5", (m) => m.p_over_2_5],
    ["BTTS", (m) => m.p_btts],
  ];
  const row = (m: ModelProbs, cls = "") => (
    <tr key={m.model} className={`border-b border-border/50 ${cls}`}>
      <td className="py-1 pr-2 font-mono text-xs">{m.model}</td>
      <td className="py-1 pr-2 text-right font-mono text-xs text-muted-foreground">
        {m.weight != null ? m.weight.toFixed(2) : "—"}
      </td>
      {cols.map(([k, f]) => (
        <td key={k} className="py-1 pl-3 text-right font-mono text-xs">
          {pct(f(m))}
        </td>
      ))}
    </tr>
  );
  return (
    <table className="w-full border-collapse" data-testid="model-board">
      <thead>
        <tr className="border-b border-border text-[10px] uppercase text-muted-foreground">
          <th className="py-1 pr-2 text-left font-medium">model</th>
          <th className="py-1 pr-2 text-right font-medium">wt</th>
          {cols.map(([k]) => (
            <th key={k} className="py-1 pl-3 text-right font-medium">
              {k}%
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {detail.models.map((m) => row(m))}
        {row(detail.ensemble, "font-semibold bg-muted/30")}
        <tr className="bg-muted/20">
          <td className="py-1 pr-2 font-mono text-xs text-muted-foreground">
            market (de-vig, {detail.market.venue})
          </td>
          <td className="py-1 pr-2 text-right font-mono text-xs text-muted-foreground">—</td>
          <td className="py-1 pl-3 text-right font-mono text-xs">{pct(detail.market.p_home)}</td>
          <td className="py-1 pl-3 text-right font-mono text-xs">{pct(detail.market.p_draw)}</td>
          <td className="py-1 pl-3 text-right font-mono text-xs">{pct(detail.market.p_away)}</td>
          <td className="py-1 pl-3 text-right font-mono text-xs text-muted-foreground" colSpan={2}>
            overround {detail.market.overround.toFixed(3)} · as of {utcShort(detail.market.as_of)}
          </td>
        </tr>
      </tbody>
    </table>
  );
}

/** The rule this panel enforces on the operator: never act on a disagreement
 * you cannot explain. Bars are neutral ink - attribution magnitude is not a
 * buy signal, and the deltas sum to the whole ensemble-vs-market gap. */
function WhyPanel({ why }: { why: Attribution[] }) {
  const total = why.reduce((s, w) => s + w.delta_pp, 0);
  const maxAbs = Math.max(...why.map((w) => Math.abs(w.delta_pp)), 0.01);
  return (
    <div className="space-y-2" data-testid="why-panel">
      {why.map((w) => (
        <div key={w.feature}>
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-mono text-xs">{w.feature}</span>
            <span className="font-mono text-xs text-muted-foreground">
              +{w.delta_pp.toFixed(1)}pp → {w.direction}
            </span>
          </div>
          <div className="mt-0.5 h-1 w-full rounded bg-muted/40">
            <div
              className="h-1 rounded bg-uncertain/70"
              style={{ width: `${(100 * Math.abs(w.delta_pp)) / maxAbs}%` }}
            />
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">{w.note}</p>
        </div>
      ))}
      <p className="border-t border-border/50 pt-1 text-[10px] text-muted-foreground">
        Σ {total.toFixed(1)}pp = full ensemble-vs-market gap. If this panel does not convince you,
        the market knows something the model does not - stay flat.
      </p>
    </div>
  );
}

export default function MatchDetailPage() {
  const { matchId = "" } = useParams();
  const detail = useQuery({
    queryKey: ["match", matchId],
    queryFn: () => fetchMatchDetail(matchId),
    enabled: matchId !== "",
  });
  const timeline = useQuery({
    queryKey: ["match", matchId, "timeline"],
    queryFn: () => fetchMatchTimeline(matchId),
    enabled: matchId !== "",
  });

  if (detail.isLoading)
    return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading match…</div>;
  if (detail.isError || !detail.data)
    return (
      <div className="p-8 text-center text-status-critical">
        Match {matchId} not found or API unreachable.{" "}
        <Link to="/matches" className="underline">
          Back to matches
        </Link>
      </div>
    );

  const d = detail.data.data;
  const restDiff = d.rest_days_home - d.rest_days_away;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link to="/matches" className="text-sm text-muted-foreground hover:text-foreground">
          ‹ Matches
        </Link>
        <ProvenanceChip provenance={detail.data.provenance} />
      </div>

      <SourceBanner provenances={[detail.data.provenance, timeline.data?.provenance]} />

      {/* Header: everything that changes how the numbers below should be read. */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">
            {d.home_team} <span className="text-muted-foreground text-xl font-normal">vs</span>{" "}
            {d.away_team}
          </h1>
          {d.group && <Badge variant="outline">Group {d.group}</Badge>}
          <LineupChip lineup={d.lineup} />
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>
            kickoff {utcShort(d.kickoff_utc)} · {localWithOffset(d.kickoff_utc)}
          </span>
          <span>
            {d.venue.name}, {d.venue.city}
          </span>
          {d.venue.altitude_m >= 1000 && (
            <Badge variant="outline" className="text-status-warn border-status-warn/50">
              ⛰ {d.venue.altitude_m}m altitude
            </Badge>
          )}
          {d.venue.heat_risk !== "low" && (
            <Badge variant="outline" className="text-status-warn border-status-warn/50">
              heat: {d.venue.heat_risk}
            </Badge>
          )}
          <span>
            rest {d.rest_days_home}d / {d.rest_days_away}d
            {restDiff !== 0 && (
              <span className="ml-1 font-semibold text-foreground">
                ({restDiff > 0 ? "+" : ""}
                {restDiff}d {restDiff > 0 ? d.home_team : d.away_team})
              </span>
            )}
          </span>
          <span>
            xG {d.expected_goals_home.toFixed(2)} – {d.expected_goals_away.toFixed(2)}
          </span>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Scoreline distribution (ensemble)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ScorelineHeatmap matrix={d.scoreline_matrix} homeTeam={d.home_team} awayTeam={d.away_team} />
            <div className="space-y-2 pt-2">
              <ProbabilityBar label={`${d.home_team} win`} p={d.prob_home_win.p} band={[d.prob_home_win.lo, d.prob_home_win.hi]} market={d.market.p_home} />
              <ProbabilityBar label="Draw" p={d.prob_draw.p} band={[d.prob_draw.lo, d.prob_draw.hi]} market={d.market.p_draw} />
              <ProbabilityBar label={`${d.away_team} win`} p={d.prob_away_win.p} band={[d.prob_away_win.lo, d.prob_away_win.hi]} market={d.market.p_away} />
              <ProbabilityBar label="Over 2.5" p={d.prob_over_2_5.p} band={[d.prob_over_2_5.lo, d.prob_over_2_5.hi]} />
              <ProbabilityBar label="BTTS" p={d.prob_btts.p} band={[d.prob_btts.lo, d.prob_btts.hi]} />
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Model board vs de-vigged market</CardTitle>
            </CardHeader>
            <CardContent>
              <ModelBoard detail={d} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Why the ensemble disagrees with the market</CardTitle>
            </CardHeader>
            <CardContent>
              <WhyPanel why={d.why} />
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Price vs fair value — full history</CardTitle>
        </CardHeader>
        <CardContent>
          {timeline.isLoading && (
            <div className="p-6 text-center text-muted-foreground animate-pulse">Loading timeline…</div>
          )}
          {timeline.data && <FairValueTimeline timeline={timeline.data.data} />}
          {timeline.isError && (
            <div className="p-6 text-center text-status-warn">Timeline unavailable.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
