import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { datasetsApi } from "@/lib/api";
import type { DataSet } from "@/lib/types";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<DataSet[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [saving, setSaving] = useState(false);

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
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

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
              <th className="text-left px-4 py-3 font-medium">Name</th>
              <th className="text-left px-4 py-3 font-medium">Description</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
              <th className="text-left px-4 py-3 font-medium">Progress</th>
              <th className="text-left px-4 py-3 font-medium">Created</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {datasets.map((d) => (
              <tr key={d.dataset_uuid} className="hover:bg-muted/30">
                <td className="px-4 py-3 font-medium">{d.name}</td>
                <td className="px-4 py-3 text-muted-foreground text-xs max-w-xs truncate">{d.description ?? "—"}</td>
                <td className="px-4 py-3"><Badge variant={d.is_active ? "success" : "secondary"}>{d.is_active ? "Active" : "Inactive"}</Badge></td>
                <td className="px-4 py-3">
                  <div className="text-sm font-medium">{d.global_progress}/{d.total_image_sets}</div>
                  {d.total_image_sets > 0 && (
                    <div className="text-xs text-muted-foreground">
                      {Math.round(d.global_progress / d.total_image_sets * 100)}%
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-muted-foreground text-xs">{new Date(d.created_at).toLocaleDateString(undefined, { timeZone: "Asia/Bangkok" })}</td>
                <td className="px-4 py-3 text-right">
                  <Button variant="ghost" size="sm" onClick={() => toggleActive(d)}>
                    {d.is_active ? "Deactivate" : "Reactivate"}
                  </Button>
                </td>
              </tr>
            ))}
            {datasets.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No datasets</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
