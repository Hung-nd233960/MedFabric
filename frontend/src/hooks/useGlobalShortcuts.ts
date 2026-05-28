import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import { useUiStore } from "@/store/uiStore";

const DISABLED_PATHS = ["/change-password"];

export function useGlobalShortcuts() {
  const { pathname } = useLocation();
  const shortcutsOpen = useUiStore((s) => s.shortcutsOpen);
  const setShortcutsOpen = useUiStore((s) => s.setShortcutsOpen);
  const openShortcuts = useUiStore((s) => s.openShortcuts);

  useEffect(() => {
    if (DISABLED_PATHS.includes(pathname)) return;

    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;

      if (e.key === "?") {
        e.preventDefault();
        if (shortcutsOpen) {
          setShortcutsOpen(false);
        } else {
          openShortcuts(pathname === "/label" ? "label" : "general");
        }
        return;
      }

      if (e.key === "/" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        toast("Press ? for keyboard shortcuts", {
          id: "shortcuts-hint",
          duration: 2500,
          position: "bottom-right",
        });
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pathname, shortcutsOpen, setShortcutsOpen, openShortcuts]);
}
