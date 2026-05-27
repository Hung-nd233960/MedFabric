import { useEffect, useState } from "react";
import { toast } from "sonner";
import { UserPlus, ShieldOff, ShieldCheck, KeyRound, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
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
  const [form, setForm] = useState({ username: "", full_name: "", password: "", email: "", role: "Doctor", is_test: false });
  const [saving, setSaving] = useState(false);
  const [resetTarget, setResetTarget] = useState<Doctor | null>(null);
  const [resetPw, setResetPw] = useState("");
  const [resetSaving, setResetSaving] = useState(false);

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

  const toggleTest = async (doctor: Doctor) => {
    try {
      await adminApi.updateDoctor(doctor.uuid, { is_test: !doctor.is_test });
      toast.success(`'${doctor.username}' marked as ${!doctor.is_test ? "testing" : "real"} account`);
      load();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to update account";
      toast.error(msg);
    }
  };

  const resetPassword = async () => {
    if (!resetTarget) return;
    if (resetPw.length < 8) { toast.error("Password must be at least 8 characters."); return; }
    setResetSaving(true);
    try {
      await adminApi.updateDoctor(resetTarget.uuid, { password: resetPw });
      toast.success(`Password reset for '${resetTarget.username}'. They will be prompted to change it on next login.`);
      setResetTarget(null);
      setResetPw("");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to reset password";
      toast.error(msg);
    } finally {
      setResetSaving(false);
    }
  };

  const createDoctor = async () => {
    if (!form.username || !form.password) { toast.error("Username and password required"); return; }
    setSaving(true);
    try {
      await adminApi.createDoctor({ ...form, email: form.email || undefined, full_name: form.full_name || undefined });
      toast.success(`Doctor '${form.username}' created`);
      setOpen(false);
      setForm({ username: "", full_name: "", password: "", email: "", role: "Doctor", is_test: false });
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
          <div className="flex items-center gap-2">
            <Switch
              id="show-inactive"
              checked={showInactive}
              onCheckedChange={setShowInactive}
            />
            <Label htmlFor="show-inactive" className="text-sm text-muted-foreground cursor-pointer">
              Show inactive
            </Label>
          </div>
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
                {(["username", "full_name", "password", "email"] as const).map((f) => (
                  <div key={f} className="space-y-1">
                    <Label className="capitalize">{f}</Label>
                    <Input
                      type={f === "password" ? "password" : "text"}
                      placeholder={f === "full_name" ? "Leave blank to prompt on first login" : undefined}
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
                <div className="flex items-center gap-2">
                  <Switch
                    id="is-test"
                    checked={form.role === "Admin" ? true : form.is_test}
                    disabled={form.role === "Admin"}
                    onCheckedChange={(checked) => setForm((p) => ({ ...p, is_test: checked }))}
                  />
                  <Label htmlFor="is-test" className={`cursor-pointer select-none ${form.role === "Admin" ? "text-muted-foreground" : ""}`}>
                    Testing account{" "}
                    <span className="text-muted-foreground text-xs">(annotations excluded from global progress)</span>
                  </Label>
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
              <th className="text-left px-4 py-3 font-medium">Full Name</th>
              <th className="text-left px-4 py-3 font-medium">Email</th>
              <th className="text-left px-4 py-3 font-medium">Role</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
              <th className="text-left px-4 py-3 font-medium">Source</th>
              <th className="text-left px-4 py-3 font-medium">Created</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {doctors.map((d) => (
              <tr key={d.uuid} className="hover:bg-muted/30">
                <td className="px-4 py-3 font-medium">{d.username}</td>
                <td className="px-4 py-3 text-muted-foreground">{d.full_name ?? <span className="italic text-yellow-600 text-xs">Not set</span>}</td>
                <td className="px-4 py-3 text-muted-foreground">{d.email ?? "—"}</td>
                <td className="px-4 py-3">
                  <Badge variant={d.role === "Admin" ? "default" : "secondary"}>{d.role}</Badge>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <Badge variant={d.is_active ? "success" : "destructive"}>
                      {d.is_active ? "Active" : "Inactive"}
                    </Badge>
                    {d.is_test && (
                      <Badge variant="outline" className="text-purple-500 border-purple-500/50">
                        <FlaskConical className="h-3 w-3 mr-1" />Testing
                      </Badge>
                    )}
                    {d.must_change_password && (
                      <Badge variant="outline" className="text-yellow-600 border-yellow-500">
                        Reset Pending
                      </Badge>
                    )}
                    {d.must_set_name && (
                      <Badge variant="outline" className="text-orange-600 border-orange-500">
                        Name Pending
                      </Badge>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Badge
                    variant="outline"
                    className={d.registration_source === "self_registered"
                      ? "text-blue-600 border-blue-500"
                      : "text-muted-foreground"}
                  >
                    {d.registration_source === "self_registered" ? "Self-registered" : "Admin"}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-muted-foreground text-xs">
                  {new Date(d.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="gap-1.5"
                      onClick={() => { setResetTarget(d); setResetPw(""); }}
                    >
                      <KeyRound className="h-3.5 w-3.5" /> Reset Password
                    </Button>
                    {d.role === "Admin" ? (
                      <Button variant="ghost" size="sm" className="gap-1.5 opacity-40 cursor-not-allowed" disabled title="Admin accounts are permanently test accounts">
                        <FlaskConical className="h-3.5 w-3.5" /> Always Test
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="gap-1.5"
                        onClick={() => toggleTest(d)}
                        title={d.is_test ? "Remove test flag (blocked if account has submissions)" : "Mark as testing account"}
                      >
                        <FlaskConical className="h-3.5 w-3.5" />
                        {d.is_test ? "Unmark Test" : "Mark as Test"}
                      </Button>
                    )}
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
                  </div>
                </td>
              </tr>
            ))}
            {doctors.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">No doctors found</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {/* Reset Password modal */}
      {resetTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-background border border-border rounded-lg p-6 w-full max-w-sm shadow-xl space-y-4">
            <h2 className="text-base font-semibold">Reset Password</h2>
            <p className="text-sm text-muted-foreground">
              Set a temporary password for <span className="font-medium text-foreground">{resetTarget.username}</span>.
              They will be required to change it on next login.
            </p>
            <div className="space-y-1">
              <Label>New Temporary Password</Label>
              <Input
                type="password"
                value={resetPw}
                onChange={(e) => setResetPw(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && resetPassword()}
              />
            </div>
            <div className="flex gap-2">
              <Button className="flex-1" disabled={resetSaving} onClick={resetPassword}>
                {resetSaving ? "Resetting…" : "Reset Password"}
              </Button>
              <Button variant="outline" className="flex-1" onClick={() => setResetTarget(null)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
