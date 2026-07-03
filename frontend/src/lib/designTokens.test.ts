/**
 * Design-token contract (ADR-0013): every token that is worn by TEXT must meet
 * WCAG AA 4.5:1 on BOTH dark surfaces (page background and card), because the
 * terminal renders 10-12px text in these colors. Series tokens are chart ink
 * (marks/lines with direct labels in foreground color), so they carry the
 * 3:1 graphical-object floor instead.
 *
 * The test parses globals.css, so the stylesheet stays the single source of
 * truth - a palette edit that breaks contrast fails CI before it ships.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { contrastRatio, hexLuminance, oklchNeutralLuminance } from "./contrast";

const css = readFileSync(join(__dirname, "..", "globals.css"), "utf8");

function token(name: string): string {
  const m = css.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!m) throw new Error(`token --${name} not found as hex in globals.css`);
  return m[1];
}

// Dark surfaces from the .dark theme: neutral oklch grays.
const BG = oklchNeutralLuminance(0.145); // --background ≈ #0a0a0a
const CARD = oklchNeutralLuminance(0.205); // --card ≈ #171717

const TEXT_TOKENS = [
  "edge-pos",
  "edge-neg",
  "uncertain",
  "status-good",
  "status-warn",
  "status-serious",
  "status-critical",
];

const SERIES_TOKENS = ["series-1", "series-2", "series-3", "series-4", "series-5", "series-6", "series-7", "series-8"];

describe("design token contrast (WCAG AA)", () => {
  it.each(TEXT_TOKENS)("--%s ≥ 4.5:1 on background and card", (name) => {
    const lum = hexLuminance(token(name));
    expect(contrastRatio(lum, BG)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(lum, CARD)).toBeGreaterThanOrEqual(4.5);
  });

  it.each(SERIES_TOKENS)("--%s ≥ 3:1 (graphical objects) on background", (name) => {
    const lum = hexLuminance(token(name));
    expect(contrastRatio(lum, BG)).toBeGreaterThanOrEqual(3);
  });

  it("muted-foreground (oklch 0.708 neutral) ≥ 4.5:1 on both surfaces", () => {
    const lum = oklchNeutralLuminance(0.708);
    expect(contrastRatio(lum, BG)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(lum, CARD)).toBeGreaterThanOrEqual(4.5);
  });
});
