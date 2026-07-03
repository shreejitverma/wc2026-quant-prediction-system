/**
 * Ladder honesty contract: pulled quotes are legible as PULLED (never
 * silently absent), a stale book dims and screams, and the depth-bar scale
 * is declared on screen.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BookLadder } from "./BookLadder";
import type { ConsoleState } from "@/lib/api";

function consoleState(active: boolean): ConsoleState {
  return {
    ticker: "KX-TEST",
    book_bids: [
      { price: 0.55, size: 620 },
      { price: 0.53, size: 1400 },
    ],
    book_asks: [
      { price: 0.59, size: 350 },
      { price: 0.61, size: 900 },
    ],
    book_as_of: new Date().toISOString(),
    my_quotes: { bid: 0.552, ask: 0.585, size: 200, active },
    quote_inputs: {
      fair_value: 0.578, variance: 0.24, inventory: 120, time_to_settlement_days: 0.25,
      gamma: 0.5, fee_floor: 0.012, widen_factor: 1, news_state: "normal",
      bid: 0.552, ask: 0.585, spread: 0.033, skew: -0.006,
    },
    quoting_status: active ? "active" : "paused",
    fills: [],
  };
}

describe("BookLadder", () => {
  it("shows my quotes with prices when active, and declares the bar scale", () => {
    render(<BookLadder console={consoleState(true)} stale={false} />);
    expect(screen.getByTestId("my-my-ask").textContent).toContain("0.585");
    expect(screen.getByTestId("my-my-bid").textContent).toContain("0.552");
    expect(screen.getByTestId("book-ladder").textContent).toContain("max 1400");
  });

  it("renders PULLED (not absence) when quotes are inactive", () => {
    render(<BookLadder console={consoleState(false)} stale={false} />);
    expect(screen.getByTestId("my-my-ask").textContent).toContain("PULLED");
    expect(screen.getByTestId("my-my-bid").textContent).toContain("PULLED");
  });

  it("screams when stale", () => {
    render(<BookLadder console={consoleState(true)} stale={true} />);
    const el = screen.getByTestId("book-ladder");
    expect(el.dataset.stale).toBe("true");
    expect(el.textContent).toContain("BOOK STALE");
  });
});
