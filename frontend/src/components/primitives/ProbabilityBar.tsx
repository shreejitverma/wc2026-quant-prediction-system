/**
 * ProbabilityBar: the only sanctioned way to render a probability (ADR-0013).
 *
 * The band is REQUIRED - by the type system and again at runtime. A probability
 * without uncertainty is exactly the number this terminal refuses to show; if a
 * caller has no band it must say so on screen ("NO BAND"), not draw a bar that
 * looks as authoritative as a calibrated one.
 *
 * Visual grammar: blue fill = point estimate (magnitude, sequential hue);
 * gray strip = the band (neutral - uncertainty never wears a direction hue);
 * white tick = the market's price on the SAME scale, so "market inside my
 * band" is visible before any edge number is read.
 */

const pct = (x: number) => `${(100 * x).toFixed(1)}%`;

export interface ProbabilityBarProps {
  p: number;
  band: readonly [number, number];
  market?: number;
  label?: string;
}

function bandInvalid(p: number, band: readonly [number, number] | undefined): boolean {
  // Guard before destructuring: an untyped caller passing no band must get
  // the visible refusal, not a crash that unmounts the whole screen.
  if (!Array.isArray(band) || band.length !== 2) return true;
  const [lo, hi] = band;
  return (
    !Number.isFinite(lo) || !Number.isFinite(hi) || lo > hi || lo < 0 || hi > 1 || !Number.isFinite(p)
  );
}

export function ProbabilityBar({ p, band, market, label }: ProbabilityBarProps) {
  if (bandInvalid(p, band)) {
    return (
      <div className="flex items-center gap-2" data-testid="probability-bar-invalid">
        {label && <span className="w-24 shrink-0 text-xs text-muted-foreground">{label}</span>}
        <span className="rounded border border-status-warn/60 px-1.5 py-0.5 text-[10px] font-semibold text-status-warn">
          NO BAND
        </span>
        <span className="text-xs text-muted-foreground">refusing to render without uncertainty</span>
      </div>
    );
  }
  const [lo, hi] = band;
  return (
    <div className="flex items-center gap-2" data-testid="probability-bar">
      {label && <span className="w-24 shrink-0 text-xs text-muted-foreground">{label}</span>}
      <div className="relative h-2.5 flex-1 overflow-hidden rounded-sm bg-muted/60">
        <div
          data-testid="pb-band"
          className="absolute inset-y-0 bg-uncertain/35"
          style={{ left: pct(lo), width: pct(hi - lo) }}
          title={`band ${pct(lo)} – ${pct(hi)}`}
        />
        <div
          data-testid="pb-point"
          className="absolute inset-y-0 w-[3px] -translate-x-1/2 rounded-full bg-series-1"
          style={{ left: pct(p) }}
        />
        {market !== undefined && (
          <div
            data-testid="pb-market"
            className="absolute inset-y-0 w-px bg-foreground/90"
            style={{ left: pct(market) }}
            title={`market ${pct(market)}`}
          />
        )}
      </div>
      <span className="w-28 shrink-0 text-right text-xs">
        <span className="font-semibold">{pct(p)}</span>{" "}
        <span className="text-muted-foreground">
          [{pct(lo)}–{pct(hi)}]
        </span>
      </span>
    </div>
  );
}
