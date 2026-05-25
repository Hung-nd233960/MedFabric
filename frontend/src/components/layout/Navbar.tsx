import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, Settings, LayoutDashboard, KeyRound, ChevronDown, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import ThemeToggle from "./ThemeToggle";
import { useAuthStore } from "@/store/authStore";
import { useNavGuardStore } from "@/store/navGuardStore";
import { authApi } from "@/lib/api";
import { toast } from "sonner";

export default function Navbar() {
  const { role, username, logout, setMustChangePassword } = useAuthStore();
  const { interceptor } = useNavGuardStore();
  const navigate = useNavigate();

  // Account dropdown
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Change password dialog
  const [pwOpen, setPwOpen] = useState(false);
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwSaving, setPwSaving] = useState(false);

  // Close dropdown on outside click
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const handleNav = (dest: string) => {
    setMenuOpen(false);
    if (interceptor) {
      interceptor(dest);
    } else {
      navigate(dest);
    }
  };

  const handleLogout = async () => {
    setMenuOpen(false);
    if (interceptor) {
      interceptor("__logout__");
      return;
    }
    try {
      await authApi.logout();
    } finally {
      logout();
      navigate("/login");
    }
  };

  const openChangePassword = () => {
    setMenuOpen(false);
    setCurrentPw("");
    setNewPw("");
    setConfirmPw("");
    setPwOpen(true);
  };

  const handleChangePassword = async () => {
    if (newPw.length < 8) {
      toast.error("New password must be at least 8 characters.");
      return;
    }
    if (newPw !== confirmPw) {
      toast.error("Passwords do not match.");
      return;
    }
    setPwSaving(true);
    try {
      await authApi.changePassword({ current_password: currentPw, new_password: newPw });
      setMustChangePassword(false);
      toast.success("Password changed successfully.");
      setPwOpen(false);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to change password.";
      toast.error(msg);
    } finally {
      setPwSaving(false);
    }
  };

  return (
    <>
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
        <div className="flex h-12 items-center gap-3 px-4">
          <button
            onClick={() => handleNav("/")}
            className="flex items-center gap-2 font-semibold text-sm hover:opacity-80 transition-opacity"
          >
            <span className="text-primary font-bold text-base">MedFabric</span>
            <span className="text-muted-foreground text-xs">3.0</span>
          </button>

          <Separator orientation="vertical" className="h-5" />

          <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => handleNav("/")}>
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </Button>

          {role === "Admin" && (
            <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => handleNav("/admin")}>
              <Settings className="h-4 w-4" />
              Admin
            </Button>
          )}

          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />

            {/* Account dropdown */}
            <div className="relative" ref={menuRef}>
              <Button
                variant="ghost"
                size="sm"
                className="gap-1.5"
                onClick={() => setMenuOpen((o) => !o)}
              >
                <User className="h-4 w-4" />
                <span className="max-w-[120px] truncate">{username ?? "Account"}</span>
                <ChevronDown className="h-3 w-3 opacity-60" />
              </Button>

              {menuOpen && (
                <div className="absolute right-0 top-full mt-1 w-48 rounded-md border border-border bg-background shadow-lg z-50 py-1">
                  <button
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                    onClick={openChangePassword}
                  >
                    <KeyRound className="h-4 w-4" />
                    Change Password
                  </button>
                  <div className="my-1 border-t border-border" />
                  <button
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-accent transition-colors"
                    onClick={handleLogout}
                  >
                    <LogOut className="h-4 w-4" />
                    Log Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Change Password dialog */}
      {pwOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-background border border-border rounded-lg p-6 w-full max-w-sm shadow-xl space-y-4">
            <h2 className="text-base font-semibold">Change Password</h2>
            <div className="space-y-3">
              <div className="space-y-1">
                <Label>Current Password</Label>
                <Input
                  type="password"
                  autoComplete="current-password"
                  value={currentPw}
                  onChange={(e) => setCurrentPw(e.target.value)}
                />
              </div>
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
                  onKeyDown={(e) => e.key === "Enter" && handleChangePassword()}
                />
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button className="flex-1" disabled={pwSaving} onClick={handleChangePassword}>
                {pwSaving ? "Saving…" : "Change Password"}
              </Button>
              <Button variant="outline" className="flex-1" onClick={() => setPwOpen(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
