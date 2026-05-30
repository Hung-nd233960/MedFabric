import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Link2, Unlink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { adminApi, datasetsApi } from "@/lib/api";
import type { DataSet, Doctor, DoctorDatasetAssignment } from "@/lib/types";

interface DoctorWithAssignment extends Doctor {
  assignment?: DoctorDatasetAssignment;
  assignedDataset?: string;
}

export default function AssignmentsPage() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [datasets, setDatasets] = useState<DataSet[]>([]);
  const [rows, setRows] = useState<DoctorWithAssignment[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ doctor_uuid: "", dataset_uuid: "" });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    const [dRes, dsRes] = await Promise.all([adminApi.listDoctors(false), datasetsApi.list(true)]);
    const docs: Doctor[] = dRes.data;
    const dsets: DataSet[] = dsRes.data;
    setDoctors(docs);
    setDatasets(dsets);

    const enriched: DoctorWithAssignment[] = await Promise.all(
      docs.map(async (d) => {
        try {
          const aRes = await adminApi.getAssignment(d.uuid);
          const assignment: DoctorDatasetAssignment = aRes.data;
          const ds = dsets.find(ds => ds.dataset_uuid === assignment.dataset_uuid);
          return { ...d, assignment, assignedDataset: ds?.name };
        } catch {
          return { ...d };
        }
      })
    );
    setRows(enriched);
    if (docs.length > 0) setForm(p => ({ ...p, doctor_uuid: docs[0].uuid }));
    if (dsets.length > 0) setForm(p => ({ ...p, dataset_uuid: dsets[0].dataset_uuid }));
  };

  useEffect(() => { load(); }, []);

  const assign = async () => {
    if (!form.doctor_uuid || !form.dataset_uuid) return;
    setSaving(true);
    try {
      await adminApi.assign({ doctor_uuid: form.doctor_uuid, dataset_uuid: form.dataset_uuid });
      toast.success("Dataset assigned");
      setOpen(false);
      load();
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed");
    } finally {
      setSaving(false);
    }
  };

  const revoke = async (row: DoctorWithAssignment) => {
    if (!row.assignment) return;
    try {
      await adminApi.revokeAssignment(row.assignment.id);
      toast.success("Assignment revoked");
      load();
    } catch {
      toast.error("Failed to revoke");
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Dataset Assignments</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm" className="gap-1.5"><Link2 className="h-4 w-4" /> Assign Dataset</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Assign Dataset to Doctor</DialogTitle></DialogHeader>
            <div className="space-y-3 mt-2">
              <div className="space-y-1">
                <Label>Doctor</Label>
                <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" value={form.doctor_uuid} onChange={e => setForm(p => ({ ...p, doctor_uuid: e.target.value }))}>
                  {doctors.map(d => <option key={d.uuid} value={d.uuid}>{d.username}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label>Dataset</Label>
                <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm" value={form.dataset_uuid} onChange={e => setForm(p => ({ ...p, dataset_uuid: e.target.value }))}>
                  {datasets.map(d => <option key={d.dataset_uuid} value={d.dataset_uuid}>{d.name}</option>)}
                </select>
              </div>
              <p className="text-xs text-muted-foreground">Previous active assignment for this doctor will be replaced.</p>
              <Button className="w-full" disabled={saving} onClick={assign}>{saving ? "Assigning…" : "Assign"}</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>{["Doctor", "Role", "Assigned Dataset", "Progress", "Since", ""].map(h => <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map(d => (
              <tr key={d.uuid} className="hover:bg-muted/30">
                <td className="px-4 py-3 font-medium">{d.username}</td>
                <td className="px-4 py-3"><Badge variant="secondary">{d.role}</Badge></td>
                <td className="px-4 py-3">
                  {d.assignment ? (
                    <span className="text-primary font-medium">{d.assignedDataset ?? d.assignment.dataset_uuid}</span>
                  ) : (
                    <span className="text-muted-foreground">— none —</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {d.assignment ? (
                    <>
                      <div className="text-sm font-medium">{d.assignment.doctor_progress}/{d.assignment.total_image_sets}</div>
                      {d.assignment.total_image_sets > 0 && (
                        <div className="text-xs text-muted-foreground">
                          {Math.round(d.assignment.doctor_progress / d.assignment.total_image_sets * 100)}%
                        </div>
                      )}
                    </>
                  ) : ""}
                </td>
                <td className="px-4 py-3 text-muted-foreground text-xs">
                  {d.assignment ? new Date(d.assignment.assigned_at).toLocaleDateString(undefined, { timeZone: "Asia/Bangkok" }) : ""}
                </td>
                <td className="px-4 py-3 text-right">
                  {d.assignment && (
                    <Button variant="ghost" size="sm" className="gap-1.5 text-destructive" onClick={() => revoke(d)}>
                      <Unlink className="h-3.5 w-3.5" /> Revoke
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
