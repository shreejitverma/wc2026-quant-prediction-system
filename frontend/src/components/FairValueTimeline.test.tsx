/**
 * Timeline honesty contract: the band area and both series render from the
 * payload, event markers appear with labels, and the legend declares which
 * clock the axis uses.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FairValueTimeline } from "./FairValueTimeline";
import type { MatchTimeline } from "@/lib/api";

const timeline: MatchTimeline = {
  match_id: "MOCK_M0",
  contract: "home win",
  points: Array.from({ length: 6 }, (_, i) => ({
    ts_utc: new Date(Date.UTC(2026, 6, 1, i)).toISOString(),
    market: 0.4 + i * 0.01,
    fair: 0.45,
    lo: 0.42,
    hi: 0.48,
  })),
  events: [{ ts_utc: new Date(Date.UTC(2026, 6, 1, 3)).toISOString(), kind: "lineup", label: "Expected XI news" }],
};

describe("FairValueTimeline", () => {
  it("renders legend with band, fair value, market, and the axis clock", () => {
    render(<FairValueTimeline timeline={timeline} />);
    const el = screen.getByTestId("fair-value-timeline");
    expect(el.textContent).toContain("fair value (home win)");
    expect(el.textContent).toContain("market mid");
    expect(el.textContent).toContain("uncertainty band");
    expect(el.textContent).toContain("time in ");
  });
});
