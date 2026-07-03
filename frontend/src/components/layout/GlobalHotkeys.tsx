/**
 * Terminal-wide keyboard entry points. ⌘K opens the palette; ⇧⌘K opens the
 * kill-switch confirmation from ANY screen - one keystroke, per the operating
 * rule that the kill switch is always reachable. Bare digits 1-9 jump to the
 * rail screens in order (guarded: never while typing in an input, and never
 * with a modifier held, so browser tab-switching stays untouched).
 */

import { useEffect } from "react";
import { useNavigate } from "react-router";
import { useUiStore } from "@/store/uiStore";
import { NAV_ITEMS } from "./Sidebar";

function isTypingTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  return el.isContentEditable || el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT";
}

export function GlobalHotkeys() {
  const { setPaletteOpen, setKillDialogOpen } = useUiStore();
  const navigate = useNavigate();

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
        return;
      }
      // Digit navigation: plain 1-9, no modifiers, not while typing.
      if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
      if (isTypingTarget(e.target)) return;
      const idx = e.key >= "1" && e.key <= "9" ? Number(e.key) - 1 : -1;
      const item = idx >= 0 ? NAV_ITEMS[idx] : undefined;
      if (item) {
        e.preventDefault();
        navigate(item.href);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [setPaletteOpen, setKillDialogOpen, navigate]);

  return null;
}
