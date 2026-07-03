/**
 * Honest placeholder for a screen that is planned but not built. States the
 * decision the screen will support (the rule: no screen ships without naming
 * its decision) and which phase delivers it - instead of a 404 or, worse, a
 * mocked-up page that looks operational.
 */
export function PlannedScreen({
  title,
  phase,
  decision,
  needs,
}: {
  title: string;
  phase: string;
  decision: string;
  needs?: string;
}) {
  return (
    <div className="mx-auto max-w-xl space-y-4 pt-16 text-center">
      <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
      <p className="text-sm text-muted-foreground">
        Not built yet — arrives in <span className="font-semibold text-foreground">{phase}</span>.
      </p>
      <div className="rounded-lg border border-border bg-card p-4 text-left text-sm">
        <p>
          <span className="text-muted-foreground">Decision this screen supports: </span>
          {decision}
        </p>
        {needs && (
          <p className="mt-2">
            <span className="text-muted-foreground">Blocked on: </span>
            {needs}
          </p>
        )}
      </div>
    </div>
  );
}
