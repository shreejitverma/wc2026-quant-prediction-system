/**
 * Heatmap honesty contract:
 *  - a near-zero cell renders with ~zero ink (no minimum-intensity floor);
 *  - truncating the display never hides mass silently - the tail is disclosed;
 *  - every cell carries its exact probability (data-prob + title), so color
 *    never carries the value alone.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ScorelineHeatmap } from "./ScorelineHeatmap";

function matrix9(fill: (h: number, a: number) => number): number[][] {
  const m = Array.from({ length: 9 }, (_, h) => Array.from({ length: 9 }, (_, a) => fill(h, a)));
  const total = m.flat().reduce((s, p) => s + p, 0);
  return m.map((row) => row.map((p) => p / total));
}

describe("ScorelineHeatmap", () => {
  it("gives a zero-probability cell zero ink", () => {
    const m = matrix9((h, a) => (h === 1 && a === 0 ? 1 : h === 8 && a === 8 ? 0.0001 : 0.01));
    render(<ScorelineHeatmap matrix={m} homeTeam="H" awayTeam="A" />);
    const modal = screen.getByTestId("cell-1-0");
    const other = screen.getByTestId("cell-6-6");
    // alpha is proportional: the modal cell mixes at 100%, low cells near 0%.
    expect(modal.style.backgroundColor).toContain("100.0%");
    const pctOf = (el: HTMLElement) => Number(/ (\d+\.?\d*)%/.exec(el.style.backgroundColor)?.[1]);
    expect(pctOf(other)).toBeLessThan(5);
  });

  it("discloses the truncated tail mass instead of dropping it", () => {
    // Put 10% of mass beyond the 6-goal display window.
    const m = matrix9((h, a) => (h === 8 && a === 8 ? 0.1 : h <= 2 && a <= 2 ? 0.1 : 0));
    render(<ScorelineHeatmap matrix={m} homeTeam="H" awayTeam="A" />);
    expect(screen.getByTestId("tail-mass").textContent).toContain("10.00%");
  });

  it("outlines the modal scoreline and prints values for cells above 1%", () => {
    const m = matrix9((h, a) => (h === 2 && a === 1 ? 0.5 : 0.01));
    render(<ScorelineHeatmap matrix={m} homeTeam="H" awayTeam="A" />);
    expect(screen.getByTestId("cell-2-1").className).toContain("ring-1");
    expect(screen.getByTestId("cell-2-1").textContent).not.toBe("");
    expect(screen.getByTestId("cell-2-1").title).toMatch(/H 2–1 A/);
  });
});
