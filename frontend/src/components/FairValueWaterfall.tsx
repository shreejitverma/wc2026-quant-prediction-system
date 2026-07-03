/**
 * FairValueWaterfall: model probability → fees → timing/lockup → resolution
 * risk → fair value, as positioned bars (ADR-0016: bespoke chart, custom DOM -
 * a charting library's waterfall would be config-wrestling for four rows).
 *
 * Honesty rules this component owns:
 *  - it renders the payload's decomposition verbatim and REFUSES (visible
 *    error, not silence) if the steps do not sum to the claimed fair value:
 *    a waterfall that doesn't account for the whole number teaches wrong
 *    intuition about where fair value comes from;
 *  - adjustments are neutral ink; only the endpoints wear series-1. A fee is
 *    not "bad for me" - direction hues stay reserved for edge.
 */
import type { FairValueStep } from "@/lib/api";

const STEP_LABEL: Record<FairValueStep["label"], string> = {
  model_probability: "model probability",
  fees: "fees",
  timing_lockup: "timing / lockup",
  resolution_risk: "resolution risk",
};

export function FairValueWaterfall({ steps }: { steps: FairValueStep[] }) {
  if (steps.length === 0) return null;
  let walk = 0;
  for (const s of steps) walk += s.delta;
  const fair = steps[steps.length - 1].value_after;
  if (Math.abs(walk - fair) > 1e-6) {
    return (
      <div
        data-testid="waterfall-invalid"
        className="rounded border border-status-warn/60 px-2 py-1 text-xs text-status-warn"
      >
        DECOMPOSITION INCONSISTENT — steps sum to {walk.toFixed(4)}, fair value claims{" "}
        {fair.toFixed(4)}. Refusing to draw it.
      </div>
    );
  }

  // Scale bars to the model probability (first step) - adjustments are small,
  // so each bar spans [value_after - |delta| … value_after] of that scale.
  const scale = Math.max(...steps.map((s) => s.value_after), 0.0001);
  return (
    <div className="space-y-1" data-testid="fair-value-waterfall">
      {steps.map((s, i) => {
        const isEndpoint = i === 0;
        const left = Math.min(s.value_after, s.value_after - s.delta);
        const width = Math.abs(s.delta);
        return (
          <div key={s.label} className="flex items-center gap-2">
            <span className="w-32 shrink-0 text-right text-[11px] text-muted-foreground">
              {STEP_LABEL[s.label]}
            </span>
            <div className="relative h-3 flex-1 rounded-sm bg-muted/30">
              <div
                className={`absolute inset-y-0 rounded-sm ${isEndpoint ? "bg-series-1/80" : "bg-uncertain/60"}`}
                style={{ left: `${(100 * left) / scale}%`, width: `${(100 * width) / scale}%` }}
              />
            </div>
            <span className="w-16 shrink-0 text-right font-mono text-[11px]">
              {i === 0 ? s.delta.toFixed(3) : `${s.delta >= 0 ? "+" : ""}${s.delta.toFixed(3)}`}
            </span>
          </div>
        );
      })}
      <div className="flex items-center gap-2 border-t border-border/50 pt-1">
        <span className="w-32 shrink-0 text-right text-[11px] font-semibold">fair value</span>
        <div className="relative h-3 flex-1 rounded-sm bg-muted/30">
          <div
            className="absolute inset-y-0 rounded-sm bg-series-1"
            style={{ left: 0, width: `${(100 * fair) / scale}%` }}
          />
        </div>
        <span className="w-16 shrink-0 text-right font-mono text-[11px] font-semibold">
          {fair.toFixed(3)}
        </span>
      </div>
    </div>
  );
}
