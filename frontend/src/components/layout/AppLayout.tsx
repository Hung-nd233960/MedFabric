import { useState } from "react";
import { Outlet } from "react-router-dom";
import { toast } from "sonner";
import { ShieldAlert } from "lucide-react";
import Navbar from "./Navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/store/authStore";
import { authApi } from "@/lib/api";

export default function AppLayout() {
  const { mustChangePassword, setMustChangePassword } = useAuthStore();

  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSetPassword = async () => {
    if (newPw.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }
    if (newPw !== confirmPw) {
      toast.error("Passwords do not match.");
      return;
    }
    setSaving(true);
    try {
      await authApi.changePassword({ new_password: newPw });
      setMustChangePassword(false);
      toast.success("Password updated. Welcome!");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to set password.";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Forced password change — blocks the entire app */}
      {mustChangePassword && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-background border border-border rounded-lg p-8 w-full max-w-sm shadow-2xl space-y-5">
            <div className="flex flex-col items-center gap-2 text-center">
              <ShieldAlert className="h-8 w-8 text-yellow-500" />
              <h2 className="text-lg font-semibold">Password Change Required</h2>
              <p className="text-sm text-muted-foreground">
                An administrator has set a temporary password for your account. Please choose a new password to continue.
              </p>
            </div>
            <div className="space-y-3">
              <div className="space-y-1">
                <Label>New Password</Label>
                <Input
                  type="password"
                  autoComplete="new-password"
                  value={newPw}
                  onChange={(e) => setNewPw(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label>Confirm New Password</Label>
                <Input
                  type="password"
                  autoComplete="new-password"
                  value={confirmPw}
                  onChange={(e) => setConfirmPw(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSetPassword()}
                />
              </div>
            </div>
            <Button className="w-full" disabled={saving} onClick={handleSetPassword}>
              {saving ? "Saving…" : "Set New Password"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
