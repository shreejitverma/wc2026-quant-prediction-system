/**
 * FreshnessDot: staleness as a property of the data, not a corner widget.
 * Fresh data earns NO color (a hollow neutral dot - fresh is the baseline,
 * not an achievement); past maxAge it turns warning amber; past 5x maxAge,
 * critical. Tooltip carries both clocks (UTC + local with offset).
 */

import { useEffect, useState } from "react";
import { ageSeconds, localWithOffset, utcShort } from "@/lib/time";

export function FreshnessDot({ asOf, maxAgeSeconds }: { asOf: string; maxAgeSeconds: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 10_000);
    return () => clearInterval(id);
  }, []);

  const age = ageSeconds(asOf, now);
  const level = age > 5 * maxAgeSeconds ? "dead" : age > maxAgeSeconds ? "stale" : "fresh";
  const cls =
    level === "dead"
      ? "bg-status-critical"
      : level === "stale"
        ? "bg-status-warn"
        : "border border-muted-foreground/60 bg-transparent";

  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${cls}`}
      data-freshness={level}
      title={`as of ${utcShort(asOf)} · ${localWithOffset(asOf)} · age ${Math.round(age)}s (limit ${maxAgeSeconds}s)`}
    />
  );
}
