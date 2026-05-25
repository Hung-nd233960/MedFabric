/**
 * Validation status box shown in the right panel.
 * Three states:
 *   - Orange warning: slice not classified (region = None)
 *   - Green: slice is valid
 *   - Red: slice classified but zones incomplete
 */
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { useLabelStore } from "@/store/labelStore";
import { cn } from "@/lib/utils";

export default function ValidationStatus() {
  const {
    currentSlice,
    isCurrentSliceValid,
    isSetSubmittable,
    validationMessage,
    aspectsEnabled,
  } = useLabelStore();

  const slice = currentSlice();
  const sliceValid = isCurrentSliceValid();
  const setReady = isSetSubmittable();
  const aspects = aspectsEnabled();

  if (!aspects) {
    return (
      <div
        className={cn(
          "rounded-md border px-3 py-2 text-sm flex items-start gap-2",
          setReady
            ? "border-green-600/40 bg-green-600/10 text-green-400"
            : "border-muted/40 bg-muted/20 text-muted-foreground"
        )}
      >
        {setReady ? (
          <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
        ) : (
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
        )}
        <span>{validationMessage()}</span>
      </div>
    );
  }

  // Determine current slice state for the indicator
  let sliceIcon = <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />;
  let sliceClass = "border-yellow-600/40 bg-yellow-600/10 text-yellow-400";
  let sliceMsg = "This slice is unclassified (None) — will be skipped.";

  if (slice.region !== "None") {
    if (sliceValid) {
      sliceIcon = <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />;
      sliceClass = "border-green-600/40 bg-green-600/10 text-green-400";
      sliceMsg = "This slice is valid.";
    } else {
      sliceIcon = <XCircle className="h-4 w-4 mt-0.5 shrink-0" />;
      sliceClass = "border-red-600/40 bg-red-600/10 text-red-400";
      sliceMsg = "Fill all zone scores for this slice.";
    }
  }

  return (
    <div className="space-y-2">
      <div className={cn("rounded-md border px-3 py-2 text-xs flex items-start gap-2", sliceClass)}>
        {sliceIcon}
        <span>{sliceMsg}</span>
      </div>
      <div
        className={cn(
          "rounded-md border px-3 py-2 text-xs flex items-start gap-2",
          setReady
            ? "border-green-600/40 bg-green-600/10 text-green-400"
            : "border-muted/40 bg-muted/20 text-muted-foreground"
        )}
      >
        {setReady ? (
          <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
        ) : (
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
        )}
        <span>{validationMessage()}</span>
      </div>
    </div>
  );
}
