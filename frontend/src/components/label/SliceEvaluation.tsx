/**
 * Per-slice evaluation: region selector + zone score grid + slice notes + slice status.
 * Only rendered when ASPECTS scoring is enabled at set level.
 */
import React, { useRef, useState } from "react";
import { useAppearanceStore } from "@/store/appearanceStore";
import type { RefObject } from "react";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import type { Region } from "@/lib/types";
import { useLabelStore } from "@/store/labelStore";
import ZoneScoreGrid from "./ZoneScoreGrid";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { WithTooltip, TooltipKbd } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type ZoneCell = { row: number; col: "left" | "right" };

const REGIONS: Region[] = ["None", "BasalGanglia", "CoronaRadiata"];

const REGION_LABELS: Record<Region, string> = {
  None: "Skip (None)",
  BasalGanglia: "Basal Ganglia",
  CoronaRadiata: "Corona Radiata",
};

const REGION_COLORS: Record<Region, string> = {
  None: "border-muted-foreground/50 bg-muted/50 text-muted-foreground",
  BasalGanglia: "border-purple-500 bg-purple-500/10 text-purple-400",
  CoronaRadiata: "border-cyan-500 bg-cyan-500/10 text-cyan-400",
};

const REGION_KBD_COLORS: Record<Region, string> = {
  None:          "bg-background text-zinc-400 border-zinc-500/50",
  BasalGanglia:  "bg-background text-purple-400 border-purple-500/50",
  CoronaRadiata: "bg-background text-cyan-400 border-cyan-500/50",
};

const REGION_KEYS: Record<Region, string> = {
  None:          "Shift+N",
  BasalGanglia:  "Shift+B",
  CoronaRadiata: "Shift+C",
};

const REGION_TOOLTIPS: Record<Region, React.ReactNode> = {
  None:          <span className="flex items-center gap-2"><span>This slice is neither Basal Ganglia nor Corona Radiata</span><TooltipKbd>Shift+N</TooltipKbd></span>,
  BasalGanglia:  <span className="flex items-center gap-2"><span>This region contains C, IC, L, I, M1, M2, M3</span><TooltipKbd>Shift+B</TooltipKbd></span>,
  CoronaRadiata: <span className="flex items-center gap-2"><span>This region contains M4, M5, M6</span><TooltipKbd>Shift+C</TooltipKbd></span>,
};

const REGION_TOOLTIPS_PLAIN: Record<Region, React.ReactNode> = {
  None:          <span>This slice is neither Basal Ganglia nor Corona Radiata</span>,
  BasalGanglia:  <span>This region contains C, IC, L, I, M1, M2, M3</span>,
  CoronaRadiata: <span>This region contains M4, M5, M6</span>,
};

interface SliceEvaluationProps {
  imageUuid: string;
  readOnly?: boolean;
  zoneModeCell?: ZoneCell | null;
  zoneModeAnchor?: ZoneCell | null;
  zoneModeScope?: "cell" | "row" | "col" | "all";
  onExitZoneMode?: () => void;
  sliceNotesRef?: RefObject<HTMLTextAreaElement>;
}

export default function SliceEvaluation({ imageUuid, readOnly, zoneModeCell, zoneModeAnchor, zoneModeScope, onExitZoneMode, sliceNotesRef }: SliceEvaluationProps) {
  const { slices, setRegion, setSliceNotes, isCurrentSliceValid } = useLabelStore();
  const internalNotesRef = useRef<HTMLTextAreaElement>(null);
  const notesRef = sliceNotesRef ?? internalNotesRef;
  const [notesFocused, setNotesFocused] = useState(false);
  const { showKbdHints } = useAppearanceStore();
  const inZoneMode = zoneModeCell != null;
  const slice = slices[imageUuid];
  const region = slice?.region ?? "None";
  const sliceValid = isCurrentSliceValid();

  let statusIcon: React.ReactNode;
  let statusClass: string;
  let statusMsg: string;

  if (region === "None") {
    statusIcon = <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />;
    statusClass = "border-muted/40 bg-muted/20 text-muted-foreground";
    statusMsg = "This slice is None — will be skipped.";
  } else if (!sliceValid) {
    statusIcon = <XCircle className="h-4 w-4 mt-0.5 shrink-0" />;
    statusClass = "border-red-600/40 bg-red-600/10 text-red-400";
    statusMsg = "Fill all zones for this slice.";
  } else {
    statusIcon = <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />;
    statusClass = "border-green-600/40 bg-green-600/10 text-green-400";
    statusMsg = "This slice is valid.";
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label className="text-base uppercase tracking-wide text-muted-foreground">Region</Label>
        <div className="flex gap-2">
          {REGIONS.map((r) => (
            <WithTooltip key={r} type="medical" content={readOnly ? REGION_TOOLTIPS_PLAIN[r] : REGION_TOOLTIPS[r]} side="top" delayDuration={120}>
              <button
                type="button"
                onClick={readOnly ? undefined : () => setRegion(imageUuid, r)}
                tabIndex={readOnly ? -1 : undefined}
                className={cn(
                  "flex-1 rounded-md border px-2 py-1.5 text-base font-medium transition-all",
                  region === r
                    ? REGION_COLORS[r]
                    : cn("border-border text-muted-foreground", !readOnly && "hover:bg-muted"),
                  readOnly && "cursor-default"
                )}
              >
                <span className="flex flex-col items-center gap-0.5">
                  {REGION_LABELS[r]}
                  {!readOnly && showKbdHints && (
                    <kbd className={`font-mono border rounded px-1.5 py-0.5 text-xs leading-none ${REGION_KBD_COLORS[r]}`}>
                      {REGION_KEYS[r]}
                    </kbd>
                  )}
                </span>
              </button>
            </WithTooltip>
          ))}
        </div>
      </div>

      {region !== "None" && <ZoneScoreGrid imageUuid={imageUuid} readOnly={readOnly} zoneModeCell={zoneModeCell} zoneModeAnchor={zoneModeAnchor} zoneModeScope={zoneModeScope} onExitZoneMode={onExitZoneMode} />}

      <div className="space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <Label className="text-base text-muted-foreground">Slice notes (optional)</Label>
          {!readOnly && showKbdHints && (inZoneMode || region === "None") && (
            notesFocused
              ? <span className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
                  <kbd className="font-mono border border-primary/50 bg-background text-primary px-1.5 py-0.5 rounded text-xs leading-none">Esc</kbd>
                  <span>when done</span>
                </span>
              : <kbd className="font-mono border border-primary/50 bg-background text-primary px-1.5 py-0.5 rounded text-xs leading-none shrink-0">
                  {region === "None" ? "Shift+N" : "N"}
                </kbd>
          )}
        </div>
        <Textarea
          ref={notesRef}
          rows={2}
          placeholder="Notes for this slice…"
          value={slice?.notes ?? ""}
          onChange={readOnly ? undefined : (e) => setSliceNotes(imageUuid, e.target.value)}
          onFocus={() => setNotesFocused(true)}
          onBlur={() => setNotesFocused(false)}
          onKeyDown={readOnly ? undefined : (e) => {
            if (e.key === "Escape") e.currentTarget.blur();
          }}
          readOnly={readOnly}
          className="text-base resize-none"
        />
      </div>

      <div className={cn("rounded-md border px-3 py-2 text-base flex items-start gap-2", statusClass)}>
        {statusIcon}
        <span>{statusMsg}</span>
      </div>
    </div>
  );
}
