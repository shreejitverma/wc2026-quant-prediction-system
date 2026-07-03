/**
 * Ops (Phase 6 core): is every source fresh enough to trust the quotes, and
 * what needs acknowledging.
 *
 * Rules this screen owns:
 *  - freshness status is computed server-side against per-source max ages -
 *    the UI renders the verdict, it never re-derives it;
 *  - alert acknowledgment is a LEDGERED command (idempotent) - acks survive
 *    restarts and sit in the hash chain like every other operator action;
 *  - acked alerts stay visible (dimmed) - an acknowledged warning is history,
 *    not deleted evidence;
 *  - pipeline runs are REAL (runs.jsonl); freshness/reconciliation are
 *    labeled mock until ingestion persists snapshots.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  commandAckAlert,
  fetchAlerts,
  fetchOpsFreshness,
  fetchRuns,
  type Alert,
} from "@/lib/api";
import { ProvenanceChip, SourceBanner } from "@/components/Provenance";
import { localWithOffset, utcShort } from "@/lib/time";

const SEV_STYLE: Record<Alert["severity"], string> = {
  critical: "border-status-critical/60 text-status-critical",
  warn: "border-status-warn/60 text-status-warn",
  info: "border-border text-muted-foreground",
};

function fmtAge(seconds: number): string {
  if (seconds < 90) return `${Math.round(seconds)}s`;
  if (seconds < 5400) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export default function OpsPage() {
  const queryClient = useQueryClient();
  const alerts = useQuery({ queryKey: ["alerts"], queryFn: fetchAlerts, refetchInterval: 30_000 });
  const freshness = useQuery({ queryKey: ["ops-freshness"], queryFn: fetchOpsFreshness, refetchInterval: 30_000 });
  const runs = useQuery({ queryKey: ["runs"], queryFn: fetchRuns });

  const ack = useMutation({
    mutationFn: (alertId: string) => commandAckAlert(alertId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const a = alerts.data?.data;
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Ops</h1>
        <ProvenanceChip provenance={freshness.data?.provenance} />
      </div>

      <SourceBanner provenances={[freshness.data?.provenance, alerts.data?.provenance]} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Data-source freshness</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full border-collapse" data-testid="freshness-matrix">
              <thead>
                <tr className="border-b border-border text-[10px] uppercase text-muted-foreground">
                  <th className="py-1 text-left font-medium">source</th>
                  <th className="py-1 text-right font-medium">last ok</th>
                  <th className="py-1 text-right font-medium">age</th>
                  <th className="py-1 text-right font-medium">limit</th>
                  <th className="py-1 text-right font-medium">status</th>
                </tr>
              </thead>
              <tbody>
                {(freshness.data?.data.sources ?? []).map((s) => (
                  <tr key={s.source} className="border-b border-border/40">
                    <td className="py-1 text-xs">{s.source}</td>
                    <td className="py-1 text-right font-mono text-xs text-muted-foreground">
                      {utcShort(s.last_success_utc)}
                    </td>
                    <td className="py-1 text-right font-mono text-xs">{fmtAge(s.staleness_seconds)}</td>
                    <td className="py-1 text-right font-mono text-xs text-muted-foreground">
                      {fmtAge(s.max_age_seconds)}
                    </td>
                    <td className="py-1 text-right">
                      <span
                        className={`font-mono text-[10px] font-bold uppercase ${
                          s.status === "ok" ? "text-muted-foreground" : "text-status-warn"
                        }`}
                      >
                        {s.status === "ok" ? "● ok" : `⚠ ${s.status}`}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-3 space-y-1 border-t border-border/50 pt-2">
              {(freshness.data?.data.reconciliation ?? []).map((r) => (
                <p key={r.venue} className="text-xs text-muted-foreground">
                  <span className="font-mono">{r.venue}</span> reconciliation:{" "}
                  <span className={r.status === "match" ? "text-status-good" : "text-status-warn"}>
                    {r.status}
                  </span>{" "}
                  — {r.detail}
                </p>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              Alerts{" "}
              {a && (
                <span className="font-mono text-xs text-muted-foreground">
                  ({a.unacked} unacked of {a.alerts.length})
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2" data-testid="alert-center">
            {a?.alerts.length === 0 && (
              <p className="text-sm text-muted-foreground">0 alerts — definitive, not an error.</p>
            )}
            {(a?.alerts ?? []).map((al) => (
              <div
                key={al.alert_id}
                data-testid={`alert-${al.alert_id}`}
                className={`space-y-1 rounded border px-3 py-2 ${SEV_STYLE[al.severity]} ${
                  al.acked ? "opacity-50" : ""
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[10px] font-bold uppercase">
                    {al.severity} · {al.kind.replace("_", " ")}
                  </span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {utcShort(al.ts_utc)} · {localWithOffset(al.ts_utc)}
                  </span>
                </div>
                <p className="text-xs text-foreground">{al.message}</p>
                {al.acked ? (
                  <p className="font-mono text-[10px] text-muted-foreground">
                    acked {al.acked_at ? utcShort(al.acked_at) : ""} (ledgered)
                  </p>
                ) : (
                  <button
                    className="rounded border border-border px-2 py-0.5 text-[11px] hover:bg-accent"
                    onClick={() => ack.mutate(al.alert_id)}
                    data-testid={`ack-${al.alert_id}`}
                  >
                    Acknowledge (ledgered)
                  </button>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">
            Pipeline runs{" "}
            <span className="font-normal text-muted-foreground">
              (real — {runs.data?.data.total_runs ?? 0} in runs.jsonl)
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {runs.data?.data.runs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              0 runs recorded — definitive. Runs appear here when the pipeline executes
              (uv run python -m wc2026.ops.cron …).
            </p>
          ) : (
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-border text-[10px] uppercase text-muted-foreground">
                  <th className="py-1 text-left font-medium">run</th>
                  <th className="py-1 text-left font-medium">model</th>
                  <th className="py-1 text-left font-medium">git</th>
                  <th className="py-1 text-right font-medium">created</th>
                </tr>
              </thead>
              <tbody>
                {(runs.data?.data.runs ?? []).map((r) => (
                  <tr key={r.run_id} className="border-b border-border/40 font-mono text-xs">
                    <td className="py-1">{r.run_id.slice(0, 12)}</td>
                    <td className="py-1">
                      {r.model_name}@{r.model_version}
                    </td>
                    <td className="py-1 text-muted-foreground">{r.git_commit?.slice(0, 8) ?? "—"}</td>
                    <td className="py-1 text-right text-muted-foreground">{localWithOffset(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
