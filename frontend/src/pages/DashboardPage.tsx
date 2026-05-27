import { useEffect, useState } from "react";
import { Check, PlayCircle, Trash2, Clock, CheckCircle2, FileEdit, Stethoscope, Globe, Layers, BookOpen, ScanEye, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
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

type Tab = "image-sets" | "drafts" | "history";
type SortDir = "asc" | "desc";
type SortCol     = "index" | "name" | "patient_id" | "icd" | "slices" | "evaluators" | "status";
type DraftSortCol = "index" | "name" | "patient_id" | "icd" | "slices" | "annotated" | "draft_time";
type HistSortCol  = "index" | "name" | "icd" | "event" | "time";

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

function Checkbox({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      onClick={(e) => { e.stopPropagation(); onChange(); }}
      className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors shrink-0 ${
        checked
          ? "bg-primary border-primary"
          : "border-muted-foreground/40 bg-transparent hover:border-primary"
      }`}
    >
      {checked && <Check className="w-2.5 h-2.5 text-primary-foreground" strokeWidth={3} />}
    </button>
  );
}

const STAT_COLORS = {
  blue:   { card: "border-blue-500/40 bg-blue-500/5",   icon: "text-blue-400",   value: "text-blue-400"   },
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
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

const EVENT_VARIANTS: Record<string, "success" | "warning" | "destructive" | "outline"> = {
  submitted: "success",
  draft_saved: "warning",
  draft_deleted: "destructive",
};
const EVENT_LABELS: Record<string, string> = {
  submitted: "Submitted",
  draft_saved: "Draft Saved",
  draft_deleted: "Draft Deleted",
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("image-sets");
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [imageSets, setImageSets] = useState<ImageSetWithProgress[]>([]);
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [starting, setStarting] = useState(false);
  const [deletingDrafts, setDeletingDrafts] = useState(false);
  const [confirmDeleteDrafts, setConfirmDeleteDrafts] = useState(false);
  const [selectedSets, setSelectedSets] = useState<Set<string>>(new Set());
  const [selectedDrafts, setSelectedDrafts] = useState<Set<string>>(new Set());
  const [sortCol, setSortCol] = useState<SortCol>("index");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [sortDraftCol, setSortDraftCol] = useState<DraftSortCol>("draft_time");
  const [sortDraftDir, setSortDraftDir] = useState<SortDir>("desc");
  const [sortHistCol, setSortHistCol] = useState<HistSortCol>("time");
  const [sortHistDir, setSortHistDir] = useState<SortDir>("desc");
  const { mode, setMode } = useLabelStore();

  // In reader mode, only show sets that have data to read
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

  const statusRank = (s: ImageSetWithProgress) => s.evaluated_by_me ? 2 : s.in_draft_by_me ? 1 : 0;

  const sortedSets = [...visibleSets].sort((a, b) => {
    // Selected rows float to top
    const sel = (selectedSets.has(b.uuid) ? 1 : 0) - (selectedSets.has(a.uuid) ? 1 : 0);
    if (sel !== 0) return sel;
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
  });

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

  const handleAnnotateSets = async () => {
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

  const handleReadSets = () => {
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

  const handlePreviewSets = () => {
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

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6" style={{ zoom: 1.2 }}>
      {/* Header */}
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

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
        <div className="space-y-4">
          {/* Mode toggle + Tab bar */}
          <div className="flex items-center justify-between gap-4 border-b border-border pb-0">
            <div className="flex gap-1">

              {(["image-sets", "drafts", "history"] as Tab[]).map((tab) => {
                const labels: Record<Tab, string> = { "image-sets": "Image Sets", drafts: `Drafts (${drafts.length})`, history: "History" };
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
                    {labels[tab]}
                  </button>
                );
              })}
            </div>
            {/* Mode toggle — only shown on image-sets and drafts tabs */}
            {(activeTab === "image-sets" || activeTab === "drafts") && (
              <div className="flex items-center gap-1 rounded-lg border border-border p-0.5 mb-1">
                <WithTooltip
                  content="Start or continue scoring image sets"
                  side="bottom"
                >
                  <button
                    type="button"
                    onClick={() => { setMode("annotate"); setSelectedSets(new Set()); setSelectedDrafts(new Set()); }}
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                      mode === "annotate" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <PlayCircle className="h-3.5 w-3.5" /> Annotate
                  </button>
                </WithTooltip>
                <WithTooltip
                  content="Review your submitted or saved annotations (read-only)"
                  side="bottom"
                >
                  <button
                    type="button"
                    onClick={() => { setMode("read"); setSelectedSets(new Set()); setSelectedDrafts(new Set()); }}
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                      mode === "read" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <BookOpen className="h-3.5 w-3.5" /> Reader
                  </button>
                </WithTooltip>
              </div>
            )}
          </div>

          {/* ── Image Sets tab ── */}
          {activeTab === "image-sets" && (
            <div className="space-y-3">
              <div className={`rounded-lg border px-4 py-3 text-sm flex items-center justify-between gap-4 transition-colors ${
                selectedSets.size > 0 ? "border-primary bg-primary/5" : "border-border bg-muted/30"
              }`}>
                {selectedSets.size === 0 ? (
                  <span className="text-muted-foreground">
                    {mode === "read" ? "Choose annotated or drafted sets to read" : "Choose image sets to annotate"}
                  </span>
                ) : (
                  <>
                    <span>
                      You have chosen sets:{" "}
                      <span className="font-mono font-medium">{chosenIndices.join(", ")}</span>
                    </span>
                    {mode === "read" ? (
                      <Button size="sm" className="gap-1.5 shrink-0" onClick={handleReadSets}>
                        <BookOpen className="h-4 w-4" /> Read
                      </Button>
                    ) : (
                      <div className="flex gap-2">
                        <WithTooltip content="Browse images without starting an annotation session" side="top">
                          <Button size="sm" variant="outline" className="gap-1.5 shrink-0 border-orange-500/60 text-orange-400 hover:bg-orange-500/10" onClick={handlePreviewSets}>
                            <ScanEye className="h-4 w-4" /> Preview
                          </Button>
                        </WithTooltip>
                        <Button size="sm" className="gap-1.5 shrink-0" disabled={starting} onClick={handleAnnotateSets}>
                          <PlayCircle className="h-4 w-4" />
                          {starting ? "Starting…" : "Annotate"}
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
                <div className="rounded-lg border overflow-hidden">
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
                    <thead className="bg-muted/50">
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
                      {sortedSets.map((s) => (
                        <tr key={s.uuid} className={`transition-colors cursor-pointer ${selectedSets.has(s.uuid) ? "bg-primary/5" : "hover:bg-muted/30"}`} onClick={() => toggleSet(s.uuid)}>
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
              )}
            </div>
          )}

          {/* ── Drafts tab ── */}
          {activeTab === "drafts" && (
            <div className="space-y-3">
              {/* Action bar */}
              <div className={`rounded-lg border px-4 py-3 text-sm flex items-center justify-between gap-4 transition-colors ${
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
                <div className="rounded-lg border overflow-hidden">
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
                    <thead className="bg-muted/50">
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
                        <tr key={d.annotation_session_uuid} className={`transition-colors cursor-pointer ${selectedDrafts.has(d.annotation_session_uuid) ? "bg-primary/5" : "hover:bg-muted/30"}`} onClick={() => toggleDraft(d.annotation_session_uuid)}>
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
              )}
            </div>
          )}

          {/* ── History tab ── */}
          {activeTab === "history" && (
            <div className="space-y-3">
              {history.length === 0 ? (
                <p className="text-muted-foreground text-sm">No activity yet.</p>
              ) : (
                <div className="rounded-lg border overflow-hidden">
                  <table className="w-full text-sm table-fixed">
                    <colgroup>
                      <col className="w-[5%]" />
                      <col className="w-[28%]" />
                      <col className="w-[8%]" />
                      <col className="w-[14%]" />
                      <col className="w-[20%]" />
                    </colgroup>
                    <thead className="bg-muted/50">
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
                      {sortedHistory.map((e) => (
                        <tr key={`${e.annotation_session_uuid}-${e.event_type}`} className="hover:bg-muted/30">
                          <td className="px-3 py-3 font-mono text-muted-foreground"><span className="block truncate">{e.dataset_index}</span></td>
                          <td className="px-3 py-3 font-medium overflow-hidden"><span className="block truncate" title={e.image_set_name}>{e.image_set_name}</span></td>
                          <td className="px-3 py-3 text-muted-foreground overflow-hidden"><span className="block truncate">{e.icd_code ?? "—"}</span></td>
                          <td className="px-3 py-3 overflow-hidden">
                            <Badge variant={EVENT_VARIANTS[e.event_type] ?? "outline"}>
                              {e.event_type === "submitted" && <CheckCircle2 className="h-3 w-3 mr-1" />}
                              {e.event_type === "draft_saved" && <FileEdit className="h-3 w-3 mr-1" />}
                              {e.event_type === "draft_deleted" && <Trash2 className="h-3 w-3 mr-1" />}
                              {EVENT_LABELS[e.event_type]}
                            </Badge>
                          </td>
                          <td className="px-3 py-3 text-muted-foreground text-xs overflow-hidden">
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3 shrink-0" />
                              {formatDateTime(e.timestamp)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Delete draft confirm dialog ── */}
      {confirmDeleteDrafts && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-background border border-border rounded-lg p-6 w-80 space-y-4 shadow-xl">
            <p className="text-base font-semibold">Delete {selectedDrafts.size} draft(s)?</p>
            <p className="text-sm text-muted-foreground">This will permanently remove the saved annotation data. This cannot be undone.</p>
            <div className="flex gap-3">
              <Button className="flex-1 bg-red-600 hover:bg-red-700 text-white" onClick={handleDeleteDrafts}>
                Yes. Delete
              </Button>
              <Button variant="outline" className="flex-1" onClick={() => setConfirmDeleteDrafts(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
