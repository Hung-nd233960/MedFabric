import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { LogOut, Settings, LayoutDashboard, KeyRound, ChevronDown, User, BookOpen, PenLine, FlaskConical, ScanEye, Palette, Info, Stethoscope } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import AppearanceDialog from "./AppearanceDialog";
import AboutDialog from "./AboutDialog";
import { useAuthStore } from "@/store/authStore";
import { useNavGuardStore } from "@/store/navGuardStore";
import { useLabelStore } from "@/store/labelStore";
import { WithTooltip } from "@/components/ui/tooltip";
import { authApi } from "@/lib/api";

export default function Navbar() {
  const { role, username, logout, isTest } = useAuthStore();
  const { interceptor } = useNavGuardStore();
  const { mode, autoSaveStatus } = useLabelStore();
  const navigate = useNavigate();
  const location = useLocation();

  const isLabeling = location.pathname.startsWith("/label");

  const [menuOpen, setMenuOpen] = useState(false);
  const [appearanceOpen, setAppearanceOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

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

  return (
    <>
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur" style={{ zoom: 1.1 }}>
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
            {isLabeling && mode === "annotate" && autoSaveStatus !== "idle" && (
              <span className={`flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                autoSaveStatus === "saved"
                  ? "border-green-500/40 bg-green-500/10 text-green-400"
                  : "border-yellow-500/40 bg-yellow-500/10 text-yellow-400"
              }`}>
                {autoSaveStatus === "pending" && "● Unsaved"}
                {autoSaveStatus === "saving"  && "● Saving…"}
                {autoSaveStatus === "saved"   && "✓ Saved as Draft"}
              </span>
            )}
            {isLabeling && (
              <WithTooltip
                content={
                  mode === "read"
                    ? "Read-only — reviewing submitted or saved annotations, no changes can be made"
                    : mode === "preview"
                    ? "Preview mode — browsing images without creating an annotation session"
                    : "Active annotation session — your scores are being recorded"
                }
                side="bottom"
              >
                <span className={`flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                  mode === "read"    ? "border-blue-500/40 bg-blue-500/10 text-blue-400"
                  : mode === "preview" ? "border-orange-500/40 bg-orange-500/10 text-orange-400"
                  : "border-green-500/40 bg-green-500/10 text-green-400"
                }`}>
                  {mode === "read"    ? <><BookOpen className="h-3 w-3" /> Reader Mode</>
                  : mode === "preview" ? <><ScanEye className="h-3 w-3" /> Preview Mode</>
                  : <><PenLine className="h-3 w-3" /> Annotate Mode</>}
                </span>
              </WithTooltip>
            )}
            {isTest ? (
              <WithTooltip
                content="Test/admin account — activity may not count toward production statistics"
                side="bottom"
              >
                <span className="flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium border-purple-500/40 bg-purple-500/10 text-purple-400">
                  <FlaskConical className="h-3 w-3" /> Testing Account
                </span>
              </WithTooltip>
            ) : role === "Doctor" && (
              <WithTooltip
                content="Annotation account — your submissions count toward production statistics"
                side="bottom"
              >
                <span className="flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium border-teal-500/40 bg-teal-500/10 text-teal-400">
                  <Stethoscope className="h-3 w-3" /> Annotation Account
                </span>
              </WithTooltip>
            )}

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
                <div className="absolute right-0 top-full mt-1 w-52 rounded-md border border-border bg-background shadow-lg z-50 py-1">
                  {!isLabeling && (
                    <button
                      className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                      onClick={() => handleNav("/change-password")}
                    >
                      <KeyRound className="h-4 w-4" />
                      Change Password
                    </button>
                  )}
                  <button
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                    onClick={() => { setMenuOpen(false); setAppearanceOpen(true); }}
                  >
                    <Palette className="h-4 w-4" />
                    Appearance Settings
                  </button>
                  <button
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                    onClick={() => { setMenuOpen(false); setAboutOpen(true); }}
                  >
                    <Info className="h-4 w-4" />
                    About
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

      <AppearanceDialog open={appearanceOpen} onOpenChange={setAppearanceOpen} />
      <AboutDialog open={aboutOpen} onOpenChange={setAboutOpen} />
    </>
  );
}
