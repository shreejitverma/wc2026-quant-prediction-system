/**
 * Shell smoke test: the full composition (router + QueryProvider + rail +
 * status strip + routed page) must mount without crashing. This is the test
 * that catches "the terminal is a white screen" before matchday does.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import { NAV_ITEMS } from "./components/layout/Sidebar";

describe("App shell", () => {
  it("mounts the shell with every rail entry", () => {
    render(<App />);
    expect(screen.getByText("WC2026 TERMINAL")).toBeDefined();
    for (const item of NAV_ITEMS) {
      expect(screen.getByRole("link", { name: item.name })).toBeDefined();
    }
  });
});
