import { PlannedScreen } from "@/components/PlannedScreen";

export default function ConsolePage() {
  return (
    <PlannedScreen
      title="MM Console"
      phase="Phase 4 (the sharp end)"
      decision="Whether to keep, widen, pull, or resize quotes on each contract given the book, inventory, and news state."
      needs="Fenced command endpoints (pause/resume/kill) and the paper execution loop."
    />
  );
}
