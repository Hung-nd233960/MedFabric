/**
 * Per-slice evaluation: region selector + zone score grid + slice notes + slice status.
 * Only rendered when ASPECTS scoring is enabled at set level.
 */
import type { RefObject } from "react";
import { useRef } from "react";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import type { Region } from "@/lib/types";
import { useLabelStore } from "@/store/labelStore";
import ZoneScoreGrid from "./ZoneScoreGrid";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { WithTooltip } from "@/components/ui/tooltip";
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

const REGION_TOOLTIPS: Record<Region, string> = {
  None:          "This slice is neither Basal Ganglia nor Corona Radiata",
  BasalGanglia:  "This region contains C, IC, L, I, M1, M2, M3",
  CoronaRadiata: "This region contains M4, M5, M6",
};

interface SliceEvaluationProps {
  imageUuid: string;
  readOnly?: boolean;
  zoneModeCell?: ZoneCell | null;
  zoneModeAnchor?: ZoneCell | null;
  onExitZoneMode?: () => void;
  sliceNotesRef?: RefObject<HTMLTextAreaElement>;
}

export default function SliceEvaluation({ imageUuid, readOnly, zoneModeCell, zoneModeAnchor, onExitZoneMode, sliceNotesRef }: SliceEvaluationProps) {
  const { slices, setRegion, setSliceNotes, isCurrentSliceValid } = useLabelStore();
  const internalNotesRef = useRef<HTMLTextAreaElement>(null);
  const notesRef = sliceNotesRef ?? internalNotesRef;
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
            <WithTooltip key={r} type="medical" content={REGION_TOOLTIPS[r]} side="top">
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
                {REGION_LABELS[r]}
              </button>
            </WithTooltip>
          ))}
        </div>
      </div>

      {region !== "None" && <ZoneScoreGrid imageUuid={imageUuid} readOnly={readOnly} zoneModeCell={zoneModeCell} zoneModeAnchor={zoneModeAnchor} onExitZoneMode={onExitZoneMode} />}

      <div className="space-y-1.5">
        <Label className="text-base text-muted-foreground">Slice notes (optional)</Label>
        <Textarea
          ref={notesRef}
          rows={2}
          placeholder="Notes for this slice…"
          value={slice?.notes ?? ""}
          onChange={readOnly ? undefined : (e) => setSliceNotes(imageUuid, e.target.value)}
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
