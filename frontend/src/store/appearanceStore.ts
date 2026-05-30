import { create } from "zustand";

export type TooltipMode = "all" | "medical" | "functional" | "off";
export type NavMode = "arrow" | "vim" | "both";

export interface UserPreferences {
  dark: boolean;
  tooltip_mode: TooltipMode;
  show_kbd_hints: boolean;
  dashboard_hint_open: boolean;
  nav_mode: NavMode;
}

interface AppearanceState {
  dark: boolean;
  tooltipMode: TooltipMode;
  showKbdHints: boolean;
  dashboardHintOpen: boolean;
  navMode: NavMode;
  setDark: (dark: boolean) => void;
  setTooltipMode: (v: TooltipMode) => void;
  setShowKbdHints: (v: boolean) => void;
  setDashboardHintOpen: (v: boolean) => void;
  setNavMode: (v: NavMode) => void;
  hydrate: (prefs: UserPreferences) => void;
}

function applyTheme(dark: boolean) {
  document.documentElement.classList.toggle("dark", dark);
  localStorage.setItem("theme", dark ? "dark" : "light");
}

// localStorage is used only as a warm-start cache so the correct theme
// is applied before the server preferences arrive (prevents flash).
const initialDark = localStorage.getItem("theme") !== "light";
const initialTooltipMode = (() => {
  const saved = localStorage.getItem("tooltipMode");
  if (saved === "all" || saved === "medical" || saved === "functional" || saved === "off") return saved as TooltipMode;
  return localStorage.getItem("tooltipsEnabled") === "false" ? "off" as TooltipMode : "all" as TooltipMode;
})();
const initialShowKbdHints = localStorage.getItem("showKbdHints") !== "false";
const initialDashboardHintOpen = localStorage.getItem("mf3-dashboard-hint") !== "closed";
const initialNavMode = ((): NavMode => {
  const v = localStorage.getItem("navMode");
  return v === "vim" || v === "both" ? v : "arrow";
})();

applyTheme(initialDark);

export const useAppearanceStore = create<AppearanceState>()((set) => ({
  dark: initialDark,
  tooltipMode: initialTooltipMode,
  showKbdHints: initialShowKbdHints,
  dashboardHintOpen: initialDashboardHintOpen,
  navMode: initialNavMode,

  setDark: (dark) => {
    applyTheme(dark);
    set({ dark });
  },
  setTooltipMode: (tooltipMode) => {
    localStorage.setItem("tooltipMode", tooltipMode);
    set({ tooltipMode });
  },
  setShowKbdHints: (showKbdHints) => {
    localStorage.setItem("showKbdHints", showKbdHints ? "true" : "false");
    set({ showKbdHints });
  },
  setDashboardHintOpen: (dashboardHintOpen) => {
    localStorage.setItem("mf3-dashboard-hint", dashboardHintOpen ? "open" : "closed");
    set({ dashboardHintOpen });
  },
  setNavMode: (navMode) => {
    localStorage.setItem("navMode", navMode);
    set({ navMode });
  },

  hydrate: (prefs) => {
    applyTheme(prefs.dark);
    localStorage.setItem("tooltipMode", prefs.tooltip_mode);
    localStorage.setItem("showKbdHints", prefs.show_kbd_hints ? "true" : "false");
    localStorage.setItem("mf3-dashboard-hint", prefs.dashboard_hint_open ? "open" : "closed");
    localStorage.setItem("navMode", prefs.nav_mode);
    set({
      dark: prefs.dark,
      tooltipMode: prefs.tooltip_mode,
      showKbdHints: prefs.show_kbd_hints,
      dashboardHintOpen: prefs.dashboard_hint_open,
      navMode: prefs.nav_mode,
    });
  },
}));
