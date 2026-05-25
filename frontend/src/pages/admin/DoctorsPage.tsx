import { useEffect, useState } from "react";
import { toast } from "sonner";
import { UserPlus, ShieldOff, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { adminApi } from "@/lib/api";
import type { Doctor } from "@/lib/types";

export default function DoctorsPage() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [showInactive, setShowInactive] = useState(false);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ username: "", password: "", email: "", role: "Doctor" });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const res = await adminApi.listDoctors(showInactive);
      setDoctors(res.data);
    } catch {
      toast.error("Failed to load doctors");
    }
  };

  useEffect(() => { load(); }, [showInactive]);

  const toggleActive = async (doctor: Doctor) => {
    try {
      await adminApi.updateDoctor(doctor.uuid, { is_active: !doctor.is_active });
      toast.success(`Doctor ${doctor.is_active ? "deactivated" : "reactivated"}`);
      load();
    } catch {
      toast.error("Failed to update doctor");
    }
  };

  const createDoctor = async () => {
    if (!form.username || !form.password) { toast.error("Username and password required"); return; }
    setSaving(true);
    try {
      await adminApi.createDoctor(form);
      toast.success(`Doctor '${form.username}' created`);
      setOpen(false);
      setForm({ username: "", password: "", email: "", role: "Doctor" });
      load();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to create doctor";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Doctors</h1>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
            <input
              type="checkbox"
              className="rounded"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
            />
            Show inactive
          </label>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-1.5">
                <UserPlus className="h-4 w-4" /> Add Doctor
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Doctor Account</DialogTitle>
              </DialogHeader>
              <div className="space-y-3 mt-2">
                {(["username", "password", "email"] as const).map((f) => (
                  <div key={f} className="space-y-1">
                    <Label className="capitalize">{f}</Label>
                    <Input
                      type={f === "password" ? "password" : "text"}
                      value={form[f]}
                      onChange={(e) => setForm((p) => ({ ...p, [f]: e.target.value }))}
                    />
                  </div>
                ))}
                <div className="space-y-1">
                  <Label>Role</Label>
                  <select
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                    value={form.role}
                    onChange={(e) => setForm((p) => ({ ...p, role: e.target.value }))}
                  >
                    <option value="Doctor">Doctor</option>
                    <option value="Admin">Admin</option>
                  </select>
                </div>
                <Button className="w-full mt-2" disabled={saving} onClick={createDoctor}>
                  {saving ? "Creating…" : "Create"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Username</th>
              <th className="text-left px-4 py-3 font-medium">Email</th>
              <th className="text-left px-4 py-3 font-medium">Role</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
              <th className="text-left px-4 py-3 font-medium">Created</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {doctors.map((d) => (
              <tr key={d.uuid} className="hover:bg-muted/30">
                <td className="px-4 py-3 font-medium">{d.username}</td>
                <td className="px-4 py-3 text-muted-foreground">{d.email ?? "—"}</td>
                <td className="px-4 py-3">
                  <Badge variant={d.role === "Admin" ? "default" : "secondary"}>{d.role}</Badge>
                </td>
                <td className="px-4 py-3">
                  <Badge variant={d.is_active ? "success" : "destructive"}>
                    {d.is_active ? "Active" : "Inactive"}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-muted-foreground text-xs">
                  {new Date(d.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3 text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => toggleActive(d)}
                  >
                    {d.is_active ? (
                      <><ShieldOff className="h-3.5 w-3.5" /> Deactivate</>
                    ) : (
                      <><ShieldCheck className="h-3.5 w-3.5" /> Reactivate</>
                    )}
                  </Button>
                </td>
              </tr>
            ))}
            {doctors.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No doctors found</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
