import { create } from "zustand";

interface UiStore {
  shortcutsOpen: boolean;
  shortcutsDefaultTab: "general" | "label";
  toggleShortcuts: () => void;
  setShortcutsOpen: (v: boolean) => void;
  openShortcuts: (tab: "general" | "label") => void;
}

export const useUiStore = create<UiStore>((set) => ({
  shortcutsOpen: false,
  shortcutsDefaultTab: "general",
  toggleShortcuts: () => set((s) => ({ shortcutsOpen: !s.shortcutsOpen })),
  setShortcutsOpen: (v) => set({ shortcutsOpen: v }),
  openShortcuts: (tab) => set({ shortcutsOpen: true, shortcutsDefaultTab: tab }),
}));
