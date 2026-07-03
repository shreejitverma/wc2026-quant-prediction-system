/**
 * Model Race (Phase 5): which model is earning its ensemble weight - without
 * overclaiming.
 *
 * Rules this screen owns: scores arrive sorted with bootstrap CIs attached;
 * the Diebold-Mariano column answers "better than the de-vigged market?" with
 * a significance verdict, and an insignificant difference says so in plain
 * text (a lucky week cannot promote a model here); the market baseline sits
 * IN the table, not in a footnote.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Line, LineChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchCalibration, fetchModelRace, type CIValue } from "@/lib/api";
import { ProvenanceChip, SourceBanner } from "@/components/Provenance";
import { ReliabilityChart } from "@/components/ReliabilityChart";

const SERIES_TOKENS = ["--series-1", "--series-2", "--series-3", "--series-4", "--series-5", "--series-6"];

const fmtCI = (v: CIValue) => (
  <span className="font-mono text-xs">
    {v.value.toFixed(4)} <span className="text-muted-foreground">[{v.ci_lo.toFixed(4)}–{v.ci_hi.toFixed(4)}]</span>
  </span>
);

const tickLocal = (iso: string) =>
  new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(iso));

export default function ModelsPage() {
  const race = useQuery({ queryKey: ["model-race"], queryFn: fetchModelRace });
  const [drill, setDrill] = useState("ensemble");
  const cal = useQuery({ queryKey: ["eval-cal", drill], queryFn: () => fetchCalibration(drill) });

  if (race.isLoading)
    return <div className="p-8 text-center text-muted-foreground animate-pulse">Running the race…</div>;

  const r = race.data?.data;
  const models = (r?.rows ?? []).filter((row) => row.model !== "market (de-vig)").map((row) => row.model);
  const weightsData = (r?.weights_over_time ?? []).map((w) => ({ ts: w.ts_utc, ...w.weights }));
  const weightModels = Object.keys(r?.weights_over_time[0]?.weights ?? {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <h1 className="text-3xl font-bold tracking-tight">Model Race</h1>
          {r && <span className="font-mono text-xs text-muted-foreground">n = {r.n} resolved events</span>}
        </div>
        <ProvenanceChip provenance={race.data?.provenance} />
      </div>

      <SourceBanner provenances={[race.data?.provenance]} />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">League table — bootstrap 95% CIs; DM test vs the de-vigged market</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full border-collapse" data-testid="race-table">
            <thead>
              <tr className="border-b border-border text-[10px] uppercase text-muted-foreground">
                <th className="py-1 text-left font-medium">model</th>
                <th className="py-1 text-right font-medium">wt</th>
                <th className="py-1 pl-4 text-right font-medium">log loss</th>
                <th className="py-1 pl-4 text-right font-medium">brier</th>
                <th className="py-1 pl-4 text-right font-medium">vs market (DM)</th>
              </tr>
            </thead>
            <tbody>
              {(r?.rows ?? []).map((row) => {
                const isMarket = row.model === "market (de-vig)";
                return (
                  <tr key={row.model} className={`border-b border-border/40 ${isMarket ? "bg-muted/25" : ""}`}>
                    <td className="py-1.5 font-mono text-xs">{row.model}</td>
                    <td className="py-1.5 text-right font-mono text-xs text-muted-foreground">
                      {row.weight != null ? row.weight.toFixed(2) : "—"}
                    </td>
                    <td className="py-1.5 pl-4 text-right">{fmtCI(row.log_loss)}</td>
                    <td className="py-1.5 pl-4 text-right">{fmtCI(row.brier)}</td>
                    <td className="py-1.5 pl-4 text-right font-mono text-xs">
                      {isMarket ? (
                        <span className="text-muted-foreground">baseline</span>
                      ) : (
                        <>
                          {row.dm_vs_market.toFixed(2)}{" "}
                          {row.dm_significant ? (
                            <span title="significant at 5% (|DM| > 1.96)">*</span>
                          ) : (
                            <span className="text-muted-foreground">not significant</span>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-2 text-[10px] text-muted-foreground">
            Negative DM = lower loss than the market. "not significant" means exactly that: with
            n={r?.n}, this difference is indistinguishable from luck — do not reweight on it.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Ensemble-weight evolution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weightsData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                  <XAxis dataKey="ts" tickFormatter={tickLocal} fontSize={9} stroke="var(--muted-foreground)" tickLine={false} axisLine={false} minTickGap={40} />
                  <YAxis fontSize={9} stroke="var(--muted-foreground)" tickLine={false} axisLine={false} width={34} tickFormatter={(v: number) => v.toFixed(2)} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "var(--popover)", borderColor: "var(--border)", fontSize: 11 }}
                    formatter={(v, name) => [Number(v).toFixed(3), String(name)]}
                    labelFormatter={(l) => tickLocal(String(l))}
                  />
                  <Legend wrapperStyle={{ fontSize: 9 }} />
                  {weightModels.map((m, i) => (
                    <Line
                      key={m}
                      dataKey={m}
                      stroke={`var(${SERIES_TOKENS[i % SERIES_TOKENS.length]})`}
                      strokeWidth={1.5}
                      dot={false}
                      isAnimationActive={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[10px] text-muted-foreground">
              Fixed series order and direct legend per ADR-0013 — colors never cycle between reloads.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm">Per-model calibration drill-down</CardTitle>
            <select
              className="rounded border border-input bg-transparent px-2 py-1 font-mono text-xs [&>option]:bg-popover"
              value={drill}
              onChange={(e) => setDrill(e.target.value)}
              aria-label="model"
            >
              {["ensemble", ...models.filter((m) => m !== "ensemble")].map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </CardHeader>
          <CardContent>{cal.data && <ReliabilityChart report={cal.data.data} />}</CardContent>
        </Card>
      </div>
    </div>
  );
}
