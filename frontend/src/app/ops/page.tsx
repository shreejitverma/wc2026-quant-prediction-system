import { PlannedScreen } from "@/components/PlannedScreen";

export default function OpsPage() {
  return (
    <PlannedScreen
      title="Ops"
      phase="Phase 6 (ops, alerts, matchday)"
      decision="Is every data source fresh enough to trust the quotes — and when model-vs-market divergence spikes, is it edge or is my data stale."
      needs="Ingestion writing per-source freshness snapshots."
    />
  );
}
