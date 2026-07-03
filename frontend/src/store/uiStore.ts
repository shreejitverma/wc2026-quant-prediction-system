/**
 * UI-only client state (ADR-0011): strictly things that are harmlessly lost on
 * refresh. Anything the backend could disagree with belongs in the TanStack
 * Query cache, never here.
 */
import { create } from "zustand";

interface UiState {
  paletteOpen: boolean;
  setPaletteOpen: (open: boolean) => void;
  killDialogOpen: boolean;
  setKillDialogOpen: (open: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  paletteOpen: false,
  setPaletteOpen: (paletteOpen) => set({ paletteOpen }),
  killDialogOpen: false,
  setKillDialogOpen: (killDialogOpen) => set({ killDialogOpen }),
}));
