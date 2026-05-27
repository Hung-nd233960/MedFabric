import { create } from "zustand";

export type TooltipMode = "all" | "medical" | "functional" | "off";

interface AppearanceState {
  dark: boolean;
  tooltipMode: TooltipMode;
  setDark: (dark: boolean) => void;
  setTooltipMode: (v: TooltipMode) => void;
}

function applyTheme(dark: boolean) {
  document.documentElement.classList.toggle("dark", dark);
  localStorage.setItem("theme", dark ? "dark" : "light");
}

function getInitialTooltipMode(): TooltipMode {
  const saved = localStorage.getItem("tooltipMode");
  if (saved === "all" || saved === "medical" || saved === "functional" || saved === "off") return saved;
  // Migrate from old boolean flag
  return localStorage.getItem("tooltipsEnabled") === "false" ? "off" : "all";
}

const initialDark = localStorage.getItem("theme") !== "light";
applyTheme(initialDark);

export const useAppearanceStore = create<AppearanceState>()((set) => ({
  dark: initialDark,
  tooltipMode: getInitialTooltipMode(),
  setDark: (dark) => {
    applyTheme(dark);
    set({ dark });
  },
  setTooltipMode: (tooltipMode) => {
    localStorage.setItem("tooltipMode", tooltipMode);
    set({ tooltipMode });
  },
}));
