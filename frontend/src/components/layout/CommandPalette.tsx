/**
 * ⌘K jump-to-anything. Navigation is the enemy during a live window; the
 * palette is the primary way to move (rail clicks are the fallback). Matches
 * load from the server when the palette opens; they are labeled [MOCK] as long
 * as their provenance says so - the palette obeys the same honesty contract
 * as any screen.
 */

import { useNavigate } from "react-router";
import { Command } from "cmdk";
import { useQuery } from "@tanstack/react-query";
import { fetchMatches } from "@/lib/api";
import { useUiStore } from "@/store/uiStore";
import { NAV_ITEMS } from "./Sidebar";

export function CommandPalette() {
  const navigate = useNavigate();
  const { paletteOpen, setPaletteOpen, setKillDialogOpen } = useUiStore();

  const matches = useQuery({
    queryKey: ["matches"],
    queryFn: fetchMatches,
    enabled: paletteOpen,
  });
  const mock = matches.data?.provenance.source === "mock";

  const go = (href: string) => {
    setPaletteOpen(false);
    navigate(href);
  };

  return (
    <Command.Dialog
      open={paletteOpen}
      onOpenChange={setPaletteOpen}
      label="Command palette"
      className="fixed left-1/2 top-24 z-50 w-full max-w-lg -translate-x-1/2 overflow-hidden rounded-lg border border-border bg-popover shadow-2xl"
    >
      <Command.Input
        placeholder="Jump to screen, match, contract…"
        className="w-full border-b border-border bg-transparent px-4 py-3 text-sm outline-none placeholder:text-muted-foreground"
      />
      <Command.List className="max-h-80 overflow-auto p-2">
        <Command.Empty className="px-3 py-6 text-center text-sm text-muted-foreground">
          No results — definitive, not an error.
        </Command.Empty>

        <Command.Group
          heading="Screens"
          className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:text-muted-foreground"
        >
          {NAV_ITEMS.map((item) => (
            <Command.Item
              key={item.href}
              value={`screen ${item.name}`}
              onSelect={() => go(item.href)}
              className="cursor-pointer rounded px-3 py-2 text-sm aria-selected:bg-accent"
            >
              {item.name}
            </Command.Item>
          ))}
        </Command.Group>

        <Command.Group
          heading="Matches"
          className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:text-muted-foreground"
        >
          {(matches.data?.data ?? []).map((m) => (
            <Command.Item
              key={m.match_id}
              value={`match ${m.home_team} ${m.away_team}`}
              onSelect={() => go(`/matches/${m.match_id}`)}
              className="cursor-pointer rounded px-3 py-2 text-sm aria-selected:bg-accent"
            >
              {m.home_team} vs {m.away_team}
              {mock && <span className="ml-2 text-[10px] text-status-warn">[MOCK]</span>}
            </Command.Item>
          ))}
        </Command.Group>

        <Command.Group
          heading="Actions"
          className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:text-muted-foreground"
        >
          <Command.Item
            value="action kill switch"
            onSelect={() => {
              setPaletteOpen(false);
              setKillDialogOpen(true);
            }}
            className="cursor-pointer rounded px-3 py-2 text-sm text-status-critical aria-selected:bg-accent"
          >
            Kill switch…
          </Command.Item>
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}
