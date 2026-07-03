/**
 * Time discipline (mirrors the backend's UTC-only rule): everything arrives as
 * UTC ISO-8601; display is the operator's local zone WITH the offset spelled
 * out. Six venues across four time zones means a bare "18:00" is a trap -
 * every rendered time says which clock it is on.
 */

export function localWithOffset(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "invalid time";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "shortOffset",
  }).format(d);
}

export function utcShort(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "invalid time";
  return `${d.toISOString().slice(11, 16)}Z`;
}

export function ageSeconds(iso: string, nowMs: number = Date.now()): number {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return Number.POSITIVE_INFINITY;
  return Math.max(0, (nowMs - t) / 1000);
}
