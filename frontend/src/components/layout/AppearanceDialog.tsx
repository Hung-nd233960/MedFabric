import { Moon, Sun, Keyboard } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { WithTooltip } from "@/components/ui/tooltip";
import { useAppearanceStore, type TooltipMode } from "@/store/appearanceStore";
import { useUiStore } from "@/store/uiStore";
import { cn } from "@/lib/utils";

const TOOLTIP_OPTIONS: { value: TooltipMode; label: string; hint: string }[] = [
  {
    value: "all",
    label: "All",
    hint: "Show all tooltips — medical definitions and interface hints",
  },
  {
    value: "medical",
    label: "Medical",
    hint: "Show medical tooltips only — zone abbreviations and usability definitions",
  },
  {
    value: "functional",
    label: "Interface",
    hint: "Show interface tooltips only — button hints and feature explanations",
  },
  {
    value: "off",
    label: "Off",
    hint: "Hide all tooltips",
  },
];

export default function AppearanceDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const { dark, tooltipMode, setDark, setTooltipMode } = useAppearanceStore();
  const openShortcuts = useUiStore((s) => s.openShortcuts);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Appearance Settings</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {/* Appearance group */}
          <div className="space-y-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Appearance
            </p>
            <div className="flex items-center justify-between">
              <Label htmlFor="dark-mode" className="flex items-center gap-2 cursor-pointer">
                {dark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                Dark Mode
              </Label>
              <Switch
                id="dark-mode"
                checked={dark}
                onCheckedChange={setDark}
              />
            </div>
          </div>

          <Separator />

          {/* Interface group */}
          <div className="space-y-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Interface
            </p>
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Tooltips</Label>
              <div className="flex rounded-lg border border-border p-0.5 gap-0.5">
                {TOOLTIP_OPTIONS.map(({ value, label, hint }) => (
                  <WithTooltip key={value} type="meta" content={hint} side="top">
                    <button
                      type="button"
                      onClick={() => setTooltipMode(value)}
                      className={cn(
                        "flex-1 px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors",
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
            </div>
          </div>

          <Separator />

          {/* Shortcuts group */}
          <div className="space-y-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Shortcuts
            </p>
            <Button
              variant="outline"
              className="w-full gap-2 justify-start"
              onClick={() => { openShortcuts("general"); onOpenChange(false); }}
            >
              <Keyboard className="h-4 w-4" />
              Keyboard Shortcuts
              <kbd className="ml-auto text-xs font-mono border border-border bg-muted px-1.5 py-0.5 rounded">?</kbd>
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
