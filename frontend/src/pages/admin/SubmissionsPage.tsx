import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLabelQueueStore } from "@/store/labelQueueStore";
import { toast } from "sonner";
import { BookOpen, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { adminApi, datasetsApi } from "@/lib/api";
import type { DataSet, SubmissionRecord } from "@/lib/types";

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Ho_Chi_Minh" });
}

type SortCol = "index" | "name" | "icd" | "doctor" | "submitted";
type SortDir = "asc" | "desc";

export default function SubmissionsPage() {
  const navigate = useNavigate();
  const [submissions, setSubmissions] = useState<SubmissionRecord[]>([]);
  const [datasets, setDatasets] = useState<DataSet[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string>("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [sortCol, setSortCol] = useState<SortCol>("submitted");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const handleSort = (col: SortCol) => {
    if (sortCol === col) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortCol(col); setSortDir("asc"); }
  };

  const SortIcon = (col: SortCol) =>
    sortCol !== col
      ? <ArrowUpDown className="h-3 w-3 opacity-40 shrink-0" />
      : sortDir === "asc" ? <ArrowUp className="h-3 w-3 shrink-0" /> : <ArrowDown className="h-3 w-3 shrink-0" />;

  const sorted = useMemo(() => [...submissions].sort((a, b) => {
    let cmp = 0;
    switch (sortCol) {
      case "index":     cmp = a.dataset_index - b.dataset_index; break;
      case "name":      cmp = a.image_set_name.localeCompare(b.image_set_name); break;
      case "icd":       cmp = (a.icd_code ?? "").localeCompare(b.icd_code ?? ""); break;
      case "doctor":    cmp = (a.doctor_full_name ?? a.doctor_username).localeCompare(b.doctor_full_name ?? b.doctor_username); break;
      case "submitted": cmp = a.submitted_at.localeCompare(b.submitted_at); break;
    }
    return sortDir === "asc" ? cmp : -cmp;
  }), [submissions, sortCol, sortDir]);

  useEffect(() => {
    datasetsApi.list(false).then((res: { data: DataSet[] }) => setDatasets(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setSelected(new Set());
    adminApi.listSubmissions(selectedDataset || undefined)
      .then((res: { data: SubmissionRecord[] }) => setSubmissions(res.data))
      .catch(() => toast.error("Failed to load submissions"))
      .finally(() => setLoading(false));
  }, [selectedDataset]);

  const toggle = (uuid: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(uuid)) next.delete(uuid); else next.add(uuid);
      return next;
    });
  };

  const handleRead = () => {
    const picked = submissions.filter((s) => selected.has(s.annotation_session_uuid));
    if (!picked.length) return;
    useLabelQueueStore.getState().enter({
      queue: picked.map((s) => s.image_set_uuid),
      currentPos: 0,
      indices: picked.map((s) => s.dataset_index),
      sources: picked.map(() => "submission"),
      sessionUuid: null,
      adminDoctors: picked.map((s) => s.doctor_uuid),
      isReadMode: true,
      isPreviewMode: false,
    });
    navigate("/label");
  };

  const allChecked = submissions.length > 0 && submissions.every((s) => selected.has(s.annotation_session_uuid));
  const toggleAll = () => {
    if (allChecked) setSelected(new Set());
    else setSelected(new Set(submissions.map((s) => s.annotation_session_uuid)));
  };

  const Th = ({ col, label, right }: { col: SortCol; label: string; right?: boolean }) => (
    <th className={`px-4 py-3 font-medium ${right ? "text-right" : "text-left"}`}>
      <button type="button" onClick={() => handleSort(col)} className="flex items-center gap-1 hover:text-foreground transition-colors text-muted-foreground data-[active]:text-foreground" data-active={sortCol === col ? "" : undefined}>
        {label}{SortIcon(col)}
      </button>
    </th>
  );

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Submissions</h1>
        <div className="flex items-center gap-3">
          {selected.size > 0 && (
            <Button size="sm" className="gap-1.5" onClick={handleRead}>
              <BookOpen className="h-4 w-4" /> Read {selected.size > 1 ? `(${selected.size})` : ""}
            </Button>
          )}
          <div className="flex items-center gap-2">
            <label className="text-sm text-muted-foreground">Dataset:</label>
            <select className="h-8 rounded-md border border-input bg-transparent px-2 text-sm" value={selectedDataset} onChange={(e) => setSelectedDataset(e.target.value)}>
              <option value="">All datasets</option>
              {datasets.map((d) => <option key={d.dataset_uuid} value={d.dataset_uuid}>{d.name}</option>)}
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-muted-foreground text-sm">Loading…</div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <Th col="index" label="#" />
                <Th col="name" label="Image Set" />
                <Th col="icd" label="ICD" />
                <Th col="doctor" label="Doctor" />
                <Th col="submitted" label="Submitted" />
                <th className="px-4 py-3 text-right">
                  {submissions.length > 0 && <Checkbox checked={allChecked} onChange={toggleAll} />}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sorted.map((s) => (
                <tr key={s.annotation_session_uuid} className={`hover:bg-muted/30 cursor-pointer ${selected.has(s.annotation_session_uuid) ? "bg-muted/50" : ""}`} onClick={() => toggle(s.annotation_session_uuid)}>
                  <td className="px-4 py-3 font-mono text-muted-foreground">{s.dataset_index}</td>
                  <td className="px-4 py-3 font-medium">{s.image_set_name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{s.icd_code ?? "—"}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium">{s.doctor_full_name ?? s.doctor_username}</div>
                    {s.doctor_full_name && <div className="text-xs text-muted-foreground">{s.doctor_username}</div>}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{formatDateTime(s.submitted_at)}</td>
                  <td className="px-4 py-3 text-right"><Checkbox checked={selected.has(s.annotation_session_uuid)} onChange={() => toggle(s.annotation_session_uuid)} /></td>
                </tr>
              ))}
              {sorted.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No submissions found</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
