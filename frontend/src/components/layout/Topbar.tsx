"use client";

import { Bell, Search } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { fetchHealth, type Envelope, type HealthData } from "@/lib/api";
import { useTopic, useWsStatus } from "@/lib/wsHooks";
import { FreshnessDot } from "@/components/primitives/FreshnessDot";
import { ConfirmTyped } from "@/components/primitives/ConfirmTyped";
import { useUiStore } from "@/store/uiStore";

/**
 * Global status strip. The mode badge is the paper/live fence made visible and
 * must reflect the backend's config, never a hardcoded string. Three states,
 * none mistakable for another: PAPER (neutral), LIVE (red), API DOWN (red -
 * when the truth is unknowable, say so instead of guessing). Health arrives by
 * REST poll AND by WS push into the same Query cache key; the WS dot shows
 * which transport is alive.
 */
export function Topbar() {
  const queryClient = useQueryClient();
  const { setPaletteOpen, killDialogOpen, setKillDialogOpen } = useUiStore();

  const health = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000, // REST fallback; WS push is the primary channel
    retry: 1,
  });
  useTopic<Envelope<HealthData>>("health", (msg) => {
    queryClient.setQueryData(["health"], msg.data);
  });
  const wsStatus = useWsStatus();

  const h = health.data?.data;
  const asOf = health.data?.provenance.data_as_of;

  return (
    <div className="flex h-14 items-center border-b px-4 lg:px-6 bg-background">
      <div className="flex flex-1 items-center space-x-4">
        <button
          onClick={() => setPaletteOpen(true)}
          className="relative flex h-9 w-full max-w-sm items-center rounded-md border border-input bg-transparent px-3 text-sm text-muted-foreground shadow-sm hover:bg-accent/50"
        >
          <Search className="mr-2 h-4 w-4" />
          Command palette…
          <kbd className="ml-auto rounded border border-border px-1.5 font-mono text-[10px]">⌘K</kbd>
        </button>
      </div>
      <div className="flex items-center space-x-3">
        <span
          className="font-mono text-[10px] uppercase text-muted-foreground"
          data-ws-status={wsStatus}
          title="WebSocket feed status"
        >
          {wsStatus === "open" ? "ws ●" : wsStatus === "connecting" ? "ws …" : "ws ○"}
        </span>

        {health.isError || !h ? (
          <Badge
            variant="outline"
            className="font-mono text-xs text-status-critical border-status-critical/40 bg-status-critical/10"
          >
            {health.isLoading ? "…" : "● API DOWN"}
          </Badge>
        ) : (
          <Badge
            variant="outline"
            className={
              h.mode === "live"
                ? "font-mono text-xs text-status-critical border-status-critical/40 bg-status-critical/10"
                : "font-mono text-xs text-muted-foreground border-border"
            }
          >
            ● {h.mode.toUpperCase()}
          </Badge>
        )}

        {h && asOf && <FreshnessDot asOf={asOf} maxAgeSeconds={h.max_data_staleness_seconds} />}
        <span className="text-xs font-mono text-muted-foreground">
          {h == null
            ? "no data"
            : h.ledger_staleness_seconds == null
              ? "ledger empty"
              : `ledger ${Math.round(h.ledger_staleness_seconds)}s`}
        </span>

        <button
          className="relative p-2 hover:bg-accent rounded-full transition-colors"
          title="Alert center arrives in Phase 6; no alerts exist yet."
        >
          <Bell className="h-4 w-4" />
        </button>

        <button
          onClick={() => setKillDialogOpen(true)}
          title="Kill switch (⇧⌘K)"
          className="rounded-md border border-status-critical/50 px-3 py-1.5 font-mono text-xs font-bold text-status-critical hover:bg-status-critical/10"
        >
          KILL
        </button>
      </div>

      <ConfirmTyped
        open={killDialogOpen}
        onOpenChange={setKillDialogOpen}
        title="Kill switch"
        description="Pull all quotes on all venues and halt the quoting engine. This writes a kill command to the ledger via the backend."
        phrase="KILL ALL QUOTING"
        confirmLabel="Kill"
        disabledReason="Not wired yet: the fenced command endpoints land in Phase 4 with the MM console. Nothing is quoting today (paper mode, no execution loop), so there is nothing to kill."
      />
    </div>
  );
}
