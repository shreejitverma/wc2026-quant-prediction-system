/**
 * Ledger browser (REAL data): the shell's proof screen. Decision it supports:
 * "can I trust that nothing in my history was rewritten, and which run/config
 * produced any number I quoted." Verification runs against the actual chain;
 * new entries stream in over the multiplexed WS `ledger` topic.
 */

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchLedger, fetchLedgerVerify, fetchRuns } from "@/lib/api";
import { useTopic } from "@/lib/wsHooks";
import { ProvenanceChip } from "@/components/Provenance";
import { localWithOffset, utcShort } from "@/lib/time";

export default function LedgerPage() {
  const queryClient = useQueryClient();
  const [kind, setKind] = useState<string | undefined>(undefined);

  const ledger = useQuery({
    queryKey: ["ledger", kind ?? "all"],
    queryFn: () => fetchLedger({ kind, limit: 200 }),
  });
  const verify = useQuery({ queryKey: ["ledger-verify"], queryFn: fetchLedgerVerify });
  const runs = useQuery({ queryKey: ["runs"], queryFn: fetchRuns });

  useTopic("ledger", () => {
    queryClient.invalidateQueries({ queryKey: ["ledger"] });
    queryClient.invalidateQueries({ queryKey: ["ledger-verify"] });
  });

  const kinds = [undefined, "ops", "run", "prediction", "quote", "fill", "command"] as const;
  const entries = ledger.data?.data.entries ?? [];
  const v = verify.data?.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Ledger</h1>
        <ProvenanceChip provenance={ledger.data?.provenance} />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Chain Integrity</CardTitle>
          </CardHeader>
          <CardContent>
            {v == null ? (
              <div className="text-muted-foreground text-sm">verifying…</div>
            ) : v.valid ? (
              <div className="text-2xl font-bold">VALID</div>
            ) : (
              <div className="text-2xl font-bold text-status-critical">BROKEN</div>
            )}
            <p className="text-xs text-muted-foreground">
              {v ? `${v.entries} entries · ${v.path} · recomputed from genesis` : ""}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Entries</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{ledger.data?.data.total_entries ?? 0}</div>
            <p className="text-xs text-muted-foreground">append-only; live tail via WS</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runs.data?.data.total_runs ?? 0}</div>
            <p className="text-xs text-muted-foreground">reproducible run records</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Entries</CardTitle>
          <div className="flex gap-1">
            {kinds.map((k) => (
              <button
                key={k ?? "all"}
                onClick={() => setKind(k)}
                className={`rounded px-2 py-1 text-xs ${
                  kind === k ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/50"
                }`}
              >
                {k ?? "all"}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          {entries.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              0 entries match — definitive, not an error.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-14">seq</TableHead>
                  <TableHead>time (UTC · local)</TableHead>
                  <TableHead>kind</TableHead>
                  <TableHead>payload</TableHead>
                  <TableHead className="text-right">row hash</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...entries].reverse().map((e) => (
                  <TableRow key={e.seq}>
                    <TableCell className="font-mono">{e.seq}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {utcShort(e.ts_utc)} · {localWithOffset(e.ts_utc)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{e.kind}</Badge>
                    </TableCell>
                    <TableCell className="max-w-md truncate font-mono text-xs text-muted-foreground">
                      {JSON.stringify(e.payload)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-muted-foreground">
                      {String(e.row_hash).slice(0, 12)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Runs</CardTitle>
        </CardHeader>
        <CardContent>
          {(runs.data?.data.runs ?? []).length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              0 runs recorded — definitive, not an error.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>run</TableHead>
                  <TableHead>model</TableHead>
                  <TableHead>created</TableHead>
                  <TableHead>git</TableHead>
                  <TableHead>metrics</TableHead>
                  <TableHead>notes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(runs.data?.data.runs ?? []).map((r) => (
                  <TableRow key={r.run_id}>
                    <TableCell className="font-mono text-xs">{r.run_id.slice(0, 12)}</TableCell>
                    <TableCell>
                      {r.model_name}
                      <span className="ml-1 text-xs text-muted-foreground">{r.model_version}</span>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {localWithOffset(r.created_at)}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {r.git_commit?.slice(0, 8) ?? "—"}
                      {r.git_dirty && <span className="ml-1 text-status-warn">dirty</span>}
                    </TableCell>
                    <TableCell className="max-w-40 truncate font-mono text-xs text-muted-foreground">
                      {Object.keys(r.metrics).length ? JSON.stringify(r.metrics) : "—"}
                    </TableCell>
                    <TableCell className="max-w-md truncate text-xs text-muted-foreground">
                      {r.notes || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
