/**
 * Set-level evaluation panel:
 *   - Usability radio group
 *   - Low Quality checkbox (only active when IschemicAssessable)
 *   - Optional notes
 */
import { useLabelStore } from "@/store/labelStore";
import type { ImageSetUsability } from "@/lib/types";
import { USABILITY_LABELS } from "@/lib/types";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { WithTooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

const USABILITIES: ImageSetUsability[] = [
  "IschemicAssessable",
  "HemorrhagicPresent",
  "Anomaly",
  "Irrelevant",
];

const USABILITY_COLORS: Record<ImageSetUsability, string> = {
  IschemicAssessable:  "border-blue-500 bg-blue-500/10 text-blue-400",
  HemorrhagicPresent:  "border-red-500 bg-red-500/10 text-red-400",
  Anomaly:             "border-yellow-500 bg-yellow-500/10 text-yellow-400",
  Irrelevant:          "border-purple-500 bg-purple-500/10 text-purple-400",
};

const USABILITY_TOOLTIPS: Record<ImageSetUsability, string> = {
  IschemicAssessable:  "ASPECTS scoring applies — ischemic stroke OR healthy patient",
  HemorrhagicPresent:  "Hemorrhage detected — ASPECTS not applicable",
  Anomaly:             "Other abnormality present — ASPECTS not applicable (eg Brain tumors)",
  Irrelevant:          "Wrong scan (wrong body part, bone CT,...), wrong patient, or non-diagnostic",
};

export default function SetLevelEvaluation({ readOnly }: { readOnly?: boolean }) {
  const { usability, lowQuality, setNotes, setUsability, setLowQuality, setSetNotes } =
    useLabelStore();

  const lqInteractive = !readOnly && usability === "IschemicAssessable";

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label className="text-base uppercase tracking-wide text-muted-foreground">
          Usability
        </Label>
        <div className="grid grid-cols-2 gap-2">
          {USABILITIES.map((u) => (
            <WithTooltip
              key={u}
              type="medical"
              content={USABILITY_TOOLTIPS[u]}
              side="top"
            >
              <button
                type="button"
                onClick={readOnly ? undefined : () => setUsability(u)}
                tabIndex={readOnly ? -1 : undefined}
                className={cn(
                  "rounded-md border px-3 py-2 text-left text-base font-medium transition-all w-full",
                  usability === u
                    ? USABILITY_COLORS[u]
                    : cn("border-border text-muted-foreground", !readOnly && "hover:bg-muted"),
                  readOnly && "cursor-default"
                )}
              >
                {USABILITY_LABELS[u]}
              </button>
            </WithTooltip>
          ))}
        </div>
      </div>

      {/* Low Quality — tickbox, only active for IschemicAssessable */}
      <div className={cn(
        "flex items-center justify-between rounded-md border border-border px-3 py-2 transition-opacity",
        !lqInteractive && !readOnly && "opacity-40"
      )}>
        <Label
          className={cn(
            "text-lg select-none",
            lqInteractive ? "cursor-pointer" : "cursor-default"
          )}
          onClick={lqInteractive ? () => setLowQuality(!lowQuality) : undefined}
        >
          Low Quality
        </Label>
        <button
          type="button"
          role="checkbox"
          aria-checked={lowQuality}
          onClick={lqInteractive ? () => setLowQuality(!lowQuality) : undefined}
          tabIndex={lqInteractive ? 0 : -1}
          className={cn(
            "h-5 w-5 shrink-0 rounded border-2 flex items-center justify-center transition-colors",
            lowQuality && lqInteractive
              ? "border-primary bg-primary"
              : lowQuality && !lqInteractive
              ? "border-muted-foreground/50 bg-muted-foreground/30"
              : "border-muted-foreground/40 bg-transparent",
            lqInteractive && !lowQuality && "hover:border-primary",
            lqInteractive ? "cursor-pointer" : "cursor-default"
          )}
        >
          {lowQuality && (
            <Check className={cn("h-3 w-3", lqInteractive ? "text-primary-foreground" : "text-muted-foreground")} strokeWidth={3} />
          )}
        </button>
      </div>

      <div className="space-y-1.5">
        <Label className="text-base text-muted-foreground">Set-level notes (optional)</Label>
        <Textarea
          rows={2}
          placeholder="Any notes about this scan…"
          value={setNotes}
          onChange={readOnly ? undefined : (e) => setSetNotes(e.target.value)}
          readOnly={readOnly}
          className="text-base resize-none"
        />
      </div>
    </div>
  );
}
