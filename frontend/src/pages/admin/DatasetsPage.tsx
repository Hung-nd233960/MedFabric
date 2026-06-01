import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Plus, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { datasetsApi } from "@/lib/api";
import type { DataSet } from "@/lib/types";

type SortCol = "name" | "status" | "progress" | "created";
type SortDir = "asc" | "desc";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<DataSet[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [saving, setSaving] = useState(false);
  const [sortCol, setSortCol] = useState<SortCol>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const handleSort = (col: SortCol) => {
    if (sortCol === col) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortCol(col); setSortDir("asc"); }
  };

  const SortIcon = (col: SortCol) =>
    sortCol !== col
      ? <ArrowUpDown className="h-3 w-3 opacity-40 shrink-0" />
      : sortDir === "asc" ? <ArrowUp className="h-3 w-3 shrink-0" /> : <ArrowDown className="h-3 w-3 shrink-0" />;

  const sorted = useMemo(() => [...datasets].sort((a, b) => {
    let cmp = 0;
    switch (sortCol) {
      case "name":     cmp = a.name.localeCompare(b.name); break;
      case "status":   cmp = (a.is_active ? 1 : 0) - (b.is_active ? 1 : 0); break;
      case "progress": cmp = (a.global_progress / Math.max(a.total_image_sets, 1)) - (b.global_progress / Math.max(b.total_image_sets, 1)); break;
      case "created":  cmp = a.created_at.localeCompare(b.created_at); break;
    }
    return sortDir === "asc" ? cmp : -cmp;
  }), [datasets, sortCol, sortDir]);

  const load = async () => {
    try {
      const res = await datasetsApi.list(false);
      setDatasets(res.data);
    } catch {
      toast.error("Failed to load datasets");
    }
  };

  useEffect(() => { load(); }, []);

  const toggleActive = async (ds: DataSet) => {
    try {
      await datasetsApi.update(ds.dataset_uuid, { is_active: !ds.is_active });
      load();
    } catch {
      toast.error("Failed to update dataset");
    }
  };

  const createDataset = async () => {
    if (!form.name.trim()) { toast.error("Name required"); return; }
    setSaving(true);
    try {
      await datasetsApi.create({ name: form.name.trim(), description: form.description || undefined });
      toast.success("Dataset created");
      setOpen(false);
      setForm({ name: "", description: "" });
      load();
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed");
    } finally {
      setSaving(false);
    }
  };

  const Th = ({ col, label }: { col: SortCol; label: string }) => (
    <th className="text-left px-4 py-3 font-medium">
      <button type="button" onClick={() => handleSort(col)} className="flex items-center gap-1 hover:text-foreground transition-colors text-muted-foreground data-[active]:text-foreground" data-active={sortCol === col ? "" : undefined}>
        {label}{SortIcon(col)}
      </button>
    </th>
  );

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Datasets</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm" className="gap-1.5"><Plus className="h-4 w-4" /> New Dataset</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create Dataset</DialogTitle></DialogHeader>
            <div className="space-y-3 mt-2">
              <div className="space-y-1"><Label>Name</Label><Input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))} /></div>
              <div className="space-y-1"><Label>Description</Label><Textarea rows={3} value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} /></div>
              <Button className="w-full" disabled={saving} onClick={createDataset}>{saving ? "Creating…" : "Create"}</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <Th col="name" label="Name" />
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">Description</th>
              <Th col="status" label="Status" />
              <Th col="progress" label="Progress" />
              <Th col="created" label="Created" />
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {sorted.map((d) => (
              <tr key={d.dataset_uuid} className="hover:bg-muted/30">
                <td className="px-4 py-3 font-medium">{d.name}</td>
                <td className="px-4 py-3 text-muted-foreground text-xs max-w-xs truncate">{d.description ?? "—"}</td>
                <td className="px-4 py-3"><Badge variant={d.is_active ? "success" : "secondary"}>{d.is_active ? "Active" : "Inactive"}</Badge></td>
                <td className="px-4 py-3">
                  <div className="text-sm font-medium">{d.global_progress}/{d.total_image_sets}</div>
                  {d.total_image_sets > 0 && <div className="text-xs text-muted-foreground">{Math.round(d.global_progress / d.total_image_sets * 100)}%</div>}
                </td>
                <td className="px-4 py-3 text-muted-foreground text-xs">{new Date(d.created_at).toLocaleDateString(undefined, { timeZone: "Asia/Ho_Chi_Minh" })}</td>
                <td className="px-4 py-3 text-right">
                  <Button variant="ghost" size="sm" onClick={() => toggleActive(d)}>{d.is_active ? "Deactivate" : "Reactivate"}</Button>
                </td>
              </tr>
            ))}
            {sorted.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No datasets</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
