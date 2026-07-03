/**
 * EdgeBadge: renders an after-fee edge only when it is honest to do so.
 *
 * Precedence (edgeState, pure and unit-tested): an unconfirmed settlement
 * mapping quarantines the contract outright; stale data blanks the edge; a
 * market price inside the model's uncertainty band is NO EDGE regardless of
 * the point estimate; below the config stay-flat threshold is NO EDGE. Only
 * then may a direction hue appear - blue for me, red against - always with a
 * glyph and sign so color never carries the meaning alone.
 */

export type EdgeClassification = "my-info" | "their-info" | "settlement-trap" | "incoherence";

export interface EdgeInputs {
  edgeAfterFees: number;
  minEdge: number;
  stale?: boolean;
  unconfirmedMapping?: boolean;
  marketInsideBand?: boolean;
}

export type EdgeStateKind = "quarantined" | "stale" | "no-edge" | "pos" | "neg";

export interface EdgeState {
  kind: EdgeStateKind;
  label: string;
}

export function edgeState(i: EdgeInputs): EdgeState {
  if (i.unconfirmedMapping) return { kind: "quarantined", label: "UNCONFIRMED" };
  if (i.stale) return { kind: "stale", label: "STALE" };
  if (i.marketInsideBand) return { kind: "no-edge", label: "no edge · inside band" };
  if (Math.abs(i.edgeAfterFees) < i.minEdge) return { kind: "no-edge", label: "no edge" };
  const sign = i.edgeAfterFees > 0 ? "+" : "";
  const glyph = i.edgeAfterFees > 0 ? "▲" : "▼";
  return {
    kind: i.edgeAfterFees > 0 ? "pos" : "neg",
    label: `${glyph} ${sign}${(100 * i.edgeAfterFees).toFixed(1)}%`,
  };
}

const STYLES: Record<EdgeStateKind, string> = {
  quarantined: "border-status-warn/60 text-status-warn",
  stale: "border-status-warn/60 text-status-warn",
  "no-edge": "border-border text-muted-foreground",
  pos: "border-edge-pos/50 text-edge-pos",
  neg: "border-edge-neg/50 text-edge-neg",
};

const CLASSIFICATION_LABEL: Record<EdgeClassification, string> = {
  "my-info": "my info",
  "their-info": "their info",
  "settlement-trap": "settlement trap",
  incoherence: "incoherence",
};

export function EdgeBadge({
  classification,
  ...inputs
}: EdgeInputs & { classification?: EdgeClassification }) {
  const s = edgeState(inputs);
  return (
    <span className="inline-flex items-center gap-1.5" data-edge-state={s.kind}>
      <span
        className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-xs font-semibold ${STYLES[s.kind]}`}
      >
        {s.label}
      </span>
      {classification && (s.kind === "pos" || s.kind === "neg") && (
        <span className="rounded bg-muted px-1 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
          {CLASSIFICATION_LABEL[classification]}
        </span>
      )}
    </span>
  );
}
