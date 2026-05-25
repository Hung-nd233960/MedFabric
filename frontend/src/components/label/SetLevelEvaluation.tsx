/**
 * Set-level evaluation panel:
 *   - Usability radio group
 *   - Low Quality checkbox
 *   - Optional notes
 */
import { useLabelStore } from "@/store/labelStore";
import type { ImageSetUsability } from "@/lib/types";
import { USABILITY_LABELS } from "@/lib/types";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const USABILITIES: ImageSetUsability[] = [
  "IschemicAssessable",
  "HemorrhagicPresent",
  "Anomaly",
  "Irrelevant",
];

const USABILITY_COLORS: Record<ImageSetUsability, string> = {
  IschemicAssessable:
    "border-blue-500 bg-blue-500/10 text-blue-400",
  HemorrhagicPresent:
    "border-red-500 bg-red-500/10 text-red-400",
  Anomaly:
    "border-yellow-500 bg-yellow-500/10 text-yellow-400",
  Irrelevant:
    "border-muted-foreground/50 bg-muted/50 text-muted-foreground",
};

export default function SetLevelEvaluation() {
  const { usability, lowQuality, setNotes, setUsability, setLowQuality, setSetNotes } =
    useLabelStore();

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label className="text-xs uppercase tracking-wide text-muted-foreground">
          Usability
        </Label>
        <div className="grid grid-cols-2 gap-2">
          {USABILITIES.map((u) => (
            <button
              key={u}
              type="button"
              onClick={() => setUsability(u)}
              className={cn(
                "rounded-md border px-3 py-2 text-left text-xs font-medium transition-all",
                usability === u
                  ? USABILITY_COLORS[u]
                  : "border-border text-muted-foreground hover:bg-muted"
              )}
            >
              {USABILITY_LABELS[u]}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between rounded-md border border-border px-3 py-2">
        <Label htmlFor="low-quality" className="cursor-pointer text-sm">
          Low Quality
        </Label>
        <Switch
          id="low-quality"
          checked={lowQuality}
          onCheckedChange={setLowQuality}
        />
      </div>

      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">Set-level notes (optional)</Label>
        <Textarea
          rows={2}
          placeholder="Any notes about this scan…"
          value={setNotes}
          onChange={(e) => setSetNotes(e.target.value)}
          className="text-sm resize-none"
        />
      </div>
    </div>
  );
}
