import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { datasetsApi, patientsApi } from "@/lib/api";
import type { DataSet, Patient } from "@/lib/types";

export default function PatientsPage() {
  const [datasets, setDatasets] = useState<DataSet[]>([]);
  const [selectedDataset, setSelectedDataset] = useState("");
  const [patients, setPatients] = useState<Patient[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ patient_id: "", category: "", age: "", gender: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    datasetsApi.list(true).then(r => {
      setDatasets(r.data);
      if (r.data.length > 0) setSelectedDataset(r.data[0].dataset_uuid);
    }).catch(() => toast.error("Failed to load datasets"));
  }, []);

  useEffect(() => {
    if (!selectedDataset) return;
    patientsApi.listByDataset(selectedDataset).then(r => setPatients(r.data)).catch(() => toast.error("Failed to load patients"));
  }, [selectedDataset]);

  const createPatient = async () => {
    if (!form.patient_id.trim() || !selectedDataset) { toast.error("Patient ID required"); return; }
    setSaving(true);
    try {
      await patientsApi.create({
        patient_id: form.patient_id.trim(),
        dataset_uuid: selectedDataset,
        category: form.category || null,
        age: form.age ? parseInt(form.age) : null,
        gender: form.gender || null,
      });
      toast.success("Patient created");
      setOpen(false);
      setForm({ patient_id: "", category: "", age: "", gender: "" });
      patientsApi.listByDataset(selectedDataset).then(r => setPatients(r.data));
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
          <h1 className="text-xl font-semibold">Patients</h1>
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
            <Button size="sm" className="gap-1.5" disabled={!selectedDataset}><Plus className="h-4 w-4" /> Add Patient</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Add Patient</DialogTitle></DialogHeader>
            <div className="space-y-3 mt-2">
              {[["patient_id", "Patient ID *"], ["category", "Category"], ["age", "Age"]].map(([f, l]) => (
                <div key={f} className="space-y-1">
                  <Label>{l}</Label>
                  <Input type={f === "age" ? "number" : "text"} value={form[f as keyof typeof form]} onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))} />
                </div>
              ))}
              <div className="space-y-1">
                <Label>Gender</Label>
                <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" value={form.gender} onChange={e => setForm(p => ({ ...p, gender: e.target.value }))}>
                  <option value="">— not specified —</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <Button className="w-full" disabled={saving} onClick={createPatient}>{saving ? "Adding…" : "Add Patient"}</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              {["Patient ID", "Category", "Age", "Gender"].map(h => (
                <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {patients.map(p => (
              <tr key={p.patient_uuid} className="hover:bg-muted/30">
                <td className="px-4 py-3 font-mono text-xs">{p.patient_id}</td>
                <td className="px-4 py-3 text-muted-foreground">{p.category ?? "—"}</td>
                <td className="px-4 py-3 text-muted-foreground">{p.age ?? "—"}</td>
                <td className="px-4 py-3 text-muted-foreground">{p.gender ?? "—"}</td>
              </tr>
            ))}
            {patients.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">No patients in this dataset</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
