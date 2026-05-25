import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { datasetsApi, imageSetsApi, patientsApi } from "@/lib/api";
import type { DataSet, ImageSetWithProgress, Patient } from "@/lib/types";

export default function ImageSetsPage() {
  const [datasets, setDatasets] = useState<DataSet[]>([]);
  const [selectedDataset, setSelectedDataset] = useState("");
  const [imageSets, setImageSets] = useState<ImageSetWithProgress[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    image_set_name: "", folder_path: "", patient_uuid: "",
    image_window_level: "", image_window_width: "", icd_code: "", description: "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    datasetsApi.list(true).then(r => {
      setDatasets(r.data);
      if (r.data.length > 0) setSelectedDataset(r.data[0].dataset_uuid);
    });
  }, []);

  useEffect(() => {
    if (!selectedDataset) return;
    imageSetsApi.listByDataset(selectedDataset).then(r => setImageSets(r.data));
    patientsApi.listByDataset(selectedDataset).then(r => {
      setPatients(r.data);
      if (r.data.length > 0) setForm(p => ({ ...p, patient_uuid: r.data[0].patient_uuid }));
    });
  }, [selectedDataset]);

  const createImageSet = async () => {
    if (!form.image_set_name.trim() || !form.folder_path.trim() || !form.patient_uuid) {
      toast.error("Name, folder path, and patient are required");
      return;
    }
    setSaving(true);
    try {
      await imageSetsApi.create({
        ...form,
        dataset_uuid: selectedDataset,
        image_window_level: form.image_window_level ? parseInt(form.image_window_level) : null,
        image_window_width: form.image_window_width ? parseInt(form.image_window_width) : null,
        icd_code: form.icd_code || null,
        description: form.description || null,
      });
      toast.success("Image set registered");
      setOpen(false);
      imageSetsApi.listByDataset(selectedDataset).then(r => setImageSets(r.data));
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">Image Sets</h1>
          <select
            className="h-8 rounded-md border border-input bg-transparent px-3 text-sm"
            value={selectedDataset}
            onChange={e => setSelectedDataset(e.target.value)}
          >
            {datasets.map(d => <option key={d.dataset_uuid} value={d.dataset_uuid}>{d.name}</option>)}
          </select>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm" className="gap-1.5" disabled={!selectedDataset}>
              <Plus className="h-4 w-4" /> Register Image Set
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader><DialogTitle>Register Image Set</DialogTitle></DialogHeader>
            <div className="space-y-3 mt-2 max-h-[70vh] overflow-y-auto">
              <div className="space-y-1"><Label>Name *</Label><Input value={form.image_set_name} onChange={e => setForm(p => ({ ...p, image_set_name: e.target.value }))} /></div>
              <div className="space-y-1">
                <Label>Patient *</Label>
                <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" value={form.patient_uuid} onChange={e => setForm(p => ({ ...p, patient_uuid: e.target.value }))}>
                  {patients.map(p => <option key={p.patient_uuid} value={p.patient_uuid}>{p.patient_id}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label className="flex items-center gap-1.5"><FolderOpen className="h-3.5 w-3.5" /> Server folder path *</Label>
                <Input placeholder="/data/datasets/patient01/scan01" value={form.folder_path} onChange={e => setForm(p => ({ ...p, folder_path: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1"><Label>WL (auto if empty)</Label><Input type="number" value={form.image_window_level} onChange={e => setForm(p => ({ ...p, image_window_level: e.target.value }))} /></div>
                <div className="space-y-1"><Label>WW (auto if empty)</Label><Input type="number" value={form.image_window_width} onChange={e => setForm(p => ({ ...p, image_window_width: e.target.value }))} /></div>
              </div>
              <div className="space-y-1"><Label>ICD Code</Label><Input value={form.icd_code} onChange={e => setForm(p => ({ ...p, icd_code: e.target.value }))} /></div>
              <div className="space-y-1"><Label>Description</Label><Input value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} /></div>
              <Button className="w-full" disabled={saving} onClick={createImageSet}>{saving ? "Registering…" : "Register"}</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>{["Name", "ICD", "Slices", "WL/WW", "Evaluators", "Status"].map(h => <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-border">
            {imageSets.map(s => (
              <tr key={s.uuid} className="hover:bg-muted/30">
                <td className="px-4 py-3 font-medium">{s.image_set_name}</td>
                <td className="px-4 py-3 text-muted-foreground">{s.icd_code ?? "—"}</td>
                <td className="px-4 py-3">{s.num_images}</td>
                <td className="px-4 py-3 text-muted-foreground text-xs font-mono">
                  {s.image_window_level ?? "—"} / {s.image_window_width ?? "—"}
                </td>
                <td className="px-4 py-3">{s.total_evaluators}</td>
                <td className="px-4 py-3"><Badge variant={s.is_active ? "success" : "secondary"}>{s.is_active ? "Active" : "Inactive"}</Badge></td>
              </tr>
            ))}
            {imageSets.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No image sets</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
