/**
 * WCAG 2.x relative luminance and contrast ratio (pure math, no DOM).
 * Used by the design-token contract test: ADR-0013's "WCAG-checked palette"
 * is enforced in CI, not asserted in prose.
 */

function linearize(channel255: number): number {
  const c = channel255 / 255;
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

/** Relative luminance of a #rrggbb hex color. */
export function hexLuminance(hex: string): number {
  const h = hex.replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(h)) throw new Error(`not a #rrggbb hex color: ${hex}`);
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b);
}

/** Relative luminance of a neutral (chroma-0) oklch gray: linear = L^3. */
export function oklchNeutralLuminance(l: number): number {
  return Math.pow(l, 3);
}

export function contrastRatio(lumA: number, lumB: number): number {
  const hi = Math.max(lumA, lumB);
  const lo = Math.min(lumA, lumB);
  return (hi + 0.05) / (lo + 0.05);
}
