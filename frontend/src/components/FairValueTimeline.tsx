/**
 * FairValueTimeline (ADR-0013): market price vs model fair value over time,
 * with the uncertainty band and event markers on one chart.
 *
 * Honesty rules this component owns:
 *  - the band is a translucent NEUTRAL area (--uncertain), never dashed lines
 *    in the point-estimate's hue (the rejected alternative in ADR-0013);
 *  - the y-axis is the full probability scale 0-1 by default - a zoomed axis
 *    is how a 2pp wiggle is made to look like a regime change;
 *  - event markers (lineup, news, goals elsewhere) are labeled reference
 *    lines: price moves must be attributable to information arrival;
 *  - x ticks are operator-local; the axis label states the offset once.
 */
import {
  Area,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MatchTimeline } from "@/lib/api";

const tickLocal = (iso: string) =>
  new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));

function localOffsetLabel(): string {
  const part = new Intl.DateTimeFormat(undefined, { timeZoneName: "shortOffset" })
    .formatToParts(new Date())
    .find((p) => p.type === "timeZoneName");
  return part?.value ?? "local";
}

export function FairValueTimeline({ timeline }: { timeline: MatchTimeline }) {
  const data = timeline.points.map((p) => ({
    ts: p.ts_utc,
    market: p.market,
    fair: p.fair,
    band: [p.lo, p.hi] as [number, number],
  }));

  return (
    <div className="h-72 w-full" data-testid="fair-value-timeline">
      <div className="mb-1 flex items-center gap-4 text-[10px] text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-[3px] w-4 rounded bg-series-1" /> fair value ({timeline.contract})
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-[3px] w-4 rounded bg-foreground/80" /> market mid
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block h-2.5 w-4 rounded bg-uncertain/35" /> uncertainty band
        </span>
        <span className="ml-auto">time in {localOffsetLabel()}</span>
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 12, right: 8, bottom: 4, left: 0 }}>
          <XAxis
            dataKey="ts"
            tickFormatter={tickLocal}
            stroke="var(--muted-foreground)"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            minTickGap={48}
          />
          <YAxis
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickFormatter={(v: number) => `${(100 * v).toFixed(0)}%`}
            stroke="var(--muted-foreground)"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            width={36}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--popover)",
              borderColor: "var(--border)",
              fontSize: 11,
            }}
            labelFormatter={(iso) => `${tickLocal(String(iso))} (${localOffsetLabel()})`}
            formatter={(value, name) => {
              if (name === "band" && Array.isArray(value)) {
                const [lo, hi] = value as [number, number];
                return [`${(100 * lo).toFixed(1)}–${(100 * hi).toFixed(1)}%`, "band"];
              }
              return [`${(100 * Number(value)).toFixed(1)}%`, String(name)];
            }}
          />
          <Area
            dataKey="band"
            stroke="none"
            fill="var(--uncertain)"
            fillOpacity={0.28}
            isAnimationActive={false}
          />
          <Line
            dataKey="fair"
            stroke="var(--series-1)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            dataKey="market"
            stroke="var(--foreground)"
            strokeOpacity={0.85}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          {timeline.events.map((ev) => (
            <ReferenceLine
              key={`${ev.ts_utc}-${ev.kind}`}
              x={ev.ts_utc}
              stroke="var(--muted-foreground)"
              strokeDasharray="4 3"
              label={{
                value: ev.label,
                position: "insideTopLeft",
                fontSize: 9,
                fill: "var(--muted-foreground)",
              }}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
