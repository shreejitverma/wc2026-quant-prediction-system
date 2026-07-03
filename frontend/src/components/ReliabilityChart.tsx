/**
 * ReliabilityChart (ADR-0016: bespoke, custom SVG): predicted probability vs
 * empirical frequency per decile bin.
 *
 * Honesty rules this component owns:
 *  - every bin wears its count (the strip along the bottom) and its Wilson CI
 *    whisker - a "perfectly calibrated" bin holding 3 samples must look like
 *    what it is;
 *  - empty bins render as gaps, never interpolated across;
 *  - the diagonal is drawn: the eye judges distance-to-ideal, not shape.
 */
import type { CalibrationReport } from "@/lib/api";

const W = 320;
const H = 240;
const PAD = 28;
const STRIP_H = 26;
const PLOT = H - PAD - STRIP_H;

const x = (p: number) => PAD + p * (W - PAD - 8);
const y = (p: number) => 8 + (1 - p) * (PLOT - 8);

export function ReliabilityChart({ report }: { report: CalibrationReport }) {
  const maxN = Math.max(...report.bins.map((b) => b.n), 1);
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full max-w-md"
      role="img"
      aria-label={`Calibration reliability for ${report.model}, n=${report.n_total}`}
      data-testid="reliability-chart"
    >
      {/* axes + diagonal (the ideal) */}
      <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(0)} stroke="var(--border)" />
      <line x1={x(0)} y1={y(0)} x2={x(0)} y2={y(1)} stroke="var(--border)" />
      <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} stroke="var(--muted-foreground)" strokeDasharray="3 3" opacity={0.6} />
      {[0, 0.5, 1].map((t) => (
        <g key={t} className="fill-muted-foreground" fontSize={8}>
          <text x={x(t)} y={y(0) + 10} textAnchor="middle">{(100 * t).toFixed(0)}%</text>
          <text x={x(0) - 4} y={y(t) + 3} textAnchor="end">{(100 * t).toFixed(0)}%</text>
        </g>
      ))}
      {/* bins: CI whisker + point; count strip below */}
      {report.bins.map((b) => {
        const cx = x(b.p_mid);
        return (
          <g key={b.p_mid}>
            {b.n > 0 && (
              <>
                <line x1={cx} y1={y(b.ci_lo)} x2={cx} y2={y(b.ci_hi)} stroke="var(--uncertain)" strokeWidth={2} opacity={0.7} />
                <circle cx={cx} cy={y(b.empirical)} r={3} fill="var(--series-1)" />
              </>
            )}
            <rect
              x={cx - 8}
              y={H - STRIP_H + (STRIP_H - 6) * (1 - b.n / maxN)}
              width={16}
              height={Math.max(0.5, (STRIP_H - 6) * (b.n / maxN))}
              fill="var(--muted-foreground)"
              opacity={0.35}
            />
            <text x={cx} y={H - 1} textAnchor="middle" fontSize={7} className="fill-muted-foreground">
              {b.n}
            </text>
          </g>
        );
      })}
      <text x={x(0.5)} y={H - STRIP_H - 2} textAnchor="middle" fontSize={7} className="fill-muted-foreground">
        predicted → · whiskers = Wilson 95% · strip = bin counts (n={report.n_total})
      </text>
    </svg>
  );
}
