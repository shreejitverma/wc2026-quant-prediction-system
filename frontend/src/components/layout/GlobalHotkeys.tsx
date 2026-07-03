/**
 * Terminal-wide keyboard entry points. ⌘K opens the palette; ⇧⌘K opens the
 * kill-switch confirmation from ANY screen - one keystroke, per the operating
 * rule that the kill switch is always reachable.
 */

import { useEffect } from "react";
import { useUiStore } from "@/store/uiStore";

export function GlobalHotkeys() {
  const { setPaletteOpen, setKillDialogOpen } = useUiStore();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (e.shiftKey) {
          setPaletteOpen(false); // kill dialog always stands alone
          setKillDialogOpen(true);
        } else {
          setPaletteOpen(true);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setPaletteOpen, setKillDialogOpen]);

  return null;
}
