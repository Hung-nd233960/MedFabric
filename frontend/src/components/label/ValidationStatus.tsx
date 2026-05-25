/**
 * Set-level validation box shown above the submit button.
 *
 * When ASPECTS is enabled, warnings follow a strict A > B > C > D hierarchy —
 * only the highest-priority unresolved issue is shown.
 *
 *   A (red)    — missing required slice types (BasalGanglia / CoronaRadiata)
 *   B (red)    — annotated slices with incomplete zone scores
 *   C (yellow) — annotated slice indices are not consecutive
 *   D (green)  — image set is valid for submission
 */
import type { ReactNode } from "react";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { useLabelStore } from "@/store/labelStore";
import type { Region, SliceEvalState } from "@/lib/types";
import { BASAL_ZONES, CORONA_ZONES } from "@/lib/types";

function relevantKeys(region: Region): string[] {
  if (region === "None") return [];
  const zones = region === "BasalGanglia" ? BASAL_ZONES : CORONA_ZONES;
  return zones.flatMap((z) => [`${z}_left_score`, `${z}_right_score`]);
}

function sliceFullyScored(slice: SliceEvalState): boolean {
  if (slice.region === "None") return true;
  return relevantKeys(slice.region).every((k) => slice.scores[k] !== null);
}

function consecutive(sorted: number[]): boolean {
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] !== sorted[i - 1] + 1) return false;
  }
  return true;
}

function RedBox({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-red-600/40 bg-red-600/10 text-red-400 px-3 py-2 text-base flex items-start gap-2">
      <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

function YellowBox({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-yellow-600/40 bg-yellow-600/10 text-yellow-400 px-3 py-2 text-base flex items-start gap-2">
      <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

function GreenBox({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-green-600/40 bg-green-600/10 text-green-400 px-3 py-2 text-base flex items-start gap-2">
      <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

function MutedBox({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-md border border-muted/40 bg-muted/20 text-muted-foreground px-3 py-2 text-base flex items-start gap-2">
      <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

export default function ValidationStatus() {
  const { images, slices, aspectsEnabled, isSetSubmittable } = useLabelStore();

  const aspects = aspectsEnabled();
  const setReady = isSetSubmittable();

  // ── ASPECTS disabled path ────────────────────────────────────────────────
  if (!aspects) {
    if (setReady) return <GreenBox>Ready to submit.</GreenBox>;
    return <MutedBox>Select a usability classification first.</MutedBox>;
  }

  // ── Class A: missing required slice types ────────────────────────────────
  const hasBasal = images.some((img) => slices[img.uuid]?.region === "BasalGanglia");
  const hasCorona = images.some((img) => slices[img.uuid]?.region === "CoronaRadiata");

  if (!hasBasal || !hasCorona) {
    const missing: string[] = [];
    if (!hasBasal) missing.push("BasalGanglia");
    if (!hasCorona) missing.push("CoronaRadiata");
    return <RedBox>Need at least one {missing.join(" and ")} slice.</RedBox>;
  }

  // ── Class B: annotated slices with incomplete zone scores ────────────────
  const incomplete = images
    .map((img, i) => ({ i, slice: slices[img.uuid] }))
    .filter(({ slice }) => slice && slice.region !== "None" && !sliceFullyScored(slice))
    .map(({ i }) => i + 1); // 1-indexed image numbers

  if (incomplete.length > 0) {
    return <RedBox>Missing annotation in image {incomplete.join(", ")}.</RedBox>;
  }

  // ── Class C: annotated slices are not consecutive ────────────────────────
  const annotatedIndices = images
    .map((img, i) => ({ i, region: slices[img.uuid]?.region ?? "None" }))
    .filter(({ region }) => region !== "None")
    .map(({ i }) => i)
    .sort((a, b) => a - b);

  if (annotatedIndices.length > 1 && !consecutive(annotatedIndices)) {
    return <YellowBox>Image slices are not consecutive, please check carefully.</YellowBox>;
  }

  // ── Class D: all clear ───────────────────────────────────────────────────
  return <GreenBox>Image set is valid for submission.</GreenBox>;
}
