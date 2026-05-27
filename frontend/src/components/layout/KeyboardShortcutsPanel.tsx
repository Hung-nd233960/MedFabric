import type { ReactNode } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useUiStore } from "@/store/uiStore";

type Row = { combo: string; desc: string };
type Column = { title: string; rows: Row[] };

const COLUMNS: Column[] = [
  {
    title: "Anywhere",
    rows: [
      { combo: "?", desc: "Open / close this panel" },
      { combo: "/", desc: "Show hint toast" },
    ],
  },
  {
    title: "Dashboard",
    rows: [
      { combo: "I / D / H", desc: "Image Sets / Drafts / History tab" },
      { combo: "↑ / ↓", desc: "Move row highlight" },
      { combo: "Shift+↑ / ↓", desc: "Jump to first / last row" },
      { combo: "Shift+1 … 0", desc: "Jump to 0% … 100% of table" },
      { combo: "Enter", desc: "Select / deselect highlighted row" },
      { combo: "A / R", desc: "Switch to Annotate / Reader mode" },
      { combo: "Shift+A", desc: "Launch selected sets — Annotate" },
      { combo: "Shift+R", desc: "Launch selected sets — Reader" },
      { combo: "Shift+P", desc: "Launch selected sets — Preview" },
      { combo: "Esc", desc: "Clear highlight & deselect" },
    ],
  },
  {
    title: "Label — Annotate Mode",
    rows: [
      { combo: "← / →", desc: "Previous / next image" },
      { combo: "Shift+← / →", desc: "Previous / next set in queue" },
      { combo: "1 / 2 / 3 / 4", desc: "Ischemic / Hemorrhagic / Anomaly / Irrelevant" },
      { combo: "Q", desc: "Toggle Low Quality (Ischemic only)" },
      { combo: "B / C / N", desc: "Region: Basal / Corona / None" },
      { combo: "M", desc: "Toggle Management Board" },
      { combo: "Ctrl+S", desc: "Save draft" },
      { combo: "Ctrl+Enter", desc: "Submit (when ready)" },
      { combo: "Esc", desc: "Close dialog / Management Board" },
    ],
  },
  {
    title: "Label — Reader / Preview",
    rows: [
      { combo: "← / →", desc: "Previous / next image" },
      { combo: "Shift+← / →", desc: "Previous / next set in queue" },
      { combo: "M", desc: "Toggle Management Board" },
      { combo: "Esc", desc: "Close Management Board" },
    ],
  },
];

function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex items-center rounded border border-border bg-muted px-2 py-1 font-mono text-sm text-foreground leading-none whitespace-nowrap shrink-0">
      {children}
    </kbd>
  );
}

export default function KeyboardShortcutsPanel() {
  const { shortcutsOpen, setShortcutsOpen } = useUiStore();

  return (
    <Dialog open={shortcutsOpen} onOpenChange={setShortcutsOpen}>
      <DialogContent className="w-[80vw] h-[80vh] max-w-none flex flex-col">
        <DialogHeader className="shrink-0">
          <DialogTitle className="text-xl">Keyboard Shortcuts</DialogTitle>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto pr-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-10 gap-y-8 pt-2">
            {COLUMNS.map((col) => (
              <div key={col.title} className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground pb-1.5 border-b border-border mb-3">
                  {col.title}
                </p>
                {col.rows.map(({ combo, desc }) => (
                  <div key={combo} className="flex items-start justify-between gap-3 py-1">
                    <span className="text-sm text-muted-foreground leading-snug">{desc}</span>
                    <Kbd>{combo}</Kbd>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
