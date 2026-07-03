/**
 * Performance (Phase 5, Job 4): is the system beating the de-vigged market
 * by enough to justify size.
 *
 * Rules this screen owns: CLV is the headline (P&L follows CLV; watching P&L
 * first teaches variance-worship); every number wears n and a CI; defaults
 * show FULL history - date-range cherry-picking is not a control this page
 * offers; the cumulative chart is backend-tested to agree with the headline.
 */
import { useQuery } from "@tanstack/react-query";
import { Area, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchCalibration, fetchClv, fetchPnl, type CIValue } from "@/lib/api";
import { ProvenanceChip, SourceBanner } from "@/components/Provenance";
import { ReliabilityChart } from "@/components/ReliabilityChart";

const tickLocal = (iso: string) =>
  new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(iso));

function CIStat({ label, v, unit }: { label: string; v: CIValue; unit: string }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="font-mono text-2xl font-bold">
        {v.value >= 0 ? "+" : ""}
        {v.value.toFixed(2)}
        {unit}
      </div>
      <div className="font-mono text-xs text-muted-foreground">
        [{v.ci_lo.toFixed(2)}–{v.ci_hi.toFixed(2)}] · n={v.n}
      </div>
    </div>
  );
}

export default function PerformancePage() {
  const clv = useQuery({ queryKey: ["eval-clv"], queryFn: fetchClv });
  const pnl = useQuery({ queryKey: ["eval-pnl"], queryFn: fetchPnl });
  const cal = useQuery({ queryKey: ["eval-cal", "ensemble"], queryFn: () => fetchCalibration("ensemble") });

  if (clv.isLoading)
    return <div className="p-8 text-center text-muted-foreground animate-pulse">Scoring full history…</div>;

  const c = clv.data?.data;
  const p = pnl.data?.data;
  const maxHist = Math.max(...(c?.histogram ?? []).map((b) => b.count), 1);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Performance — full history (no date filter by design)</h1>
        <ProvenanceChip provenance={clv.data?.provenance} />
      </div>

      <SourceBanner provenances={[clv.data?.provenance, pnl.data?.provenance, cal.data?.provenance]} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">CLV — the headline (close vs entry, prob points)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {c && (
              <>
                <div className="flex gap-8">
                  <CIStat label="mean CLV / trade" v={c.mean_pp} unit="pp" />
                  {c.by_class.map((bc) => (
                    <CIStat key={bc.market_class} label={bc.market_class} v={bc.mean_pp} unit="pp" />
                  ))}
                </div>
                <div className="h-40">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={c.cumulative} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                      <XAxis dataKey="ts_utc" tickFormatter={tickLocal} fontSize={9} stroke="var(--muted-foreground)" tickLine={false} axisLine={false} minTickGap={40} />
                      <YAxis fontSize={9} stroke="var(--muted-foreground)" tickLine={false} axisLine={false} width={40} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "var(--popover)", borderColor: "var(--border)", fontSize: 11 }}
                        formatter={(v) => [`${Number(v).toFixed(1)}pp`, "cumulative CLV"]}
                        labelFormatter={(l) => tickLocal(String(l))}
                      />
                      <Line dataKey="cum_pp" stroke="var(--series-1)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                {/* per-trade distribution: honest about the spread around the mean */}
                <div className="flex h-14 items-end gap-px" data-testid="clv-histogram">
                  {c.histogram.map((b) => (
                    <div
                      key={b.lo_pp}
                      className={`flex-1 ${b.lo_pp >= 0 ? "bg-series-1/60" : "bg-uncertain/50"}`}
                      style={{ height: `${(100 * b.count) / maxHist}%` }}
                      title={`${b.lo_pp.toFixed(1)}–${b.hi_pp.toFixed(1)}pp: ${b.count} trades`}
                    />
                  ))}
                </div>
                <p className="text-[10px] text-muted-foreground">
                  Per-trade CLV distribution (gray = negative side; hue marks sign, not judgment).
                  CLV leads P&L: if this is positive and P&L is not, that is variance, not a broken model.
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Calibration — ensemble reliability</CardTitle>
          </CardHeader>
          <CardContent>
            {cal.data && <ReliabilityChart report={cal.data.data} />}
            <p className="mt-2 text-[10px] text-muted-foreground">
              Points on the diagonal = honest probabilities. Whiskers are Wilson 95% per bin; the
              strip shows how many samples each bin actually holds.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">
            Paper P&L{" "}
            {p && (
              <span className="font-normal text-muted-foreground">
                — n={p.n_trades} trades · max drawdown {p.max_drawdown.toFixed(2)} · {(p.kelly_fraction * 100).toFixed(0)}% of full Kelly
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={p?.points ?? []} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <XAxis dataKey="ts_utc" tickFormatter={tickLocal} fontSize={9} stroke="var(--muted-foreground)" tickLine={false} axisLine={false} minTickGap={40} />
                <YAxis fontSize={9} stroke="var(--muted-foreground)" tickLine={false} axisLine={false} width={44} />
                <Tooltip
                  contentStyle={{ backgroundColor: "var(--popover)", borderColor: "var(--border)", fontSize: 11 }}
                  formatter={(v, name) => [Number(v).toFixed(2), String(name)]}
                  labelFormatter={(l) => tickLocal(String(l))}
                />
                <Area dataKey="drawdown" stroke="none" fill="var(--uncertain)" fillOpacity={0.3} isAnimationActive={false} />
                <Line dataKey="cum_pnl" stroke="var(--series-1)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <p className="text-[10px] text-muted-foreground">
            Blue = cumulative paper P&L ($1 notional/event); gray area = drawdown from peak. PAPER
            mode — this number has never touched an exchange.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
