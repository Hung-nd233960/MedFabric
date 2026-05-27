import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { toast } from "sonner";
import { useUiStore } from "@/store/uiStore";

const DISABLED_PATHS = ["/change-password"];

export function useGlobalShortcuts() {
  const { pathname } = useLocation();
  const toggleShortcuts = useUiStore((s) => s.toggleShortcuts);

  useEffect(() => {
    if (DISABLED_PATHS.includes(pathname)) return;

    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;

      if (e.key === "?") {
        e.preventDefault();
        toggleShortcuts();
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
  }, [pathname, toggleShortcuts]);
}
