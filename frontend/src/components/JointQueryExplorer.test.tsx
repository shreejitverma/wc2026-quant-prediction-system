/**
 * Explorer honesty contract: a joint-probability answer never renders without
 * its CI, its sample size (n and hits), and the naive product beside it - the
 * three numbers that stop a counted 3.2% from being read as gospel.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { JointQueryExplorer } from "./JointQueryExplorer";

vi.mock("@/lib/api", () => ({
  postSimQuery: vi.fn(async () => ({
    data: {
      events: [
        { team: "Brazil", outcome: "wins_group" },
        { team: "France", outcome: "reaches_final" },
      ],
      p: { p: 0.032, lo: 0.029, hi: 0.035 },
      n_draws: 20000,
      n_hits: 640,
      independent_product: 0.021,
      dependence_ratio: 1.52,
    },
    provenance: { source: "mock", generated_at: "", data_as_of: null, run_id: null, git_commit: null, config_hash: "x" },
  })),
}));

function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("JointQueryExplorer", () => {
  it("shows CI, sample size, and the naive product with every answer", async () => {
    renderWithQuery(<JointQueryExplorer teams={["Brazil", "France"]} />);
    fireEvent.click(screen.getByTestId("run-query"));
    const result = await screen.findByTestId("query-result");
    expect(result.textContent).toContain("3.20%");
    expect(result.textContent).toContain("[2.90%–3.50%]");
    expect(result.textContent).toContain("640");
    expect(result.textContent).toContain("20,000");
    expect(result.textContent).toContain("2.10%"); // naive product
    expect(result.textContent).toContain("×1.52"); // dependence ratio
  });
});
