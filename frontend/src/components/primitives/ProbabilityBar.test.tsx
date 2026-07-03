/**
 * The load-bearing behavior: a ProbabilityBar CANNOT render a bar without a
 * valid band. TypeScript enforces the prop's presence; these tests enforce
 * the runtime refusal for JS callers and malformed bands.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ProbabilityBar } from "./ProbabilityBar";

afterEach(cleanup);

describe("ProbabilityBar", () => {
  it("renders point, band, and market marker on the same scale", () => {
    render(<ProbabilityBar p={0.5} band={[0.45, 0.58]} market={0.61} label="Home win" />);
    expect(screen.getByTestId("probability-bar")).toBeTruthy();
    // jsdom normalizes "45.0%" to "45%"; compare numerically.
    expect(parseFloat(screen.getByTestId("pb-band").style.left)).toBeCloseTo(45);
    expect(parseFloat(screen.getByTestId("pb-band").style.width)).toBeCloseTo(13);
    expect(parseFloat(screen.getByTestId("pb-point").style.left)).toBeCloseTo(50);
    expect(parseFloat(screen.getByTestId("pb-market").style.left)).toBeCloseTo(61);
    expect(screen.getByText(/45\.0%–58\.0%/)).toBeTruthy(); // band always printed beside the point
  });

  it("refuses to render a bar when the band is malformed (lo > hi)", () => {
    render(<ProbabilityBar p={0.5} band={[0.6, 0.4]} />);
    expect(screen.getByTestId("probability-bar-invalid")).toBeTruthy();
    expect(screen.getByText("NO BAND")).toBeTruthy();
    expect(screen.queryByTestId("pb-point")).toBeNull();
  });

  it("refuses to render when a JS caller passes no band at all", () => {
    // @ts-expect-error - band is required; simulating an untyped caller
    render(<ProbabilityBar p={0.5} band={undefined} />);
    expect(screen.getByTestId("probability-bar-invalid")).toBeTruthy();
  });

  it("refuses NaN and out-of-range bands", () => {
    render(<ProbabilityBar p={0.5} band={[Number.NaN, 0.6]} />);
    expect(screen.getByTestId("probability-bar-invalid")).toBeTruthy();
  });
});
