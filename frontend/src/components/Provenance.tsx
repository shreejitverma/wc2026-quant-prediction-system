/**
 * Provenance primitives (ADR-0012). Two rules they enforce:
 *  - mock data is impossible to mistake for real (loud banner, not a footnote);
 *  - "as of" comes from the payload's provenance, never from `new Date()` -
 *    the client clock tells you when you looked, not how fresh the data is.
 */
import { AlertTriangle } from "lucide-react";
import type { Provenance } from "@/lib/api";

export function SourceBanner({ provenances }: { provenances: (Provenance | undefined)[] }) {
  const mock = provenances.filter((p) => p?.source === "mock").length;
  if (mock === 0) return null;
  return (
    <div
      role="status"
      className="flex items-center gap-2 rounded-md border border-amber-500/60 bg-amber-500/15 px-3 py-2 text-sm font-semibold text-amber-500"
    >
      <AlertTriangle className="h-4 w-4 shrink-0" />
      MOCK DATA — this screen is not wired to the real pipeline yet. Do not act on these numbers.
    </div>
  );
}

export function ProvenanceChip({ provenance }: { provenance: Provenance | undefined }) {
  if (!provenance) return null;
  const asOf = provenance.data_as_of ?? provenance.generated_at;
  const commit = provenance.git_commit?.slice(0, 8) ?? "no-git";
  return (
    <span
      className="inline-flex items-center gap-2 rounded border border-border px-2 py-0.5 font-mono text-xs text-muted-foreground"
      title={`config ${provenance.config_hash.slice(0, 12)} · generated ${provenance.generated_at}`}
    >
      <span>{provenance.source === "mock" ? "MOCK" : commit}</span>
      <span>as of {new Date(asOf).toLocaleString()}</span>
    </span>
  );
}
