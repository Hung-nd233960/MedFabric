import { useEffect, useState } from "react";
import { Check, PlayCircle, Trash2, Clock, CheckCircle2, FileEdit, Stethoscope, Globe, Layers } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { dashboardApi, imageSetsApi, annotationSessionsApi, evaluationsApi } from "@/lib/api";
import type { DashboardStats, DraftItem, HistoryEvent, ImageSetWithProgress } from "@/lib/types";

type Tab = "image-sets" | "drafts" | "history";

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

function StatCard({
  icon: Icon, label, value, pct, sub,
}: {
  icon: React.ElementType; label: string; value: number; pct?: number; sub?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2 flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-bold">{value}</div>
          {pct !== undefined && <div className="text-sm font-medium text-muted-foreground">{pct}%</div>}
        </div>
        {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function formatDateTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("image-sets");
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [imageSets, setImageSets] = useState<ImageSetWithProgress[]>([]);
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [deletingDrafts, setDeletingDrafts] = useState(false);
  const [confirmDeleteDrafts, setConfirmDeleteDrafts] = useState(false);
  const [selectedSets, setSelectedSets] = useState<Set<string>>(new Set());
  const [selectedDrafts, setSelectedDrafts] = useState<Set<string>>(new Set());

  const refreshDraftsAndHistory = async () => {
    try {
      const [draftsRes, histRes] = await Promise.all([
        evaluationsApi.listMyDrafts(),
        annotationSessionsApi.myHistory(),
      ]);
      setDrafts(draftsRes.data);
      setHistory(histRes.data);
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
      } finally {
        setLoading(false);
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
    setSelectedSets(selectedSets.size === imageSets.length ? new Set() : new Set(imageSets.map((s) => s.uuid)));

  const handleAnnotateSets = async () => {
    const chosen = [...imageSets.filter((s) => selectedSets.has(s.uuid))].sort(
      (a, b) => a.dataset_index - b.dataset_index
    );
    const target = chosen.find((s) => !s.evaluated_by_me) ?? chosen[0];
    if (!target) return;
    setStarting(true);
    try {
      const res = await annotationSessionsApi.open(target.uuid);
      const queue = chosen.map((s) => s.uuid).join(",");
      const indices = chosen.map((s) => s.dataset_index).join(",");
      navigate(`/label/${target.uuid}?session=${res.data.annotation_session_uuid}&queue=${queue}&indices=${indices}`);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to start";
      toast.error(msg);
    } finally {
      setStarting(false);
    }
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
      navigate(`/label/${draft.image_set_uuid}?session=${res.data.annotation_session_uuid}&queue=${draft.image_set_uuid}&indices=${draft.dataset_index}`);
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
    const targets = drafts.filter((d) => selectedDrafts.has(d.annotation_session_uuid));
    try {
      await Promise.all(targets.map((d) => evaluationsApi.deleteDraftByImageSet(d.image_set_uuid)));
      setSelectedDrafts(new Set());
      toast.success(`${targets.length} draft(s) deleted.`);
      await refreshDraftsAndHistory();
    } catch {
      toast.error("Failed to delete some drafts.");
    } finally {
      setDeletingDrafts(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-muted-foreground">Loading…</div>;
  }

  const chosenIndices = [...imageSets.filter((s) => selectedSets.has(s.uuid))]
    .sort((a, b) => a.dataset_index - b.dataset_index)
    .map((s) => s.dataset_index);

  const EVENT_LABELS: Record<string, string> = {
    submitted: "Submitted",
    draft_saved: "Draft Saved",
    draft_deleted: "Draft Deleted",
  };
  const EVENT_VARIANTS: Record<string, "success" | "warning" | "destructive" | "outline"> = {
    submitted: "success",
    draft_saved: "warning",
    draft_deleted: "destructive",
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
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
          <StatCard icon={Layers} label="Total Image Sets" value={stats.total_image_sets} />
          <StatCard
            icon={Stethoscope}
            label="My Progress"
            value={stats.my_progress}
            pct={stats.total_image_sets > 0 ? parseFloat((stats.my_progress / stats.total_image_sets * 100).toFixed(2)) : 0}
            sub="sets evaluated by you"
          />
          <StatCard
            icon={Globe}
            label="Global Progress"
            value={stats.global_progress}
            pct={stats.total_image_sets > 0 ? parseFloat((stats.global_progress / stats.total_image_sets * 100).toFixed(2)) : 0}
            sub="unique sets with ≥1 evaluation"
          />
          <StatCard icon={CheckCircle2} label="Remaining" value={Math.max(0, stats.total_image_sets - stats.my_progress)} sub="sets you haven't evaluated" />
        </div>
      )}

      {/* Tabs */}
      {stats?.assigned_dataset && (
        <div className="space-y-4">
          {/* Tab bar */}
          <div className="flex gap-1 border-b border-border">
            {(["image-sets", "drafts", "history"] as Tab[]).map((tab) => {
              const labels: Record<Tab, string> = { "image-sets": "Image Sets", drafts: `Drafts (${drafts.length})`, history: "History" };
              return (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveTab(tab)}
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

          {/* ── Image Sets tab ── */}
          {activeTab === "image-sets" && (
            <div className="space-y-3">
              <div className={`rounded-lg border px-4 py-3 text-sm flex items-center justify-between gap-4 transition-colors ${
                selectedSets.size > 0 ? "border-primary bg-primary/5" : "border-border bg-muted/30"
              }`}>
                {selectedSets.size === 0 ? (
                  <span className="text-muted-foreground">Please choose image sets to annotate</span>
                ) : (
                  <>
                    <span>
                      You have chosen sets:{" "}
                      <span className="font-mono font-medium">{chosenIndices.join(", ")}</span>
                    </span>
                    <Button size="sm" className="gap-1.5 shrink-0" disabled={starting} onClick={handleAnnotateSets}>
                      <PlayCircle className="h-4 w-4" />
                      {starting ? "Starting…" : "Annotate"}
                    </Button>
                  </>
                )}
              </div>

              {imageSets.length === 0 ? (
                <p className="text-muted-foreground text-sm">No image sets found.</p>
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
                        {["Index", "Image Set Name", "Patient ID", "ICD", "Slices", "Evaluators", "Status"].map((h) => (
                          <th key={h} className="text-left px-3 py-3 font-medium truncate">{h}</th>
                        ))}
                        <th className="px-3 py-3 flex justify-end">
                          <Checkbox checked={selectedSets.size === imageSets.length && imageSets.length > 0} onChange={toggleAllSets} />
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {imageSets.map((s) => (
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
                  <span className="text-muted-foreground">Select drafts to annotate or delete</span>
                ) : (
                  <>
                    <span><span className="font-medium">{selectedDrafts.size}</span> draft(s) selected</span>
                    <div className="flex gap-2">
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
                      {selectedDrafts.size === 1 && (() => {
                        const draft = drafts.find((d) => selectedDrafts.has(d.annotation_session_uuid));
                        return draft ? (
                          <Button size="sm" className="gap-1.5" disabled={starting} onClick={() => handleAnnotateDraft(draft)}>
                            <PlayCircle className="h-4 w-4" />
                            {starting ? "Starting…" : "Annotate"}
                          </Button>
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
                        {["Index", "Image Set Name", "Patient ID", "ICD", "Slices", "Annotated", "Draft Time"].map((h) => (
                          <th key={h} className="text-left px-3 py-3 font-medium truncate">{h}</th>
                        ))}
                        <th className="px-3 py-3 flex justify-end">
                          <Checkbox checked={selectedDrafts.size === drafts.length && drafts.length > 0} onChange={toggleAllDrafts} />
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {drafts.map((d) => (
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
                        {["Index", "Image Set Name", "ICD", "Event", "Time"].map((h) => (
                          <th key={h} className="text-left px-3 py-3 font-medium truncate">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {history.map((e) => (
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
