import { create } from "zustand";

interface UiStore {
  shortcutsOpen: boolean;
  toggleShortcuts: () => void;
  setShortcutsOpen: (v: boolean) => void;
}

export const useUiStore = create<UiStore>((set) => ({
  shortcutsOpen: false,
  toggleShortcuts: () => set((s) => ({ shortcutsOpen: !s.shortcutsOpen })),
  setShortcutsOpen: (v) => set({ shortcutsOpen: v }),
}));
