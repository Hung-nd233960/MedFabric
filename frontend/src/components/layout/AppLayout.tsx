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
import { useGlobalShortcuts } from "@/hooks/useGlobalShortcuts";
import { useHeartbeat } from "@/hooks/useHeartbeat";

export default function AppLayout() {
  useGlobalShortcuts();
  useHeartbeat();
  const { mustChangePassword, mustSetName, setMustChangePassword, setMustSetName } = useAuthStore();

  const [fullName, setFullName] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [saving, setSaving] = useState(false);

  const needsSetup = mustChangePassword || mustSetName;

  const handleSetup = async () => {
    if (mustSetName && fullName.trim().length < 2) {
      toast.error("Full name must be at least 2 characters.");
      return;
    }
    if (mustChangePassword) {
      if (newPw.length < 8) { toast.error("Password must be at least 8 characters."); return; }
      if (newPw !== confirmPw) { toast.error("Passwords do not match."); return; }
    }
    setSaving(true);
    try {
      await authApi.setupAccount({
        full_name: mustSetName ? fullName.trim() : undefined,
        new_password: mustChangePassword ? newPw : undefined,
      });
      if (mustSetName) setMustSetName(false);
      if (mustChangePassword) setMustChangePassword(false);
      toast.success("Account set up. Welcome!");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Setup failed.";
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

      {needsSetup && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-background border border-border rounded-lg p-8 w-full max-w-sm shadow-2xl space-y-5">
            <div className="flex flex-col items-center gap-2 text-center">
              <ShieldAlert className="h-8 w-8 text-yellow-500" />
              <h2 className="text-lg font-semibold">Complete Account Setup</h2>
              <p className="text-sm text-muted-foreground">
                Please complete your account setup before continuing.
              </p>
            </div>
            <div className="space-y-3">
              {mustSetName && (
                <div className="space-y-1">
                  <Label>Full Name</Label>
                  <Input
                    autoComplete="name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Your full name"
                  />
                </div>
              )}
              {mustChangePassword && (
                <>
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
                      onKeyDown={(e) => e.key === "Enter" && handleSetup()}
                    />
                  </div>
                </>
              )}
            </div>
            <Button className="w-full" disabled={saving} onClick={handleSetup}>
              {saving ? "Saving…" : "Complete Setup"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
