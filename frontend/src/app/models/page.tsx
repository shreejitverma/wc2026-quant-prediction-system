import { PlannedScreen } from "@/components/PlannedScreen";

export default function ModelsPage() {
  return (
    <PlannedScreen
      title="Model Race"
      phase="Phase 5 (honesty pages)"
      decision="Which model is earning its ensemble weight, per scoring rule and market type — with bootstrap CIs so a lucky week cannot promote a model."
      needs="Backtest runs producing per-model scores into the runs ledger."
    />
  );
}
