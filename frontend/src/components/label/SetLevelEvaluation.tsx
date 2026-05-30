/**
 * Set-level evaluation panel:
 *   - Usability radio group
 *   - Low Quality checkbox (only active when IschemicAssessable)
 *   - Optional notes
 */
import { useEffect, useRef, useState } from "react";
import { useAppearanceStore } from "@/store/appearanceStore";
import type { RefObject, ReactNode } from "react";
import { useLabelStore } from "@/store/labelStore";
import type { ImageSetUsability } from "@/lib/types";
import { USABILITY_LABELS } from "@/lib/types";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { WithTooltip, TooltipKbd } from "@/components/ui/tooltip";
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

const USABILITY_KBD_COLORS: Record<ImageSetUsability, string> = {
  IschemicAssessable: "bg-background text-blue-400 border-blue-500/50",
  HemorrhagicPresent: "bg-background text-red-400 border-red-500/50",
  Anomaly:            "bg-background text-yellow-400 border-yellow-500/50",
  Irrelevant:         "bg-background text-purple-400 border-purple-500/50",
};

const USABILITY_KEYS: Record<ImageSetUsability, string> = {
  IschemicAssessable: "Shift+1",
  HemorrhagicPresent: "Shift+2",
  Anomaly:            "Shift+3",
  Irrelevant:         "Shift+4",
};

const USABILITY_TOOLTIPS: Record<ImageSetUsability, ReactNode> = {
  IschemicAssessable:  <span className="flex items-center gap-2"><span>ASPECTS scoring applies — ischemic stroke or healthy patient</span><TooltipKbd>Shift+1</TooltipKbd></span>,
  HemorrhagicPresent:  <span className="flex items-center gap-2"><span>Hemorrhage detected — ASPECTS not applicable</span><TooltipKbd>Shift+2</TooltipKbd></span>,
  Anomaly:             <span className="flex items-center gap-2"><span>Other abnormality present — ASPECTS not applicable (eg. brain tumors). Describe in notes.</span><TooltipKbd>Shift+3</TooltipKbd></span>,
  Irrelevant:          <span className="flex items-center gap-2"><span>Wrong scan, wrong patient, or non-diagnostic. Include reason in notes.</span><TooltipKbd>Shift+4</TooltipKbd></span>,
};

export default function SetLevelEvaluation({
  readOnly,
  notesRef: externalNotesRef,
  zoneMode,
}: {
  readOnly?: boolean;
  notesRef?: RefObject<HTMLTextAreaElement>;
  zoneMode?: boolean;
}) {
  const { usability, lowQuality, setNotes, setUsability, setLowQuality, setSetNotes } =
    useLabelStore((s) => ({
      usability: s.usability,
      lowQuality: s.lowQuality,
      setNotes: s.setNotes,
      setUsability: s.setUsability,
      setLowQuality: s.setLowQuality,
      setSetNotes: s.setSetNotes,
    }));

  const internalNotesRef = useRef<HTMLTextAreaElement>(null);
  const notesTextareaRef = externalNotesRef ?? internalNotesRef;
  const lqInteractive = !readOnly && usability === "IschemicAssessable";
  const [notesFocused, setNotesFocused] = useState(false);
  const { showKbdHints } = useAppearanceStore();

  // Auto-focus notes textarea when Anomaly/Irrelevant is selected (notes are required)
  useEffect(() => {
    if (!readOnly && (usability === "Anomaly" || usability === "Irrelevant")) {
      notesTextareaRef.current?.focus();
    }
  }, [usability, readOnly]);

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <Label className="text-base uppercase tracking-wide text-muted-foreground">Usability</Label>
          {!readOnly && (
            zoneMode
              ? <span className="text-xs text-muted-foreground shrink-0">Disable Zone Mode to change usability</span>
              : showKbdHints
              ? <span className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                  <kbd className="font-mono border border-primary/50 bg-background text-primary px-1.5 py-0.5 rounded text-xs leading-none">Shift+0</kbd>
                  <span>to unselect</span>
                </span>
              : null
          )}
        </div>
        <div className="grid grid-cols-2 gap-2">
          {USABILITIES.map((u) => (
            <WithTooltip
              key={u}
              type="medical"
              content={USABILITY_TOOLTIPS[u]}
              side="top"
              delayDuration={120}
            >
              <button
                type="button"
                onClick={readOnly ? undefined : () => setUsability(usability === u ? null : u)}
                tabIndex={readOnly ? -1 : undefined}
                className={cn(
                  "rounded-md border px-3 py-2 text-left text-base font-medium transition-all w-full",
                  usability === u
                    ? USABILITY_COLORS[u]
                    : cn("border-border text-muted-foreground", !readOnly && "hover:bg-muted"),
                  readOnly && "cursor-default"
                )}
              >
                <span className="flex items-center justify-between gap-2">
                  {USABILITY_LABELS[u]}
                  {!readOnly && !zoneMode && showKbdHints && (
                    <kbd className={`font-mono border px-1.5 py-0.5 rounded text-xs leading-none shrink-0 ${USABILITY_KBD_COLORS[u]}`}>
                      {USABILITY_KEYS[u]}
                    </kbd>
                  )}
                </span>
              </button>
            </WithTooltip>
          ))}
        </div>
      </div>

      {/* Low Quality — tickbox, only active for IschemicAssessable */}
      <WithTooltip
        type="medical"
        content={<span className="flex items-center gap-2"><span>Poor image quality — artifacts or technical issues reducing diagnostic confidence</span><TooltipKbd>Shift+Q</TooltipKbd></span>}
        side="top"
      >
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
          <div className="flex items-center gap-2">
            {!readOnly && !zoneMode && showKbdHints && (
              <kbd className="font-mono border border-orange-500/50 bg-background text-orange-400 px-1.5 py-0.5 rounded text-xs leading-none shrink-0">Shift+Q</kbd>
            )}
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
        </div>
      </WithTooltip>

      {(() => {
        const notesRequired = !readOnly && (usability === "Anomaly" || usability === "Irrelevant");
        const notesEmpty = !setNotes?.trim();
        return (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <Label className={cn("text-base", notesRequired ? "text-foreground font-medium" : "text-muted-foreground")}>
                Set-level notes{notesRequired ? <span className="text-destructive ml-1">*</span> : " (optional)"}
              </Label>
              {!readOnly && showKbdHints && (
                zoneMode
                  ? <span className="text-xs text-muted-foreground shrink-0">N goes to slice notes here</span>
                  : notesFocused
                  ? <span className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                      <kbd className="font-mono border border-primary/50 bg-background text-primary px-1.5 py-0.5 rounded text-xs leading-none">Esc</kbd>
                      <span>when done</span>
                    </span>
                  : <kbd className="font-mono border border-primary/50 bg-background text-primary px-1.5 py-0.5 rounded text-xs leading-none shrink-0">N</kbd>
              )}
            </div>
            <Textarea
              ref={notesTextareaRef}
              rows={2}
              placeholder={notesRequired ? `Describe the ${usability === "Anomaly" ? "anomaly" : "reason this scan is irrelevant"}…` : "Any notes about this scan…"}
              value={setNotes}
              onChange={readOnly ? undefined : (e) => setSetNotes(e.target.value)}
              onFocus={() => setNotesFocused(true)}
              onBlur={() => setNotesFocused(false)}
              onKeyDown={readOnly ? undefined : (e) => {
                if (e.key === "Escape") e.currentTarget.blur();
              }}
              readOnly={readOnly}
              className={cn("text-base resize-none", notesRequired && notesEmpty && "border-destructive focus-visible:ring-destructive")}
            />
          </div>
        );
      })()}
    </div>
  );
}
