/**
 * The edge-state precedence IS the honesty policy for Job 2; these tests pin
 * it. Quarantine beats staleness beats band-overlap beats threshold beats sign.
 */
import { describe, expect, it } from "vitest";
import { edgeState } from "./EdgeBadge";

const base = { edgeAfterFees: 0.05, minEdge: 0.03 };

describe("edgeState precedence", () => {
  it("unconfirmed settlement mapping quarantines regardless of edge size", () => {
    expect(edgeState({ ...base, edgeAfterFees: 0.5, unconfirmedMapping: true }).kind).toBe(
      "quarantined",
    );
  });

  it("stale data blanks the edge even above threshold", () => {
    expect(edgeState({ ...base, stale: true }).kind).toBe("stale");
  });

  it("market inside the model band is NO EDGE regardless of point estimate", () => {
    const s = edgeState({ ...base, edgeAfterFees: 0.2, marketInsideBand: true });
    expect(s.kind).toBe("no-edge");
    expect(s.label).toContain("inside band");
  });

  it("below the stay-flat threshold is NO EDGE, in both directions", () => {
    expect(edgeState({ edgeAfterFees: 0.029, minEdge: 0.03 }).kind).toBe("no-edge");
    expect(edgeState({ edgeAfterFees: -0.029, minEdge: 0.03 }).kind).toBe("no-edge");
  });

  it("signed edge renders with glyph + sign (color never carries meaning alone)", () => {
    const pos = edgeState({ edgeAfterFees: 0.042, minEdge: 0.03 });
    expect(pos.kind).toBe("pos");
    expect(pos.label).toBe("▲ +4.2%");
    const neg = edgeState({ edgeAfterFees: -0.042, minEdge: 0.03 });
    expect(neg.kind).toBe("neg");
    expect(neg.label).toBe("▼ -4.2%");
  });
});
