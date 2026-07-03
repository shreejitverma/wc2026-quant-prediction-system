/**
 * ScorelineHeatmap (ADR-0013): the ensemble's full goals matrix.
 *
 * Honesty rules this component owns:
 *  - cell alpha is EXACTLY proportional to probability (no minimum-intensity
 *    floor: a near-zero cell must look near-zero, not 10% blue);
 *  - the display truncates at `displayMax` goals for density, so the residual
 *    tail mass is disclosed as a number instead of silently dropped;
 *  - the modal scoreline is outlined, values are always printed for cells
 *    above 1% and on hover for the rest - color alone never carries a value;
 *  - ink is the series-1 token via color-mix, never a hardcoded hex.
 */

export interface ScorelineHeatmapProps {
  matrix: number[][];
  homeTeam: string;
  awayTeam: string;
  displayMax?: number;
}

export function ScorelineHeatmap({ matrix, homeTeam, awayTeam, displayMax = 6 }: ScorelineHeatmapProps) {
  const n = matrix.length;
  const max = Math.min(displayMax, n - 1);

  let shownMass = 0;
  let best: { h: number; a: number; p: number } = { h: 0, a: 0, p: -1 };
  let maxShown = 0;
  for (let h = 0; h < n; h++) {
    for (let a = 0; a < n; a++) {
      const p = matrix[h]?.[a] ?? 0;
      if (p > best.p) best = { h, a, p };
      if (h <= max && a <= max) {
        shownMass += p;
        if (p > maxShown) maxShown = p;
      }
    }
  }
  const tail = Math.max(0, 1 - shownMass);

  return (
    <div className="inline-flex flex-col gap-1" data-testid="scoreline-heatmap">
      <div className="flex items-center gap-1">
        <div className="w-6" />
        <div
          className="grid flex-1 text-center text-[10px] text-muted-foreground"
          style={{ gridTemplateColumns: `repeat(${max + 1}, 2rem)` }}
        >
          {Array.from({ length: max + 1 }).map((_, a) => (
            <span key={a}>{a}</span>
          ))}
        </div>
      </div>
      {Array.from({ length: max + 1 }).map((_, h) => (
        <div key={h} className="flex items-center gap-1">
          <span className="w-6 text-right text-[10px] text-muted-foreground">{h}</span>
          <div className="grid gap-px" style={{ gridTemplateColumns: `repeat(${max + 1}, 2rem)` }}>
            {Array.from({ length: max + 1 }).map((_, a) => {
              const p = matrix[h]?.[a] ?? 0;
              const alpha = maxShown > 0 ? p / maxShown : 0;
              const isModal = h === best.h && a === best.a;
              return (
                <div
                  key={a}
                  data-testid={`cell-${h}-${a}`}
                  data-prob={p.toFixed(6)}
                  title={`${homeTeam} ${h}–${a} ${awayTeam}: ${(100 * p).toFixed(2)}%`}
                  className={`flex h-8 w-8 items-center justify-center rounded-[2px] font-mono text-[9px] ${
                    isModal ? "ring-1 ring-foreground/80" : ""
                  } ${alpha > 0.55 ? "text-background" : "text-muted-foreground"}`}
                  style={{
                    backgroundColor: `color-mix(in srgb, var(--series-1) ${(alpha * 100).toFixed(1)}%, transparent)`,
                  }}
                >
                  {p >= 0.01 ? (100 * p).toFixed(1) : ""}
                </div>
              );
            })}
          </div>
        </div>
      ))}
      <div className="mt-1 flex items-baseline justify-between text-[10px] text-muted-foreground">
        <span>
          {homeTeam} goals ↓ · {awayTeam} goals →
        </span>
        <span data-testid="tail-mass">P(either side &gt;{max}) = {(100 * tail).toFixed(2)}%</span>
      </div>
    </div>
  );
}
