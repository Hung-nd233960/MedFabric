import { useEffect, useState, type ReactNode } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useUiStore } from "@/store/uiStore";
import { cn } from "@/lib/utils";

type Row = { combo: string; desc: string };
type Column = { title: string; rows: Row[]; tab: "general" | "label" };

const COLUMNS: Column[] = [
  {
    tab: "general",
    title: "Anywhere",
    rows: [
      { combo: "?", desc: "Open / close this panel" },
      { combo: "/", desc: "Show hint toast" },
    ],
  },
  {
    tab: "general",
    title: "Dashboard",
    rows: [
      { combo: "Tab / Shift+Tab", desc: "Cycle tabs forward / backward" },
      { combo: "V", desc: "Enter / exit Visual selection mode" },
      { combo: "I / D / H", desc: "Jump to Image Sets / Drafts / History" },
      { combo: "Ctrl+A", desc: "Select / deselect all in current tab" },
      { combo: "↑ / ↓", desc: "Move row highlight" },
      { combo: "Shift+↑ / ↓", desc: "Jump to first / last row" },
      { combo: "Shift+1 … 0", desc: "Jump to 0% … 100% of table" },
      { combo: "Enter / Space", desc: "Select / deselect highlighted row" },
      { combo: "A / R", desc: "Switch to Annotate / Reader mode" },
      { combo: "Shift+A", desc: "Launch selected sets — Annotate" },
      { combo: "Shift+R", desc: "Launch selected sets — Reader" },
      { combo: "Shift+P", desc: "Launch selected sets — Preview" },
      { combo: "Del / Shift+D", desc: "Delete selected drafts (Drafts tab)" },
      { combo: "Esc", desc: "Clear highlight & deselect" },
    ],
  },
  {
    tab: "label",
    title: "Label — Annotate Mode",
    rows: [
      { combo: "← / →", desc: "Previous / next image" },
      { combo: "Shift+← / →", desc: "Previous / next set in queue" },
      { combo: "Shift+1/2/3/4", desc: "Ischemic / Hemorrhagic / Anomaly / Irrelevant" },
      { combo: "Shift+Q", desc: "Toggle Low Quality (Ischemic only)" },
      { combo: "Shift+B / C / N", desc: "Region: Basal / Corona / None" },
      { combo: "N", desc: "Focus Image Set Notes" },
      { combo: "J", desc: "Jump to image number input" },
      { combo: "Shift+J", desc: "Jump to set number input" },
      { combo: "W", desc: "Jump to WL input" },
      { combo: "Shift+W", desc: "Reset windowing" },
      { combo: "Shift+Tab", desc: "Cycle Image Set Evaluation tabs" },
      { combo: "M", desc: "Toggle Management Board" },
      { combo: "Ctrl+S", desc: "Save draft" },
      { combo: "Ctrl+Enter", desc: "Submit (when ready)" },
      { combo: "Shift+Del", desc: "Open Reset All Annotations prompt" },
      { combo: "Y / N", desc: "Confirm / cancel reset prompt" },
      { combo: "Shift+Esc", desc: "Return to Dashboard" },
      { combo: "Esc", desc: "Close dialog / Management Board" },
    ],
  },
  {
    tab: "label",
    title: "Zone Mode",
    rows: [
      { combo: "Z", desc: "Enter Zone Mode (Basal/Corona image)" },
      { combo: "V", desc: "Enter Zone Mode directly in Visual" },
      { combo: "Shift+B / C", desc: "Re-press current zone to enter Zone Mode" },
      { combo: "1 / 2 / 3", desc: "Damaged / OK / Not Visible → advance" },
      { combo: "V", desc: "Enter / exit Visual selection" },
      { combo: "Ctrl+A", desc: "Select all cells" },
      { combo: "Shift+1 … N", desc: "Select entire row N (both sides)" },
      { combo: "<", desc: "Select all Left column" },
      { combo: ">", desc: "Select all Right column" },
      { combo: "↑ / ↓", desc: "Move row" },
      { combo: "← / →", desc: "Switch column (Left / Right)" },
      { combo: "Shift+↑ / ↓", desc: "Jump to first / last row in column" },
      { combo: "N", desc: "Focus slice notes (Zone Mode stays on)" },
      { combo: "Z / Esc", desc: "Exit Zone Mode" },
    ],
  },
  {
    tab: "label",
    title: "Label — Reader / Preview",
    rows: [
      { combo: "← / →", desc: "Previous / next image" },
      { combo: "Shift+← / →", desc: "Previous / next set in queue" },
      { combo: "J / Shift+J", desc: "Jump to image / set number input" },
      { combo: "W / Shift+W", desc: "Jump to WL input / Reset windowing" },
      { combo: "Shift+Tab", desc: "Cycle Image Set Evaluation tabs" },
      { combo: "M", desc: "Toggle Management Board" },
      { combo: "Shift+Esc", desc: "Return to Dashboard" },
      { combo: "Esc", desc: "Close Management Board" },
    ],
  },
  {
    tab: "label",
    title: "Management Board",
    rows: [
      { combo: "↑ / ↓", desc: "Navigate rows in active panel" },
      { combo: "← / →", desc: "Switch active panel" },
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
  const { shortcutsOpen, shortcutsDefaultTab, setShortcutsOpen } = useUiStore();
  const [activeTab, setActiveTab] = useState<"general" | "label">(shortcutsDefaultTab);

  // Sync active tab whenever the dialog opens
  useEffect(() => {
    if (shortcutsOpen) setActiveTab(shortcutsDefaultTab);
  }, [shortcutsOpen, shortcutsDefaultTab]);

  const visibleColumns = COLUMNS.filter((c) => c.tab === activeTab);

  return (
    <Dialog open={shortcutsOpen} onOpenChange={setShortcutsOpen}>
      <DialogContent
        className="w-[80vw] h-[80vh] max-w-none flex flex-col"
        onKeyDown={(e) => {
          // Don't intercept if focus is inside an input/textarea
          const tag = (e.target as HTMLElement).tagName;
          if (tag === "INPUT" || tag === "TEXTAREA") return;

          if (e.key === "Tab") {
            e.preventDefault();
            setActiveTab((t) => (t === "general" ? "label" : "general"));
          } else if (e.key.toUpperCase() === "G" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            setActiveTab("general");
          } else if (e.key.toUpperCase() === "L" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            setActiveTab("label");
          }
        }}
      >
        <DialogHeader className="shrink-0">
          <DialogTitle className="text-xl">Keyboard Shortcuts</DialogTitle>
        </DialogHeader>

        {/* Tab bar */}
        <div className="flex gap-1 shrink-0 border-b border-border pb-2 mb-1">
          {(["general", "label"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-1.5 rounded-md text-sm font-medium transition-colors",
                activeTab === tab
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              {tab === "general" ? "General" : "Label"}
              <span className="ml-2 font-mono text-xs opacity-50">{tab === "general" ? "G" : "L"}</span>
            </button>
          ))}
          <span className="ml-auto self-center text-xs text-muted-foreground/50 font-mono pr-1">Tab to switch</span>
        </div>

        <div className="flex-1 overflow-y-auto pr-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-10 gap-y-8 pt-2">
            {visibleColumns.map((col) => (
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
