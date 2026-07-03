import { PlannedScreen } from "@/components/PlannedScreen";

export default function PerformancePage() {
  return (
    <PlannedScreen
      title="Performance"
      phase="Phase 5 (honesty pages)"
      decision="Is the system beating the de-vigged market (CLV, calibration, proper scores) by enough to justify size — with sample sizes and CIs on every number."
      needs="CLV capture at entry/close in the execution path (backend gap named in ADR-0011)."
    />
  );
}
