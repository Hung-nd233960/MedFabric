import { useEffect, useState, type ReactNode } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useUiStore } from "@/store/uiStore";
import { useAppearanceStore, type NavMode } from "@/store/appearanceStore";
import { navLabel } from "@/lib/navKeys";
import { cn } from "@/lib/utils";

// ── Data ─────────────────────────────────────────────────────────────────────

type Row = { combo: string; desc: string };
type Category = { title: string; rows: Row[]; tab: "general" | "label" };

function buildCategories(nm: NavMode): Category[] {
  const L = (dir: Parameters<typeof navLabel>[0]) => navLabel(dir, nm);
  return [
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
        { combo: "Tab / Shift+Tab",                          desc: "Cycle tabs forward / backward" },
        { combo: "V",                                        desc: "Enter / exit Visual selection mode" },
        { combo: "1 / 2 / 3",                               desc: "Jump to Image Sets / Drafts / History" },
        { combo: "Ctrl+A",                                   desc: "Select / deselect all in current tab" },
        { combo: `${L("up")} / ${L("down")}`,                desc: "Move row highlight" },
        { combo: `${L("shiftUp")} / ${L("shiftDown")}`,      desc: "Jump to first / last row" },
        { combo: "Shift+1 … 0",                              desc: "Jump to 0% … 100% of table" },
        { combo: "Enter / Space",                            desc: "Select / deselect highlighted row" },
        { combo: "A / R",                                    desc: "Switch to Annotate / Reader mode" },
        { combo: "Shift+A",                                  desc: "Launch selected sets — Annotate" },
        { combo: "Shift+R",                                  desc: "Launch selected sets — Reader" },
        { combo: "Shift+P",                                  desc: "Launch selected sets — Preview" },
        { combo: "Shift+Q",                                  desc: "Jump to first not-done set (nothing selected)" },
        { combo: "Del / Shift+D",                            desc: "Delete selected drafts (Drafts tab)" },
        { combo: "Esc",                                      desc: "Clear highlight & deselect" },
      ],
    },
    {
      tab: "label",
      title: "Label — Annotate Mode",
      rows: [
        { combo: `${L("left")} / ${L("right")}`,             desc: "Previous / next image" },
        { combo: `${L("shiftLeft")} / ${L("shiftRight")}`,   desc: "Previous / next set in queue" },
        { combo: "Shift+1/2/3/4",                            desc: "Ischemic / Hemorrhagic / Anomaly / Irrelevant" },
        { combo: "Shift+0",                                  desc: "Clear usability selection" },
        { combo: "Shift+Q",                                  desc: "Toggle Low Quality (Ischemic only)" },
        { combo: "Shift+B / C",                              desc: "Region: Basal / Corona" },
        { combo: "Shift+N",                                  desc: "Region: None — or focus slice notes if already None" },
        { combo: "N",                                        desc: "Focus set-level notes" },
        { combo: "I",                                        desc: "Jump to image number input" },
        { combo: "Shift+I",                                  desc: "Jump to set number input" },
        { combo: "Shift+A",                                  desc: "AI Assist (In Development)" },
        { combo: "W",                                        desc: "Jump to WL input" },
        { combo: "Shift+W",                                  desc: "Reset windowing" },
        { combo: "Shift+Tab",                                desc: "Cycle Image Set Evaluation tabs" },
        { combo: "P",                                        desc: "Toggle Wide Image Panel Mode" },
        { combo: "Shift+P",                                  desc: "Switch tab in Wide Mode (Annotation / Evaluation)" },
        { combo: "M",                                        desc: "Toggle Management Board" },
        { combo: "Ctrl+S",                                   desc: "Save draft" },
        { combo: "Ctrl+Enter",                               desc: "Submit (when ready)" },
        { combo: "Shift+Del",                                desc: "Open Reset All Annotations prompt" },
        { combo: "Y / N",                                    desc: "Confirm / cancel reset prompt" },
        { combo: "Shift+Esc",                                desc: "Return to Dashboard" },
        { combo: "Esc",                                      desc: "Close dialog / Management Board" },
      ],
    },
    {
      tab: "label",
      title: "Zone Mode",
      rows: [
        { combo: "Z",                                        desc: "Enter Zone Mode (Basal/Corona image)" },
        { combo: "V",                                        desc: "Enter Zone Mode directly in Vis" },
        { combo: "Shift+B / C",                              desc: "Re-press current zone to enter Zone Mode" },
        { combo: "1 / 2 / 3",                               desc: "Score selection (DMG / OK / NV) → advance" },
        { combo: "Shift+1 … N",                             desc: "Select row N" },
        { combo: "< / >",                                   desc: "Select Left / Right column" },
        { combo: "Ctrl+A",                                   desc: "Select all cells" },
        { combo: "V",                                        desc: "Promote selection to Vis range (or toggle Vis)" },
        { combo: "Esc",                                      desc: "Cancel selection scope → exit Vis → exit Zone Mode" },
        { combo: `${L("up")} / ${L("down")}`,                desc: "Move cursor row (or navigate selected row)" },
        { combo: `${L("left")} / ${L("right")}`,             desc: "Switch column (or navigate selected column)" },
        { combo: `${L("shiftUp")} / ${L("shiftDown")}`,      desc: "Jump to first / last row (cell scope only)" },
        { combo: "0",                                        desc: "Clear current cell / row / col / all selection" },
        { combo: "Del / Backspace",                          desc: "Clear selection (implicit, same as 0)" },
        { combo: "N",                                        desc: "Focus slice notes (Zone Mode stays on)" },
        { combo: "Z",                                        desc: "Exit Zone Mode" },
      ],
    },
    {
      tab: "label",
      title: "Label — Reader / Preview",
      rows: [
        { combo: `${L("left")} / ${L("right")}`,             desc: "Previous / next image" },
        { combo: `${L("shiftLeft")} / ${L("shiftRight")}`,   desc: "Previous / next set in queue" },
        { combo: "I / Shift+I",                              desc: "Jump to image / set number input" },
        { combo: "W / Shift+W",                              desc: "Jump to WL input / Reset windowing" },
        { combo: "Shift+Tab",                                desc: "Cycle Image Set Evaluation tabs" },
        { combo: "M",                                        desc: "Toggle Management Board" },
        { combo: "Shift+Esc",                                desc: "Return to Dashboard" },
        { combo: "Esc",                                      desc: "Close Management Board" },
      ],
    },
    {
      tab: "label",
      title: "Management Board",
      rows: [
        { combo: `${L("up")} / ${L("down")}`,               desc: "Navigate rows in active panel" },
        { combo: `${L("left")} / ${L("right")}`,            desc: "Switch active panel" },
      ],
    },
  ];
}

// ── Layout helpers ────────────────────────────────────────────────────────────

/** Distribute categories into `numCols` visual columns, preserving order. */
function distributeCategories(cats: Category[], numCols: number): Category[][] {
  const totalHeight = cats.reduce((s, c) => s + c.rows.length + 2, 0);
  const target = totalHeight / numCols;
  const cols: Category[][] = [[]];
  let colHeight = 0;
  for (const cat of cats) {
    const h = cat.rows.length + 2;
    if (colHeight > 0 && colHeight + h > target && cols.length < numCols) {
      cols.push([]);
      colHeight = 0;
    }
    cols[cols.length - 1].push(cat);
    colHeight += h;
  }
  return cols;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex items-center rounded border border-foreground/30 bg-foreground/10 px-1.5 py-0.5 font-mono text-xs text-foreground leading-none whitespace-nowrap shrink-0">
      {children}
    </kbd>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function KeyboardShortcutsPanel() {
  const { shortcutsOpen, shortcutsDefaultTab, setShortcutsOpen } = useUiStore();
  const { navMode } = useAppearanceStore();
  const [activeTab, setActiveTab] = useState<"general" | "label">(shortcutsDefaultTab);

  useEffect(() => {
    if (shortcutsOpen) setActiveTab(shortcutsDefaultTab);
  }, [shortcutsOpen, shortcutsDefaultTab]);

  const allCategories = buildCategories(navMode).filter((c) => c.tab === activeTab);
  const numCols = Math.min(allCategories.length, 3);
  const columns = distributeCategories(allCategories, numCols);

  return (
    <Dialog open={shortcutsOpen} onOpenChange={setShortcutsOpen}>
      <DialogContent
        className="w-[80vw] h-[80vh] max-w-none flex flex-col"
        onKeyDown={(e) => {
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
          <DialogTitle className="text-xl flex items-center gap-2.5">
            Keyboard Shortcuts
            {navMode !== "arrow" && (
              <span className="text-xs font-medium text-amber-400 border border-amber-400/40 bg-amber-400/10 px-2 py-0.5 rounded-md">
                Vim Mode On
              </span>
            )}
          </DialogTitle>
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

        {/* Content — horizontal flex of auto-width columns */}
        <div className="flex-1 overflow-y-auto">
          <div className="flex gap-10 pt-2 h-full">
            {columns.map((colCats, ci) => (
              <div key={ci} className="flex flex-col gap-6 w-max shrink-0">
                {colCats.map((cat) => (
                  <div key={cat.title}>
                    <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground pb-1.5 border-b border-border mb-2">
                      {cat.title}
                    </p>
                    <div className="space-y-0.5">
                      {cat.rows.map(({ combo, desc }) => (
                        <div key={`${combo}-${desc}`} className="flex items-center justify-between gap-4 py-0.5 whitespace-nowrap">
                          <span className="text-xs text-muted-foreground">{desc}</span>
                          <Kbd>{combo}</Kbd>
                        </div>
                      ))}
                    </div>
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
