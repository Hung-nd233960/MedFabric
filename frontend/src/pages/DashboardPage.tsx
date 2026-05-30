import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { PlayCircle, Trash2, Clock, CheckCircle2, FileEdit, Stethoscope, Globe, Layers, BookOpen, ScanEye, ArrowUpDown, ArrowUp, ArrowDown, AlertTriangle, ChevronLeft, ChevronRight, Keyboard, Minus } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { dashboardApi, imageSetsApi, annotationSessionsApi, evaluationsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useLabelStore } from "@/store/labelStore";
import { useLabelQueueStore } from "@/store/labelQueueStore";
import { WithTooltip } from "@/components/ui/tooltip";
import type { DashboardStats, DraftItem, HistoryEvent, ImageSetWithProgress } from "@/lib/types";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useUiStore } from "@/store/uiStore";
import { useAuthStore } from "@/store/authStore";
import { useAppearanceStore } from "@/store/appearanceStore";
import { nav, navLabel } from "@/lib/navKeys";

type Tab = "image-sets" | "drafts" | "history";
type SortDir = "asc" | "desc";
type SortCol     = "index" | "name" | "patient_id" | "icd" | "slices" | "evaluators" | "status";
type DraftSortCol = "index" | "name" | "patient_id" | "icd" | "slices" | "annotated" | "draft_time";
type HistSortCol  = "index" | "name" | "icd" | "event" | "time";

const TABS: Tab[] = ["image-sets", "drafts", "history"];

const SET_COLS: { key: SortCol; label: string }[] = [
  { key: "index",      label: "Index" },
  { key: "name",       label: "Image Set Name" },
  { key: "patient_id", label: "Patient ID" },
  { key: "icd",        label: "ICD" },
  { key: "slices",     label: "Slices" },
  { key: "evaluators", label: "Evaluators" },
  { key: "status",     label: "Status" },
];

const DRAFT_COLS: { key: DraftSortCol; label: string }[] = [
  { key: "index",      label: "Index" },
  { key: "name",       label: "Image Set Name" },
  { key: "patient_id", label: "Patient ID" },
  { key: "icd",        label: "ICD" },
  { key: "slices",     label: "Slices" },
  { key: "annotated",  label: "Annotated" },
  { key: "draft_time", label: "Draft" },
];

const HIST_COLS: { key: HistSortCol; label: string }[] = [
  { key: "index", label: "Index" },
  { key: "name",  label: "Image Set Name" },
  { key: "icd",   label: "ICD" },
  { key: "event", label: "Event" },
  { key: "time",  label: "Time" },
];

const STAT_COLORS = {
  blue:   { card: "border-blue-500/40 bg-blue-500/5",    icon: "text-blue-400",   value: "text-blue-400"   },
  green:  { card: "border-green-500/40 bg-green-500/5",  icon: "text-green-400",  value: "text-green-400"  },
  purple: { card: "border-purple-500/40 bg-purple-500/5", icon: "text-purple-400", value: "text-purple-400" },
  amber:  { card: "border-amber-500/40 bg-amber-500/5",  icon: "text-amber-400",  value: "text-amber-400"  },
} as const;

function StatCard({
  icon: Icon, label, value, pct, sub, color = "blue", tooltip,
}: {
  icon: React.ElementType; label: string; value: number; pct?: number; sub?: string;
  color?: keyof typeof STAT_COLORS; tooltip?: string;
}) {
  const c = STAT_COLORS[color];
  const card = (
    <Card className={cn("border", c.card)}>
      <CardHeader className="pb-2 flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className={cn("h-4 w-4", c.icon)} />
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <div className={cn("text-2xl font-bold", c.value)}>{value}</div>
          {pct !== undefined && <div className="text-sm font-medium text-muted-foreground">{pct}%</div>}
        </div>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
  if (!tooltip) return card;
  return (
    <WithTooltip content={tooltip} side="bottom">
      {card}
    </WithTooltip>
  );
}

function formatDateTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Bangkok" });
}

const EVENT_VARIANTS: Record<string, "success" | "warning" | "destructive" | "outline"> = {
  submitted: "success",
  draft_saved: "warning",
  draft_deleted: "destructive",
};
function compressIds(ids: number[]): string {
  if (ids.length === 0) return "";
  const sorted = [...ids].sort((a, b) => a - b);
  const ranges: string[] = [];
  let start = sorted[0];
  let end = sorted[0];
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] === end + 1) {
      end = sorted[i];
    } else {
      ranges.push(end > start ? `${start}-${end}` : `${start}`);
      start = sorted[i];
      end = sorted[i];
    }
  }
  ranges.push(end > start ? `${start}-${end}` : `${start}`);
  return ranges.join(", ");
}

const EVENT_LABELS: Record<string, string> = {
  submitted: "Submitted",
  draft_saved: "Draft Saved",
  draft_deleted: "Draft Deleted",
};

const statusRank = (s: ImageSetWithProgress) => s.evaluated_by_me ? 2 : s.in_draft_by_me ? 1 : 0;

export default function DashboardPage() {
  const navigate = useNavigate();
  const { fullName, username } = useAuthStore();
  const [activeTab, setActiveTab] = useState<Tab>("image-sets");
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [imageSets, setImageSets] = useState<ImageSetWithProgress[]>([]);
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [starting, setStarting] = useState(false);
  const [deletingDrafts, setDeletingDrafts] = useState(false);
  const [confirmDeleteDrafts, setConfirmDeleteDrafts] = useState(false);
  const [confirmLaunch, setConfirmLaunch] = useState<{ type: "annotate" | "read" | "preview"; count: number } | null>(null);
  const [selectedSets, setSelectedSets] = useState<Set<string>>(new Set());
  const [selectedDrafts, setSelectedDrafts] = useState<Set<string>>(new Set());
  const [sortCol, setSortCol] = useState<SortCol>("index");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [sortDraftCol, setSortDraftCol] = useState<DraftSortCol>("draft_time");
  const [sortDraftDir, setSortDraftDir] = useState<SortDir>("desc");
  const [sortHistCol, setSortHistCol] = useState<HistSortCol>("time");
  const [sortHistDir, setSortHistDir] = useState<SortDir>("desc");
  const { mode, setMode } = useLabelStore();
  const { showKbdHints, dashboardHintOpen, setDashboardHintOpen, navMode } = useAppearanceStore();
  const [kbHighlight, setKbHighlight] = useState(-1);
  const [visualMode, setVisualMode] = useState(false);
  const [visualAnchor, setVisualAnchor] = useState(-1);
  const kbHighlightTargetRef = useRef<{ uuid: string; setAnchor: boolean } | null>(null);

  const readableSets = imageSets.filter((s) => s.evaluated_by_me || s.in_draft_by_me);
  const visibleSets = mode === "read" ? readableSets : imageSets;
  const chosenIndices = [...visibleSets.filter((s: ImageSetWithProgress) => selectedSets.has(s.uuid))]
    .sort((a: ImageSetWithProgress, b: ImageSetWithProgress) => a.dataset_index - b.dataset_index)
    .map((s: ImageSetWithProgress) => s.dataset_index);

  const refreshDraftsAndHistory = async () => {
    try {
      const [draftsRes, histRes] = await Promise.all([
        evaluationsApi.listMyDrafts(),
        annotationSessionsApi.myHistory(),
      ]);
      setDrafts(draftsRes.data);
      setHistory(histRes.data);
      if (stats?.assigned_dataset) {
        const setsRes = await imageSetsApi.listByDataset(stats.assigned_dataset.dataset_uuid);
        setImageSets(setsRes.data);
      }
    } catch {
      // silent — the main load already toasted on failure
    }
  };

  useEffect(() => {
    const load = async () => {
      try {
        const statsRes = await dashboardApi.stats();
        const s: DashboardStats = statsRes.data;
        setStats(s);
        if (s.assigned_dataset) {
          const [setsRes, draftsRes, histRes] = await Promise.all([
            imageSetsApi.listByDataset(s.assigned_dataset.dataset_uuid),
            evaluationsApi.listMyDrafts(),
            annotationSessionsApi.myHistory(),
          ]);
          setImageSets(setsRes.data);
          setDrafts(draftsRes.data);
          setHistory(histRes.data);
        }
      } catch {
        toast.error("Failed to load dashboard");
      }
    };
    load();
  }, []);

  useEffect(() => {
    const poll = async () => {
      if (document.hidden) return;
      try {
        const statsRes = await dashboardApi.stats();
        const s: DashboardStats = statsRes.data;
        setStats(s);
        if (s.assigned_dataset) {
          const setsRes = await imageSetsApi.listByDataset(s.assigned_dataset.dataset_uuid);
          setImageSets(setsRes.data);
        }
      } catch {
        // silent — don't disrupt the user with background poll errors
      }
    };
    const id = setInterval(poll, 30_000);
    return () => clearInterval(id);
  }, []);

  // ── Image Sets tab helpers ──────────────────────────────────────────────────
  const toggleSet = (uuid: string) => setSelectedSets((prev) => {
    const next = new Set(prev);
    if (next.has(uuid)) next.delete(uuid); else next.add(uuid);
    return next;
  });
  const toggleAllSets = () =>
    setSelectedSets(selectedSets.size === visibleSets.length ? new Set() : new Set(visibleSets.map((s) => s.uuid)));

  const handleSort      = (col: SortCol)      => { if (sortCol === col)      setSortDir((d) => d === "asc" ? "desc" : "asc"); else { setSortCol(col);      setSortDir("asc"); } };
  const handleSortDraft = (col: DraftSortCol) => { if (sortDraftCol === col) setSortDraftDir((d) => d === "asc" ? "desc" : "asc"); else { setSortDraftCol(col); setSortDraftDir("asc"); } };
  const handleSortHist  = (col: HistSortCol)  => { if (sortHistCol === col)  setSortHistDir((d) => d === "asc" ? "desc" : "asc"); else { setSortHistCol(col);  setSortHistDir("asc"); } };

  const sortedSets = useMemo(() => [...visibleSets].sort((a, b) => {
    const sel = (selectedSets.has(b.uuid) ? 1 : 0) - (selectedSets.has(a.uuid) ? 1 : 0);
    if (!visualMode && sel !== 0) return sel;
    let cmp = 0;
    switch (sortCol) {
      case "index":      cmp = a.dataset_index - b.dataset_index; break;
      case "name":       cmp = (a.image_set_name ?? "").localeCompare(b.image_set_name ?? ""); break;
      case "patient_id": cmp = (a.patient_id ?? "").localeCompare(b.patient_id ?? ""); break;
      case "icd":        cmp = (a.icd_code ?? "").localeCompare(b.icd_code ?? ""); break;
      case "slices":     cmp = a.num_images - b.num_images; break;
      case "evaluators": cmp = a.total_evaluators - b.total_evaluators; break;
      case "status":     cmp = statusRank(a) - statusRank(b); break;
    }
    return sortDir === "asc" ? cmp : -cmp;
  }), [visibleSets, selectedSets, sortCol, sortDir, visualMode]);

  const sortedDrafts = [...drafts].sort((a, b) => {
    const sel = (selectedDrafts.has(b.annotation_session_uuid) ? 1 : 0) - (selectedDrafts.has(a.annotation_session_uuid) ? 1 : 0);
    if (sel !== 0) return sel;
    let cmp = 0;
    switch (sortDraftCol) {
      case "index":      cmp = a.dataset_index - b.dataset_index; break;
      case "name":       cmp = (a.image_set_name ?? "").localeCompare(b.image_set_name ?? ""); break;
      case "patient_id": cmp = (a.patient_id ?? "").localeCompare(b.patient_id ?? ""); break;
      case "icd":        cmp = (a.icd_code ?? "").localeCompare(b.icd_code ?? ""); break;
      case "slices":     cmp = a.num_images - b.num_images; break;
      case "annotated":  cmp = (a.evaluated_by_me ? 1 : 0) - (b.evaluated_by_me ? 1 : 0); break;
      case "draft_time": cmp = a.draft_saved_at.localeCompare(b.draft_saved_at); break;
    }
    return sortDraftDir === "asc" ? cmp : -cmp;
  });

  const sortedHistory = [...history].sort((a, b) => {
    let cmp = 0;
    switch (sortHistCol) {
      case "index": cmp = a.dataset_index - b.dataset_index; break;
      case "name":  cmp = (a.image_set_name ?? "").localeCompare(b.image_set_name ?? ""); break;
      case "icd":   cmp = (a.icd_code ?? "").localeCompare(b.icd_code ?? ""); break;
      case "event": cmp = a.event_type.localeCompare(b.event_type); break;
      case "time":  cmp = a.timestamp.localeCompare(b.timestamp); break;
    }
    return sortHistDir === "asc" ? cmp : -cmp;
  });

  const mkSortIcon = (active: string, dir: SortDir) => (col: string) =>
    active !== col
      ? <ArrowUpDown className="h-3 w-3 opacity-40 shrink-0" />
      : dir === "asc"
        ? <ArrowUp className="h-3 w-3 shrink-0" />
        : <ArrowDown className="h-3 w-3 shrink-0" />;

  const SortIcon      = mkSortIcon(sortCol,      sortDir);
  const SortIconDraft = mkSortIcon(sortDraftCol, sortDraftDir);
  const SortIconHist  = mkSortIcon(sortHistCol,  sortHistDir);

  // ── Launch helpers — split into doX (actual launch) and handleX (count guard) ──
  const doAnnotateSets = async () => {
    const chosen = [...imageSets.filter((s) => selectedSets.has(s.uuid))].sort(
      (a, b) => a.dataset_index - b.dataset_index
    );
    const target = chosen.find((s) => !s.evaluated_by_me) ?? chosen[0];
    if (!target) return;
    setStarting(true);
    try {
      const res = await annotationSessionsApi.open(target.uuid);
      useLabelQueueStore.getState().enter({
        queue: chosen.map((s) => s.uuid),
        currentPos: chosen.findIndex((s) => s.uuid === target.uuid),
        indices: chosen.map((s) => s.dataset_index),
        sources: [],
        sessionUuid: res.data.annotation_session_uuid,
        adminDoctors: [],
        isReadMode: false,
        isPreviewMode: false,
      });
      navigate("/label");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to start";
      toast.error(msg);
    } finally {
      setStarting(false);
    }
  };

  const handleAnnotateSets = () => {
    if (selectedSets.size >= 50) { setConfirmLaunch({ type: "annotate", count: selectedSets.size }); return; }
    doAnnotateSets();
  };

  const doReadSets = () => {
    const chosen = [...readableSets.filter((s) => selectedSets.has(s.uuid))].sort(
      (a, b) => a.dataset_index - b.dataset_index
    );
    if (!chosen.length) return;
    useLabelQueueStore.getState().enter({
      queue: chosen.map((s) => s.uuid),
      currentPos: 0,
      indices: chosen.map((s) => s.dataset_index),
      sources: chosen.map((s) => (s.evaluated_by_me ? "submission" : "draft")),
      sessionUuid: null,
      adminDoctors: [],
      isReadMode: true,
      isPreviewMode: false,
    });
    navigate("/label");
  };

  const handleReadSets = () => {
    if (selectedSets.size >= 50) { setConfirmLaunch({ type: "read", count: selectedSets.size }); return; }
    doReadSets();
  };

  const doPreviewSets = () => {
    const chosen = [...imageSets.filter((s) => selectedSets.has(s.uuid))].sort(
      (a, b) => a.dataset_index - b.dataset_index
    );
    if (!chosen.length) return;
    useLabelQueueStore.getState().enter({
      queue: chosen.map((s) => s.uuid),
      currentPos: 0,
      indices: chosen.map((s) => s.dataset_index),
      sources: [],
      sessionUuid: null,
      adminDoctors: [],
      isReadMode: false,
      isPreviewMode: true,
    });
    navigate("/label");
  };

  const handlePreviewSets = () => {
    if (selectedSets.size >= 50) { setConfirmLaunch({ type: "preview", count: selectedSets.size }); return; }
    doPreviewSets();
  };

  const handleReadDraft = (draft: { image_set_uuid: string; dataset_index: number }) => {
    useLabelQueueStore.getState().enter({
      queue: [draft.image_set_uuid],
      currentPos: 0,
      indices: [draft.dataset_index],
      sources: ["draft"],
      sessionUuid: null,
      adminDoctors: [],
      isReadMode: true,
      isPreviewMode: false,
    });
    navigate("/label");
  };

  // ── Drafts tab helpers ──────────────────────────────────────────────────────
  const toggleDraft = (uuid: string) => setSelectedDrafts((prev) => {
    const next = new Set(prev);
    if (next.has(uuid)) next.delete(uuid); else next.add(uuid);
    return next;
  });
  const toggleAllDrafts = () =>
    setSelectedDrafts(selectedDrafts.size === drafts.length ? new Set() : new Set(drafts.map((d) => d.annotation_session_uuid)));

  const handleAnnotateDraft = async (draft: DraftItem) => {
    setStarting(true);
    try {
      const res = await annotationSessionsApi.open(draft.image_set_uuid);
      useLabelQueueStore.getState().enter({
        queue: [draft.image_set_uuid],
        currentPos: 0,
        indices: [draft.dataset_index],
        sources: [],
        sessionUuid: res.data.annotation_session_uuid,
        adminDoctors: [],
        isReadMode: false,
        isPreviewMode: false,
      });
      navigate("/label");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to start";
      toast.error(msg);
    } finally {
      setStarting(false);
    }
  };

  const handleDeleteDrafts = async () => {
    setDeletingDrafts(true);
    setConfirmDeleteDrafts(false);
    const targets = drafts.filter((d: DraftItem) => selectedDrafts.has(d.annotation_session_uuid));
    try {
      for (const d of targets) {
        await evaluationsApi.deleteDraftByImageSet(d.image_set_uuid);
      }
      setSelectedDrafts(new Set());
      toast.success(`${targets.length} draft(s) deleted.`);
      await refreshDraftsAndHistory();
    } catch {
      toast.error("Failed to delete some drafts.");
    } finally {
      setDeletingDrafts(false);
    }
  };

  // Reset keyboard highlight and visual mode when tab changes
  useEffect(() => { setKbHighlight(-1); setVisualMode(false); setVisualAnchor(-1); }, [activeTab]);

  // Auto-scroll highlighted row into view
  useEffect(() => {
    if (kbHighlight < 0) return;
    const el = document.querySelector(`[data-kb-row="${kbHighlight}"]`);
    el?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [kbHighlight]);

  // Restore cursor position by UUID after sort order changes (e.g. entering/exiting Visual Mode)
  useLayoutEffect(() => {
    const target = kbHighlightTargetRef.current;
    if (!target) return;
    kbHighlightTargetRef.current = null;
    const idx = sortedSets.findIndex((s) => s.uuid === target.uuid);
    if (idx >= 0) {
      setKbHighlight(idx);
      if (target.setAnchor) setVisualAnchor(idx);
    }
  }, [sortedSets]);

  // ── Keyboard shortcuts ───────────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (useUiStore.getState().shortcutsOpen) return;
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.altKey) return;

      const key = e.key;
      const UP = key.toUpperCase();
      const shift = e.shiftKey;
      const ctrl = e.ctrlKey || e.metaKey;

      // Confirm dialogs handle their own keys via ConfirmDialog's capture listener;
      // consume any remaining keys here so they don't leak to table navigation.
      if (confirmDeleteDrafts || confirmLaunch) { e.preventDefault(); return; }

      // Tab — cycle tabs forward (Shift+Tab backward)
      if (key === "Tab" && !ctrl) {
        e.preventDefault();
        const idx = TABS.indexOf(activeTab);
        const next = shift ? (idx - 1 + TABS.length) % TABS.length : (idx + 1) % TABS.length;
        setActiveTab(TABS[next]);
        setKbHighlight(-1);
        setSelectedSets(new Set());
        setSelectedDrafts(new Set());
        return;
      }

      // Ctrl+A — select / deselect all in current tab
      if (ctrl && !shift && UP === "A") {
        e.preventDefault();
        if (activeTab === "image-sets") toggleAllSets();
        else if (activeTab === "drafts") toggleAllDrafts();
        return;
      }

      // 1 / 2 / 3 — switch tabs directly
      if (!shift && !ctrl) {
        if (key === "1") { setActiveTab("image-sets"); setKbHighlight(-1); setSelectedSets(new Set()); setSelectedDrafts(new Set()); return; }
        if (key === "2") { setActiveTab("drafts");     setKbHighlight(-1); setSelectedSets(new Set()); setSelectedDrafts(new Set()); return; }
        if (key === "3") { setActiveTab("history");    setKbHighlight(-1); setSelectedSets(new Set()); setSelectedDrafts(new Set()); return; }
      }

      // Drafts tab: Del (no shift) or Shift+D — open delete confirm
      if (activeTab === "drafts" && selectedDrafts.size > 0 && mode !== "read") {
        if ((key === "Delete" && !shift && !ctrl) || (shift && !ctrl && UP === "D")) {
          e.preventDefault();
          setConfirmDeleteDrafts(true);
          return;
        }
      }

      if (activeTab !== "image-sets") return;

      // V — enter / exit Visual Mode
      if (!ctrl && !shift && UP === "V" && sortedSets.length > 0) {
        if (visualMode) {
          if (kbHighlight >= 0 && kbHighlight < sortedSets.length)
            kbHighlightTargetRef.current = { uuid: sortedSets[kbHighlight].uuid, setAnchor: false };
          setVisualMode(false);
          setVisualAnchor(-1);
        } else {
          const anchor = kbHighlight >= 0 ? kbHighlight : 0;
          if (anchor < sortedSets.length)
            kbHighlightTargetRef.current = { uuid: sortedSets[anchor].uuid, setAnchor: true };
          if (kbHighlight < 0) setKbHighlight(0);
          setVisualAnchor(anchor);
          setVisualMode(true);
        }
        return;
      }

      // Mode toggle
      if (!shift && !ctrl) {
        if (UP === "A") { setMode("annotate"); return; }
        if (UP === "R") { setMode("read"); return; }
      }

      // Row navigation
      if (!ctrl && nav.up(e, navMode)) {
        e.preventDefault();
        setKbHighlight((h) => (sortedSets.length === 0 ? -1 : h <= 0 ? sortedSets.length - 1 : h - 1));
        return;
      }
      if (!ctrl && nav.down(e, navMode)) {
        e.preventDefault();
        setKbHighlight((h) => (sortedSets.length === 0 ? -1 : h >= sortedSets.length - 1 ? 0 : h + 1));
        return;
      }
      if (!ctrl && nav.shiftUp(e, navMode)) {
        e.preventDefault();
        if (sortedSets.length > 0) setKbHighlight(0);
        return;
      }
      if (!ctrl && nav.shiftDown(e, navMode)) {
        e.preventDefault();
        if (sortedSets.length > 0) setKbHighlight(sortedSets.length - 1);
        return;
      }

      // Shift+Q — jump to first not-done image set (only when nothing is selected and not in Visual Mode)
      if (shift && !ctrl && UP === "Q" && !visualMode && selectedSets.size === 0 && sortedSets.length > 0) {
        e.preventDefault();
        const found = sortedSets.findIndex((s) => !s.evaluated_by_me);
        if (found >= 0) setKbHighlight(found);
        return;
      }

      // Shift+1–0 — jump to decile
      if (shift && !ctrl && e.code?.startsWith("Digit") && sortedSets.length > 0) {
        const d = parseInt(e.code.slice(-1));
        if (!isNaN(d)) {
          e.preventDefault();
          const len = sortedSets.length;
          const idx = d === 1 ? 0 : d === 0 ? len - 1 : Math.min(Math.floor((d - 1) * 0.1 * len), len - 1);
          setKbHighlight(idx);
        }
        return;
      }

      // Esc — exit Visual Mode, or clear highlight and selection
      if (key === "Escape") {
        if (visualMode) {
          if (kbHighlight >= 0 && kbHighlight < sortedSets.length)
            kbHighlightTargetRef.current = { uuid: sortedSets[kbHighlight].uuid, setAnchor: false };
          setVisualMode(false);
          setVisualAnchor(-1);
          return;
        }
        setKbHighlight(-1);
        setSelectedSets(new Set());
        return;
      }

      // Enter / Space — confirm Visual Mode range, or toggle highlighted row
      if ((key === "Enter" || key === " ") && !shift && !ctrl && kbHighlight >= 0 && kbHighlight < sortedSets.length) {
        e.preventDefault();
        if (visualMode) {
          const lo = Math.min(visualAnchor, kbHighlight);
          const hi = Math.max(visualAnchor, kbHighlight);
          kbHighlightTargetRef.current = { uuid: sortedSets[kbHighlight].uuid, setAnchor: false };
          setSelectedSets((prev) => {
            const next = new Set(prev);
            for (let i = lo; i <= hi; i++) {
              if (i < sortedSets.length) {
                const uuid = sortedSets[i].uuid;
                if (next.has(uuid)) next.delete(uuid); else next.add(uuid);
              }
            }
            return next;
          });
          setVisualMode(false);
          setVisualAnchor(-1);
        } else {
          toggleSet(sortedSets[kbHighlight].uuid);
        }
        return;
      }

      // Shift+A/R/P — launch selected sets
      if (shift && !ctrl && selectedSets.size > 0) {
        if (UP === "A") { e.preventDefault(); handleAnnotateSets(); return; }
        if (UP === "R") { e.preventDefault(); handleReadSets();     return; }
        if (UP === "P") { e.preventDefault(); handlePreviewSets();  return; }
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeTab, kbHighlight, sortedSets, selectedSets, selectedDrafts, toggleSet, toggleAllSets, toggleAllDrafts, // eslint-disable-line react-hooks/exhaustive-deps
      confirmDeleteDrafts, confirmLaunch, handleAnnotateSets, handleReadSets, handlePreviewSets,
      doAnnotateSets, doReadSets, doPreviewSets, handleDeleteDrafts, mode, visualMode, visualAnchor]);

  return (
    <div className="flex flex-col overflow-hidden" style={{ zoom: 1.2, height: "calc(100vh / 1.2)" }}>
      <div className="flex-1 overflow-hidden flex flex-col max-w-6xl mx-auto w-full px-6 pt-5 pb-4 gap-4">

        {/* Header */}
        <div className="shrink-0 flex items-start justify-between gap-6">
          <div>
            <h1 className="text-2xl font-semibold">Dashboard</h1>
            {stats?.assigned_dataset ? (
              <p className="text-muted-foreground text-sm mt-1">
                Assigned dataset:{" "}
                <span className="text-foreground font-medium">{stats.assigned_dataset.name}</span>
              </p>
            ) : (
              <p className="text-muted-foreground text-sm mt-1">No dataset assigned — contact an admin.</p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="text-lg font-semibold">{(() => {
              const h = new Date().getHours();
              const greet = h >= 5 && h < 12 ? "Good Morning,"
                : h >= 12 && h < 18 ? "Good Afternoon,"
                : h >= 18 && h < 22 ? "Good Evening,"
                : "Staying Up Late?";
              return `${greet} ${fullName ?? username ?? "Doctor"}`;
            })()} 👋</p>
            <p className="text-sm text-muted-foreground mt-0.5">Thank you for your dedication to advancing medical AI.</p>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="shrink-0 grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={Layers} label="Total Image Sets" value={stats.total_image_sets} color="blue" />
            <StatCard
              icon={Stethoscope}
              label="My Progress"
              value={stats.my_progress}
              pct={stats.total_image_sets > 0 ? parseFloat((stats.my_progress / stats.total_image_sets * 100).toFixed(2)) : 0}
              sub="sets evaluated by you"
              color="green"
            />
            <StatCard
              icon={Globe}
              label="Global Progress"
              value={stats.global_progress}
              pct={stats.total_image_sets > 0 ? parseFloat((stats.global_progress / stats.total_image_sets * 100).toFixed(2)) : 0}
              sub="unique sets with ≥1 evaluation"
              color="purple"
              tooltip="Unique image sets with at least one evaluation from any doctor in the cohort"
            />
            <StatCard icon={CheckCircle2} label="Remaining" value={Math.max(0, stats.total_image_sets - stats.my_progress)} sub="sets you haven't evaluated" color="amber" />
          </div>
        )}

        {/* Tabs */}
        {stats?.assigned_dataset && (
          <div className="flex-1 overflow-hidden flex flex-col gap-3">

            {/* Tab bar + mode toggle */}
            <div className="shrink-0 flex items-center justify-between gap-4 border-b border-border pb-0">
              <div className="flex items-center">
                {showKbdHints && (
                  <button
                    type="button"
                    onClick={() => { const idx = TABS.indexOf(activeTab); setActiveTab(TABS[(idx - 1 + TABS.length) % TABS.length]); setSelectedSets(new Set()); setSelectedDrafts(new Set()); }}
                    className="flex items-center gap-1 px-2 py-2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    <kbd className="font-mono border border-primary/40 bg-primary text-black px-1.5 py-0.5 rounded text-xs leading-none">Shift+Tab</kbd>
                  </button>
                )}
                {(["image-sets", "drafts", "history"] as Tab[]).map((tab, i) => {
                  const labels: Record<Tab, string> = { "image-sets": "Image Sets", drafts: "Drafts", history: "History" };
                  return (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => { setActiveTab(tab); setSelectedSets(new Set()); setSelectedDrafts(new Set()); }}
                      className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                        activeTab === tab
                          ? "border-primary text-foreground"
                          : "border-transparent text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <span className="flex items-center gap-1.5">
                        {labels[tab]}
                        {tab === "drafts" && (
                          <span className={`rounded-full border px-1.5 py-0 text-xs font-semibold leading-5 tabular-nums transition-colors ${
                            drafts.length > 0
                              ? "border-amber-500/50 bg-amber-500/15 text-amber-400"
                              : "border-muted-foreground/20 bg-muted/30 text-muted-foreground/50"
                          }`}>
                            {drafts.length}
                          </span>
                        )}
                        {showKbdHints && <kbd className="font-mono border border-primary/40 bg-primary text-black px-1.5 py-0.5 rounded text-xs leading-none">{i + 1}</kbd>}
                      </span>
                    </button>
                  );
                })}
                {showKbdHints && (
                  <button
                    type="button"
                    onClick={() => { const idx = TABS.indexOf(activeTab); setActiveTab(TABS[(idx + 1) % TABS.length]); setSelectedSets(new Set()); setSelectedDrafts(new Set()); }}
                    className="flex items-center gap-1 px-2 py-2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <kbd className="font-mono border border-primary/40 bg-primary text-black px-1.5 py-0.5 rounded text-xs leading-none">Tab</kbd>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              {(activeTab === "image-sets" || activeTab === "drafts") && (
                <div className="flex items-center gap-1 rounded-lg border border-border p-0.5 mb-1">
                  <WithTooltip content="Start or continue scoring image sets" side="bottom">
                    <button
                      type="button"
                      onClick={() => { setMode("annotate"); setSelectedSets(new Set()); setSelectedDrafts(new Set()); }}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                        mode === "annotate" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <PlayCircle className="h-3.5 w-3.5" /> Annotate {showKbdHints && <kbd className={`font-mono border rounded px-1.5 py-0.5 text-xs leading-none ${mode === "annotate" ? "bg-background text-primary border-primary/40" : "bg-primary text-primary-foreground border-primary/20"}`}>A</kbd>}
                    </button>
                  </WithTooltip>
                  <WithTooltip content="Review your submitted or saved annotations (read-only)" side="bottom">
                    <button
                      type="button"
                      onClick={() => { setMode("read"); setSelectedSets(new Set()); setSelectedDrafts(new Set()); }}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                        mode === "read" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <BookOpen className="h-3.5 w-3.5" /> Reader {showKbdHints && <kbd className={`font-mono border rounded px-1.5 py-0.5 text-xs leading-none ${mode === "read" ? "bg-background text-primary border-primary/40" : "bg-primary text-primary-foreground border-primary/20"}`}>R</kbd>}
                    </button>
                  </WithTooltip>
                </div>
              )}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-hidden">

              {/* ── Image Sets tab ── */}
              {activeTab === "image-sets" && (
                <div className="h-full flex flex-col gap-3">
                  <div className={`shrink-0 rounded-lg border px-4 py-3 text-sm flex items-center justify-between gap-4 transition-colors ${
                    selectedSets.size > 0 ? "border-primary bg-primary/5" : "border-border bg-muted/30"
                  }`}>
                    {selectedSets.size === 0 ? (
                      <span className="text-muted-foreground">
                        {mode === "read" ? "Choose annotated or drafted sets to read" : "Choose image sets to annotate"}
                      </span>
                    ) : (
                      <>
                        <span>
                          You have chosen {chosenIndices.length === 1 ? "set" : "sets"}:{" "}
                          <span className="font-mono font-medium">{compressIds(chosenIndices)}</span>
                        </span>
                        {mode === "read" ? (
                          <Button size="sm" className="gap-1.5 shrink-0" onClick={handleReadSets}>
                            <BookOpen className="h-4 w-4" /> Read {showKbdHints && <kbd className="font-mono border border-primary/40 bg-background text-primary rounded px-1.5 py-0.5 text-xs leading-none">Shift+R</kbd>}
                          </Button>
                        ) : (
                          <div className="flex gap-2">
                            <WithTooltip content="Browse images without starting an annotation session" side="top">
                              <Button size="sm" variant="outline" className="gap-1.5 shrink-0 border-orange-500/60 text-orange-400 hover:bg-orange-500/10" onClick={handlePreviewSets}>
                                <ScanEye className="h-4 w-4" /> Preview {showKbdHints && <kbd className="font-mono border border-amber-600/40 bg-amber-500 text-black rounded px-1.5 py-0.5 text-xs leading-none">Shift+P</kbd>}
                              </Button>
                            </WithTooltip>
                            <Button size="sm" className="gap-1.5 shrink-0" disabled={starting} onClick={handleAnnotateSets}>
                              <PlayCircle className="h-4 w-4" />
                              {starting ? "Starting…" : <>Annotate {showKbdHints && <kbd className="font-mono border border-primary/40 bg-background text-primary rounded px-1.5 py-0.5 text-xs leading-none">Shift+A</kbd>}</>}
                            </Button>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {visibleSets.length === 0 ? (
                    <p className="text-muted-foreground text-sm">
                      {mode === "read" ? "No annotated or drafted sets to read." : "No image sets found."}
                    </p>
                  ) : (
                    <div className="flex-1 overflow-hidden rounded-lg border flex flex-col">
                      <div className="flex-1 overflow-y-auto">
                        <table className="w-full text-sm table-fixed">
                          <colgroup>
                            <col className="w-[6%]" />
                            <col className="w-[25%]" />
                            <col className="w-[25%]" />
                            <col className="w-[8%]" />
                            <col className="w-[7%]" />
                            <col className="w-[10%]" />
                            <col className="w-[10%]" />
                            <col className="w-[5%]" />
                          </colgroup>
                          <thead className="bg-muted sticky top-0 z-10">
                            <tr>
                              {SET_COLS.map(({ key, label }) => (
                                <th key={key} className="text-left px-3 py-2 font-medium">
                                  <button
                                    type="button"
                                    onClick={() => handleSort(key)}
                                    className="flex items-center gap-1 hover:text-foreground transition-colors text-muted-foreground data-[active]:text-foreground"
                                    data-active={sortCol === key ? "" : undefined}
                                  >
                                    {label}
                                    {SortIcon(key)}
                                  </button>
                                </th>
                              ))}
                              <th className="px-3 py-2 flex justify-end">
                                <Checkbox checked={selectedSets.size === visibleSets.length && visibleSets.length > 0} onChange={toggleAllSets} />
                              </th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {sortedSets.map((s, si) => (
                              <tr
                                key={s.uuid}
                                data-kb-row={si}
                                className={`transition-colors cursor-pointer ${
                                  visualMode && si >= Math.min(visualAnchor, kbHighlight) && si <= Math.max(visualAnchor, kbHighlight)
                                    ? si === kbHighlight
                                      ? "bg-blue-500/25 ring-2 ring-inset ring-blue-500/50"
                                      : "bg-blue-500/15 ring-1 ring-inset ring-blue-500/25"
                                    : kbHighlight === si
                                      ? "bg-primary/10 ring-1 ring-inset ring-primary/40"
                                      : selectedSets.has(s.uuid)
                                        ? "bg-primary/5"
                                        : "hover:bg-muted/30"
                                }`}
                                onClick={() => { setVisualMode(false); setVisualAnchor(-1); setKbHighlight(-1); toggleSet(s.uuid); }}
                              >
                                <td className="px-3 py-3 font-mono text-muted-foreground overflow-hidden"><span className="block truncate">{s.dataset_index}</span></td>
                                <td className="px-3 py-3 font-medium overflow-hidden"><span className="block truncate" title={s.image_set_name}>{s.image_set_name}</span></td>
                                <td className="px-3 py-3 text-muted-foreground overflow-hidden"><span className="block truncate font-mono text-xs" title={s.patient_id ?? ""}>{s.patient_id ?? "—"}</span></td>
                                <td className="px-3 py-3 text-muted-foreground overflow-hidden"><span className="block truncate">{s.icd_code ?? "—"}</span></td>
                                <td className="px-3 py-3 overflow-hidden"><span className="block truncate">{s.num_images}</span></td>
                                <td className="px-3 py-3 overflow-hidden"><span className="block truncate">{s.total_evaluators}</span></td>
                                <td className="px-3 py-3 overflow-hidden">
                                  {s.evaluated_by_me ? (
                                    <Badge variant="success">Done</Badge>
                                  ) : s.in_draft_by_me ? (
                                    <Badge variant="warning">In Draft</Badge>
                                  ) : (
                                    <Badge variant="outline">Pending</Badge>
                                  )}
                                </td>
                                <td className="px-3 py-3">
                                  <div className="flex justify-end">
                                    <Checkbox checked={selectedSets.has(s.uuid)} onChange={() => toggleSet(s.uuid)} />
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {visualMode && (() => {
                        const lo = Math.min(visualAnchor, kbHighlight);
                        const hi = Math.max(visualAnchor, kbHighlight);
                        const total = hi - lo + 1;
                        let chosen = 0;
                        for (let i = lo; i <= hi; i++) {
                          if (i < sortedSets.length && selectedSets.has(sortedSets[i].uuid)) chosen++;
                        }
                        const notChosen = total - chosen;
                        const rangedSets = sortedSets.slice(lo, hi + 1);
                        const cntDone    = rangedSets.filter(s => s.evaluated_by_me).length;
                        const cntDraft   = rangedSets.filter(s => s.in_draft_by_me).length;
                        const cntPending = rangedSets.filter(s => !s.evaluated_by_me && !s.in_draft_by_me).length;
                        return (
                          <div className="shrink-0 border-t border-blue-500/20 bg-blue-500/5 px-3 py-1.5 text-xs font-mono select-none flex items-center gap-3 flex-wrap">
                            <span className="text-blue-400">-- VISUAL --</span>
                            <span className="text-muted-foreground">
                              {total} row{total !== 1 ? "s" : ""},{"  "}
                              <span className="text-primary">{chosen} chosen</span>,{"  "}
                              {notChosen} not chosen
                            </span>
                            <span className="text-muted-foreground/40">|</span>
                            <span className="text-muted-foreground">
                              <span className="text-green-400">{cntDone} done</span>
                              {"  ·  "}
                              <span className="text-yellow-400">{cntDraft} draft</span>
                              {"  ·  "}
                              <span className="text-muted-foreground">{cntPending} pending</span>
                            </span>
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </div>
              )}

              {/* ── Drafts tab ── */}
              {activeTab === "drafts" && (
                <div className="h-full flex flex-col gap-3">
                  <div className={`shrink-0 rounded-lg border px-4 py-3 text-sm flex items-center justify-between gap-4 transition-colors ${
                    selectedDrafts.size > 0 ? "border-primary bg-primary/5" : "border-border bg-muted/30"
                  }`}>
                    {selectedDrafts.size === 0 ? (
                      <span className="text-muted-foreground">
                        {mode === "read" ? "Select a draft to read" : "Select drafts to annotate or delete"}
                      </span>
                    ) : (
                      <>
                        <span><span className="font-medium">{selectedDrafts.size}</span> draft(s) selected</span>
                        <div className="flex gap-2">
                          {mode !== "read" && (
                            <Button
                              size="sm"
                              variant="destructive"
                              className="gap-1.5"
                              disabled={deletingDrafts}
                              onClick={() => setConfirmDeleteDrafts(true)}
                            >
                              <Trash2 className="h-4 w-4" />
                              Delete Draft
                            </Button>
                          )}
                          {selectedDrafts.size === 1 && (() => {
                            const draft = drafts.find((d) => selectedDrafts.has(d.annotation_session_uuid));
                            return draft ? (
                              mode === "read" ? (
                                <Button size="sm" className="gap-1.5" onClick={() => handleReadDraft(draft)}>
                                  <BookOpen className="h-4 w-4" /> Read
                                </Button>
                              ) : (
                                <Button size="sm" className="gap-1.5" disabled={starting} onClick={() => handleAnnotateDraft(draft)}>
                                  <PlayCircle className="h-4 w-4" />
                                  {starting ? "Starting…" : "Annotate"}
                                </Button>
                              )
                            ) : null;
                          })()}
                        </div>
                      </>
                    )}
                  </div>

                  {drafts.length === 0 ? (
                    <p className="text-muted-foreground text-sm">No drafts saved.</p>
                  ) : (
                    <div className="flex-1 overflow-hidden rounded-lg border">
                      <div className="h-full overflow-y-auto">
                        <table className="w-full text-sm table-fixed">
                          <colgroup>
                            <col className="w-[5%]" />
                            <col className="w-[24%]" />
                            <col className="w-[20%]" />
                            <col className="w-[7%]" />
                            <col className="w-[6%]" />
                            <col className="w-[10%]" />
                            <col className="w-[18%]" />
                            <col className="w-[5%]" />
                          </colgroup>
                          <thead className="bg-muted sticky top-0 z-10">
                            <tr>
                              {DRAFT_COLS.map(({ key, label }) => (
                                <th key={key} className="text-left px-3 py-2 font-medium">
                                  <button
                                    type="button"
                                    onClick={() => handleSortDraft(key)}
                                    className="flex items-center gap-1 hover:text-foreground transition-colors text-muted-foreground data-[active]:text-foreground"
                                    data-active={sortDraftCol === key ? "" : undefined}
                                  >
                                    {label}
                                    {SortIconDraft(key)}
                                  </button>
                                </th>
                              ))}
                              <th className="px-3 py-2 flex justify-end">
                                <Checkbox checked={selectedDrafts.size === drafts.length && drafts.length > 0} onChange={toggleAllDrafts} />
                              </th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {sortedDrafts.map((d) => (
                              <tr
                                key={d.annotation_session_uuid}
                                className={`transition-colors cursor-pointer ${selectedDrafts.has(d.annotation_session_uuid) ? "bg-primary/5" : "hover:bg-muted/30"}`}
                                onClick={() => toggleDraft(d.annotation_session_uuid)}
                              >
                                <td className="px-3 py-3 font-mono text-muted-foreground overflow-hidden"><span className="block truncate">{d.dataset_index}</span></td>
                                <td className="px-3 py-3 font-medium overflow-hidden"><span className="block truncate" title={d.image_set_name}>{d.image_set_name}</span></td>
                                <td className="px-3 py-3 text-muted-foreground overflow-hidden"><span className="block truncate font-mono text-xs">{d.patient_id ?? "—"}</span></td>
                                <td className="px-3 py-3 text-muted-foreground overflow-hidden"><span className="block truncate">{d.icd_code ?? "—"}</span></td>
                                <td className="px-3 py-3 overflow-hidden"><span className="block truncate">{d.num_images}</span></td>
                                <td className="px-3 py-3 overflow-hidden">
                                  {d.evaluated_by_me ? <Badge variant="success">Done</Badge> : <Badge variant="outline">Pending</Badge>}
                                </td>
                                <td className="px-3 py-3 overflow-hidden">
                                  <span className="flex items-center gap-1 text-muted-foreground text-xs">
                                    <Clock className="h-3 w-3 shrink-0" />
                                    <span className={d.draft_source === "manual" ? "text-yellow-400" : "text-muted-foreground"}>
                                      {d.draft_source === "manual" ? "Manual" : "Auto"}
                                    </span>
                                    {formatDateTime(d.draft_saved_at)}
                                  </span>
                                </td>
                                <td className="px-3 py-3">
                                  <div className="flex justify-end">
                                    <Checkbox checked={selectedDrafts.has(d.annotation_session_uuid)} onChange={() => toggleDraft(d.annotation_session_uuid)} />
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── History tab ── */}
              {activeTab === "history" && (
                <div className="h-full flex flex-col gap-3">
                  {history.length === 0 ? (
                    <p className="text-muted-foreground text-sm">No activity yet.</p>
                  ) : (
                    <div className="flex-1 overflow-hidden rounded-lg border">
                      <div className="h-full overflow-y-auto">
                        <table className="w-full text-sm table-fixed">
                          <colgroup>
                            <col className="w-[5%]" />
                            <col className="w-[28%]" />
                            <col className="w-[8%]" />
                            <col className="w-[14%]" />
                            <col className="w-[20%]" />
                          </colgroup>
                          <thead className="bg-muted/50 sticky top-0 z-10">
                            <tr>
                              {HIST_COLS.map(({ key, label }) => (
                                <th key={key} className="text-left px-3 py-2 font-medium">
                                  <button
                                    type="button"
                                    onClick={() => handleSortHist(key)}
                                    className="flex items-center gap-1 hover:text-foreground transition-colors text-muted-foreground data-[active]:text-foreground"
                                    data-active={sortHistCol === key ? "" : undefined}
                                  >
                                    {label}
                                    {SortIconHist(key)}
                                  </button>
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {sortedHistory.map((ev) => (
                              <tr key={`${ev.annotation_session_uuid}-${ev.event_type}`} className="hover:bg-muted/30">
                                <td className="px-3 py-3 font-mono text-muted-foreground"><span className="block truncate">{ev.dataset_index}</span></td>
                                <td className="px-3 py-3 font-medium overflow-hidden"><span className="block truncate" title={ev.image_set_name}>{ev.image_set_name}</span></td>
                                <td className="px-3 py-3 text-muted-foreground overflow-hidden"><span className="block truncate">{ev.icd_code ?? "—"}</span></td>
                                <td className="px-3 py-3 overflow-hidden">
                                  <Badge variant={EVENT_VARIANTS[ev.event_type] ?? "outline"}>
                                    {ev.event_type === "submitted" && <CheckCircle2 className="h-3 w-3 mr-1" />}
                                    {ev.event_type === "draft_saved" && <FileEdit className="h-3 w-3 mr-1" />}
                                    {ev.event_type === "draft_deleted" && <Trash2 className="h-3 w-3 mr-1" />}
                                    {EVENT_LABELS[ev.event_type]}
                                  </Badge>
                                </td>
                                <td className="px-3 py-3 text-muted-foreground text-xs overflow-hidden">
                                  <span className="flex items-center gap-1">
                                    <Clock className="h-3 w-3 shrink-0" />
                                    {formatDateTime(ev.timestamp)}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>
        )}
      </div>

      {/* ── Keyboard shortcut hint panel ── */}
      {showKbdHints && dashboardHintOpen ? (
        <div className="fixed bottom-4 right-2 w-56 rounded-lg border border-border bg-background/95 shadow-xl backdrop-blur-sm z-30 text-xs">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <span className="font-semibold text-muted-foreground flex items-center gap-1.5">
              <Keyboard className="h-3.5 w-3.5" /> Shortcuts
            </span>
            <button type="button" onClick={() => setDashboardHintOpen(false)} className="text-muted-foreground hover:text-foreground transition-colors" title="Minimize">
              <Minus className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="px-3 py-2 space-y-0.5">
            {([
              { combo: "Tab / Shift+Tab", desc: "Cycle tabs" },
              { combo: "1 / 2 / 3",       desc: "Jump to tab" },
              { combo: "A / R",            desc: "Switch mode" },
              null,
              { combo: `${navLabel("up", navMode)} / ${navLabel("down", navMode)}`, desc: "Navigate rows" },
              { combo: "Space / Enter",    desc: "Toggle row" },
              { combo: "V",                desc: "Visual mode" },
              { combo: "Ctrl+A",           desc: "Select all" },
              { combo: "Shift+Q",          desc: "First pending" },
              null,
              { combo: "Shift+A / R / P",  desc: "Launch sets" },
              { combo: "Del / Shift+D",    desc: "Delete drafts" },
              { combo: "Esc",              desc: "Clear / deselect" },
            ] as ({ combo: string; desc: string } | null)[]).map((row, i) =>
              row === null
                ? <hr key={i} className="border-border my-1" />
                : (
                  <div key={row.combo} className="flex items-center justify-between gap-2 py-0.5">
                    <span className="text-muted-foreground">{row.desc}</span>
                    <kbd className="font-mono border border-primary/40 bg-primary text-black px-1.5 py-0.5 rounded text-xs leading-none shrink-0">{row.combo}</kbd>
                  </div>
                )
            )}
          </div>
        </div>
      ) : showKbdHints ? (
        <button
          type="button"
          onClick={() => setDashboardHintOpen(true)}
          className="fixed right-0 bottom-32 rounded-l-md border border-r-0 border-border bg-background/95 backdrop-blur-sm shadow-md px-1.5 py-3 text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors z-30"
          title="Show shortcuts"
        >
          <Keyboard className="h-4 w-4" />
        </button>
      ) : null}

      {/* ── Delete drafts confirm dialog ── */}
      {confirmDeleteDrafts && (
        <ConfirmDialog
          title={`Delete ${selectedDrafts.size} draft(s)?`}
          body="This will permanently remove the saved annotation data. This cannot be undone."
          layout="horizontal"
          defaultFocusIndex={1}
          buttons={[
            { label: "Yes. Delete", onClick: handleDeleteDrafts, className: "bg-red-600 hover:bg-red-700 text-white" },
            { label: "No. Cancel", onClick: () => setConfirmDeleteDrafts(false), className: "" },
          ]}
        />
      )}

      {/* ── Large selection warning dialog ── */}
      {confirmLaunch && (
        <ConfirmDialog
          title={
            <span className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-400 shrink-0" />
              Large selection
            </span>
          }
          body={
            <>
              You are about to open{" "}
              <span className="font-medium text-foreground">{confirmLaunch.count}</span>{" "}
              image sets. This may affect system stability.
            </>
          }
          layout="horizontal"
          defaultFocusIndex={1}
          buttons={[
            {
              label: "Yes. Proceed",
              className: "bg-blue-600 hover:bg-blue-700 text-white",
              onClick: () => {
                const type = confirmLaunch.type;
                setConfirmLaunch(null);
                if (type === "annotate") doAnnotateSets();
                else if (type === "read") doReadSets();
                else doPreviewSets();
              },
            },
            { label: "No. Cancel", onClick: () => setConfirmLaunch(null), className: "" },
          ]}
        />
      )}
    </div>
  );
}
