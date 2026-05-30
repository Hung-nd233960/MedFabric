import { useEffect, useRef, useState, type ReactNode } from "react";
import { Keyboard, ArrowLeft, FlaskConical, Stethoscope, ShieldCheck, User, ShieldAlert, RotateCcw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { WithTooltip } from "@/components/ui/tooltip";
import { useAppearanceStore, type TooltipMode, type NavMode, type UserPreferences } from "@/store/appearanceStore";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useAuthStore } from "@/store/authStore";
import { useUiStore } from "@/store/uiStore";
import { preferencesApi, authApi } from "@/lib/api";
import { cn } from "@/lib/utils";

// ── Section definitions ───────────────────────────────────────────────────

const SECTIONS = [
  { id: "appearance", label: "Appearance" },
  { id: "interface",  label: "Interface"  },
  { id: "keyboard",   label: "Keyboard"   },
  { id: "account",    label: "Account"    },
] as const;

type SectionId = typeof SECTIONS[number]["id"];

// ── Tooltip mode options ──────────────────────────────────────────────────

const TOOLTIP_OPTIONS: { value: TooltipMode; label: string; hint: string }[] = [
  { value: "all",        label: "All",       hint: "Show all tooltips — medical definitions and interface hints" },
  { value: "medical",    label: "Medical",   hint: "Show medical tooltips only — zone names and usability definitions" },
  { value: "functional", label: "Interface", hint: "Show interface tooltips only — button hints and feature explanations" },
  { value: "off",        label: "Off",       hint: "Hide all tooltips" },
];

// ── Sub-components ────────────────────────────────────────────────────────

function SectionHeading({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h2 id={id} className="text-base font-semibold text-foreground pt-10 pb-3 border-b border-border first:pt-0 scroll-mt-8">
      {children}
    </h2>
  );
}

function SettingRow({
  name,
  description,
  control,
  border = true,
}: {
  name: string;
  description?: string;
  control: ReactNode;
  border?: boolean;
}) {
  return (
    <div className={cn("flex items-center justify-between gap-10 py-4", border && "border-b border-border/60")}>
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{name}</p>
        {description && <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{description}</p>}
      </div>
      <div className="shrink-0">{control}</div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────

type MeData = {
  uuid: string;
  username: string;
  email: string | null;
  full_name: string | null;
  role: string;
  is_test: boolean;
  created_at: string | null;
};

export default function SettingsPage() {
  const {
    dark, tooltipMode, showKbdHints, dashboardHintOpen, navMode,
    setDark, setTooltipMode, setShowKbdHints, setDashboardHintOpen, setNavMode,
  } = useAppearanceStore();
  const { role, isTest } = useAuthStore();
  const openShortcuts = useUiStore((s) => s.openShortcuts);
  const navigate = useNavigate();

  const [me, setMe] = useState<MeData | null>(null);
  useEffect(() => {
    authApi.me().then((r) => setMe(r.data)).catch(() => {});
  }, []);

  const [confirmReset, setConfirmReset] = useState(false);

  const handleResetDefaults = () => {
    const defaults: UserPreferences = {
      dark: true,
      tooltip_mode: "all",
      show_kbd_hints: true,
      dashboard_hint_open: true,
      nav_mode: "arrow",
    };
    setDark(true);
    setTooltipMode("all");
    setShowKbdHints(true);
    setDashboardHintOpen(true);
    setNavMode("arrow");
    save(defaults);
    setConfirmReset(false);
  };

  const [activeSection, setActiveSection] = useState<SectionId>("appearance");
  const observerRef = useRef<IntersectionObserver | null>(null);

  // Track which section heading is in view
  useEffect(() => {
    observerRef.current?.disconnect();
    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActiveSection(entry.target.id as SectionId);
        }
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );
    observerRef.current = obs;
    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, []);

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const save = (patch: Partial<UserPreferences>) => {
    const prefs: UserPreferences = {
      dark,
      tooltip_mode: tooltipMode,
      show_kbd_hints: showKbdHints,
      dashboard_hint_open: dashboardHintOpen,
      nav_mode: navMode,
      ...patch,
    };
    preferencesApi.save(prefs).catch(() => {});
  };

  const NAV_OPTIONS: { value: NavMode; label: string; hint: string }[] = [
    { value: "arrow", label: "Arrow Keys", hint: "Use ← → ↑ ↓ for navigation" },
    { value: "vim",   label: "Vim (hjkl)",  hint: "Use h j k l for navigation. Enables navigation by hjkl keys. If you do not know what Vim is, disable is recommended." },
    { value: "both",  label: "Both",        hint: "Arrow keys and hjkl both work simultaneously" },
  ];

  return (
    <div className="flex overflow-hidden" style={{ height: "calc(100vh - 3.3rem)" }}>

      {/* ── Left sidebar (20%) ── */}
      <div className="w-[20%] shrink-0 flex flex-col border-r border-border/40 bg-muted/20">
        <div className="flex-1 overflow-y-auto px-6 pt-10 pb-6 space-y-0.5">
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground px-3 pb-3">Settings</p>
          {SECTIONS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => scrollTo(id)}
              className={cn(
                "w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors",
                activeSection === id
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="shrink-0 px-6 py-4 border-t border-border/40">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-full px-3 py-1.5 rounded-md hover:bg-muted/50"
          >
            <ArrowLeft className="h-4 w-4 shrink-0" />
            Return to Dashboard
          </button>
        </div>
      </div>

      {/* ── Main settings area (60%) ── */}
      <div className="w-[60%] overflow-y-auto px-12 pb-20">

        {/* Appearance */}
        <SectionHeading id="appearance">Appearance</SectionHeading>
        <SettingRow
          name="Dark Mode"
          description="Dark mode is always enabled — light mode is not supported."
          control={<Switch checked={true} disabled />}
        />

        {/* Interface */}
        <SectionHeading id="interface">Interface</SectionHeading>
        <SettingRow
          name="Tooltip Mode"
          description="Controls which tooltips are displayed when hovering over elements."
          control={
            <div className="flex rounded-lg border border-border p-0.5 gap-0.5">
              {TOOLTIP_OPTIONS.map(({ value, label, hint }) => (
                <WithTooltip key={value} type="meta" content={hint} side="top">
                  <button
                    type="button"
                    onClick={() => { setTooltipMode(value); save({ tooltip_mode: value }); }}
                    className={cn(
                      "px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap",
                      tooltipMode === value
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    )}
                  >
                    {label}
                  </button>
                </WithTooltip>
              ))}
            </div>
          }
        />
        <SettingRow
          name="Show Keyboard Hints"
          description="Show shortcut keys on buttons, tabs, zone grids, and other inline UI elements."
          control={
            <Switch
              checked={showKbdHints}
              onCheckedChange={(v) => { setShowKbdHints(v); save({ show_kbd_hints: v }); }}
            />
          }
        />
        <SettingRow
          name="Dashboard Shortcut Panel"
          description="Show the floating keyboard shortcuts reference panel on the Dashboard."
          control={
            <Switch
              checked={dashboardHintOpen}
              onCheckedChange={(v) => { setDashboardHintOpen(v); save({ dashboard_hint_open: v }); }}
            />
          }
          border={false}
        />

        {/* Keyboard */}
        <SectionHeading id="keyboard">Keyboard</SectionHeading>
        <SettingRow
          name="Navigation Keys"
          description="Enables navigation by hjkl keys. If you do not know what Vim is, Arrow Keys is recommended."
          control={
            <div className="flex rounded-lg border border-border p-0.5 gap-0.5">
              {NAV_OPTIONS.map(({ value, label, hint }) => (
                <WithTooltip key={value} type="meta" content={hint} side="top">
                  <button
                    type="button"
                    onClick={() => { setNavMode(value); save({ nav_mode: value }); }}
                    className={cn(
                      "px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap",
                      navMode === value
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    )}
                  >
                    {label}
                  </button>
                </WithTooltip>
              ))}
            </div>
          }
        />
        <SettingRow
          name="Keyboard Shortcuts"
          description="Browse all available keyboard shortcuts for the Dashboard and annotation interface."
          border={false}
          control={
            <Button
              variant="outline"
              className="gap-2"
              onClick={() => openShortcuts("general")}
            >
              <Keyboard className="h-4 w-4" />
              Open
              <kbd className="ml-1 text-xs font-mono border border-foreground/30 bg-foreground/10 text-foreground px-1.5 py-0.5 rounded">?</kbd>
            </Button>
          }
        />

        {/* Account */}
        <SectionHeading id="account">Account</SectionHeading>

        {/* Role + test badges */}
        <div className="flex items-center gap-2 py-3 border-b border-border/60">
          {isTest ? (
            <WithTooltip type="meta" content="Test/admin account — activity may not count toward production statistics" side="top">
              <span className="flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium border-purple-500/40 bg-purple-500/10 text-purple-400">
                <FlaskConical className="h-3 w-3" /> Testing Account
              </span>
            </WithTooltip>
          ) : (
            <WithTooltip type="meta" content="Annotation account — your submissions count toward production statistics" side="top">
              <span className="flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium border-teal-500/40 bg-teal-500/10 text-teal-400">
                <Stethoscope className="h-3 w-3" /> Official Account
              </span>
            </WithTooltip>
          )}
          {role === "Admin" ? (
            <span className="flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium border-orange-500/40 bg-orange-500/10 text-orange-400">
              <ShieldAlert className="h-3 w-3" /> Admin
            </span>
          ) : (
            <span className="flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium border-blue-500/40 bg-blue-500/10 text-blue-400">
              <User className="h-3 w-3" /> Doctor
            </span>
          )}
        </div>

        <SettingRow
          name="Username"
          control={<span className="text-sm text-muted-foreground font-mono">{me?.username ?? "—"}</span>}
        />
        <SettingRow
          name="Display Name"
          control={<span className="text-sm text-muted-foreground">{me?.full_name ?? "—"}</span>}
        />
        <SettingRow
          name="Email"
          control={<span className="text-sm text-muted-foreground">{me?.email ?? "—"}</span>}
        />
        <SettingRow
          name="Member Since"
          control={
            <span className="text-sm text-muted-foreground">
              {me?.created_at
                ? new Date(me.created_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric", timeZone: "Asia/Bangkok" })
                : "—"}
            </span>
          }
        />
        <SettingRow
          name="Password"
          description="Change your account password."
          control={
            <Button
              variant="outline"
              className="gap-2"
              onClick={() => navigate("/change-password")}
            >
              <ShieldCheck className="h-4 w-4" />
              Change Password
            </Button>
          }
        />
        <SettingRow
          name="Reset Settings"
          description="Restore all appearance and interface settings to their defaults."
          border={false}
          control={
            <Button
              variant="outline"
              className="gap-2 text-destructive hover:text-destructive hover:border-destructive/60"
              onClick={() => setConfirmReset(true)}
            >
              <RotateCcw className="h-4 w-4" />
              Reset to Defaults
            </Button>
          }
        />

      </div>

      {confirmReset && (
        <ConfirmDialog
          title="Reset all settings?"
          body="This will restore Dark Mode, Tooltip Mode, Keyboard Hints, Dashboard Panel, and Navigation Keys to their default values."
          layout="horizontal"
          defaultFocusIndex={1}
          buttons={[
            {
              label: "Yes, Reset",
              onClick: handleResetDefaults,
              className: "bg-destructive hover:bg-destructive/90 text-destructive-foreground",
            },
            {
              label: "Cancel",
              onClick: () => setConfirmReset(false),
              className: "bg-transparent hover:bg-muted text-muted-foreground",
            },
          ]}
        />
      )}

      {/* ── Right margin (20%) ── */}
      <div className="w-[20%] shrink-0" />
    </div>
  );
}
