/**
 * Waterfall honesty contract: renders a payload whose steps sum to the fair
 * value; REFUSES visibly when they do not. A decomposition that fails to
 * account for the whole number must never be drawn as if it did.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FairValueWaterfall } from "./FairValueWaterfall";
import type { FairValueStep } from "@/lib/api";

const good: FairValueStep[] = [
  { label: "model_probability", delta: 0.6, value_after: 0.6 },
  { label: "fees", delta: -0.012, value_after: 0.588 },
  { label: "timing_lockup", delta: -0.004, value_after: 0.584 },
  { label: "resolution_risk", delta: -0.006, value_after: 0.578 },
];

describe("FairValueWaterfall", () => {
  it("renders all steps plus the fair-value row", () => {
    render(<FairValueWaterfall steps={good} />);
    const el = screen.getByTestId("fair-value-waterfall");
    for (const text of ["model probability", "fees", "timing / lockup", "resolution risk", "fair value"]) {
      expect(el.textContent).toContain(text);
    }
    expect(el.textContent).toContain("0.578");
  });

  it("refuses to draw an inconsistent decomposition", () => {
    const bad = good.map((s, i) => (i === 3 ? { ...s, value_after: 0.9 } : s));
    render(<FairValueWaterfall steps={bad} />);
    expect(screen.getByTestId("waterfall-invalid").textContent).toContain("Refusing to draw");
    expect(screen.queryByTestId("fair-value-waterfall")).toBeNull();
  });
});
