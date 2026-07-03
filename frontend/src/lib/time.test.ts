import { describe, expect, it } from "vitest";
import { ageSeconds, localWithOffset, utcShort } from "./time";

describe("time discipline", () => {
  it("utcShort renders the UTC clock with an explicit Z", () => {
    expect(utcShort("2026-06-11T18:00:00+00:00")).toBe("18:00Z");
  });

  it("localWithOffset always names its clock (GMT offset present)", () => {
    expect(localWithOffset("2026-06-11T18:00:00+00:00")).toMatch(/GMT/);
  });

  it("ageSeconds measures from the given now and never goes negative", () => {
    const t = "2026-06-11T18:00:00+00:00";
    const now = new Date("2026-06-11T18:02:00+00:00").getTime();
    expect(ageSeconds(t, now)).toBe(120);
    expect(ageSeconds("2099-01-01T00:00:00+00:00", now)).toBe(0);
  });

  it("invalid timestamps are visibly invalid, not silently now", () => {
    expect(utcShort("garbage")).toBe("invalid time");
    expect(ageSeconds("garbage")).toBe(Number.POSITIVE_INFINITY);
  });
});
