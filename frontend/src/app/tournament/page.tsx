import { PlannedScreen } from "@/components/PlannedScreen";

export default function TournamentPage() {
  return (
    <PlannedScreen
      title="Tournament"
      phase="Phase 2 (prediction screens)"
      decision="Which bracket paths, group outcomes, and third-place scenarios are mispriced — including joint queries like P(A wins group ∧ B reaches final)."
      needs="The simulator persisting its path draws (backend gap named in ADR-0011)."
    />
  );
}
